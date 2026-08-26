<?php
declare(strict_types=1);
require_once dirname(__DIR__) . '/config.php';

date_default_timezone_set('Asia/Ho_Chi_Minh');

function get_pdo(): PDO {
    static $pdo = null;
    if ($pdo === null) {
        $pdo = new PDO(
            'mysql:host=localhost;dbname=mini_db;charset=utf8mb4',
            'root',
            '',
            [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC]
        );
    }
    return $pdo;
}

$method = $_SERVER['REQUEST_METHOD'];
$action = (string) ($_GET['action'] ?? $_POST['action'] ?? 'log');

if (!in_array($action, ['log', 'ota'], true)) {
    send_json(['success' => false, 'message' => 'action must be "log" or "ota".'], 400);
}

if ($method === 'GET') {
    if ($action !== 'log') {
        send_json(['success' => false, 'message' => 'GET only supports action=log.'], 400);
    }
    try {
        $stmt = get_pdo()->query('SELECT id, device_name, temperature, humidity, created_at FROM sensor_logs ORDER BY created_at DESC, id DESC LIMIT 10');
        send_json(['success' => true, 'data' => $stmt->fetchAll(), 'server_time' => date('Y-m-d H:i:s')]);
    } catch (Throwable $error) {
        send_json(['success' => false, 'message' => 'Failed to fetch sensor data'], 500);
    }
}

if ($method === 'POST') {
    if ($action === 'ota') {
        require_key(OTA_ADMIN_KEY);

        if (!isset($_FILES['file']) || !is_array($_FILES['file']) || $_FILES['file']['error'] !== UPLOAD_ERR_OK) {
            send_json(['success' => false, 'message' => 'No valid file was uploaded.'], 400);
        }

        $version = trim((string) ($_POST['ver'] ?? ''));
        $versionInformation = trim((string) ($_POST['version_information'] ?? ''));
        $clientName = trim((string) ($_POST['client'] ?? ''));
        if ($version === '' || mb_strlen($version) > 64 || mb_strlen($versionInformation) > 255 || mb_strlen($clientName) > 64) {
            send_json(['success' => false, 'message' => 'ver is required (up to 64 characters); version_information is limited to 255 characters; client is limited to 64 characters.'], 400);
        }

        $upload = $_FILES['file'];
        if ($upload['size'] < 1 || $upload['size'] > 10 * 1024 * 1024) {
            send_json(['success' => false, 'message' => 'File size must be between 1 byte and 10 MB.'], 400);
        }

        $binary = file_get_contents($upload['tmp_name']);
        if ($binary === false || strlen($binary) !== (int) $upload['size']) {
            send_json(['success' => false, 'message' => 'Could not read the uploaded file.'], 500);
        }

        try {
            $pdo = get_pdo();
            $pdo->beginTransaction();

            $insert = $pdo->prepare('INSERT INTO storage (ver, `file`, version_information, client) VALUES (:ver, :file, :version_information, :client)');
            $insert->bindValue(':ver', $version, PDO::PARAM_STR);
            $insert->bindValue(':file', $binary, PDO::PARAM_LOB);
            $insert->bindValue(':version_information', $versionInformation === '' ? null : $versionInformation, $versionInformation === '' ? PDO::PARAM_NULL : PDO::PARAM_STR);
            $insert->bindValue(':client', $clientName === '' ? null : $clientName, $clientName === '' ? PDO::PARAM_NULL : PDO::PARAM_STR);
            $insert->execute();
            $newId = (int) $pdo->lastInsertId();

            $keepIds = $pdo->query('SELECT id FROM storage ORDER BY `timestamp` DESC, id DESC LIMIT 5')->fetchAll(PDO::FETCH_COLUMN);
            $placeholders = implode(',', array_fill(0, count($keepIds), '?'));
            $delete = $pdo->prepare("DELETE FROM storage WHERE id NOT IN ($placeholders)");
            $delete->execute($keepIds);
            $deletedCount = $delete->rowCount();

            $pdo->commit();
            send_json([
                'success' => true,
                'message' => 'File stored in the database.',
                'id' => $newId,
                'version' => $version,
                'client' => $clientName === '' ? null : $clientName,
                'size' => (int) $upload['size'],
                'removed_old_records' => $deletedCount,
            ], 201);
        } catch (Throwable $error) {
            if (isset($pdo) && $pdo->inTransaction()) {
                $pdo->rollBack();
            }
            send_json(['success' => false, 'message' => 'Database storage failed.'], 500);
        }
    }

    // action === 'log'
    $data = json_decode(file_get_contents('php://input'), true);
    if (!is_array($data)) {
        send_json(['success' => false, 'message' => 'Invalid JSON'], 400);
    }

    $device = $data['device'] ?? null;
    $temp = $data['temp'] ?? null;
    $humidity = $data['humidity'] ?? null;
    if ($device === null || $temp === null || $humidity === null) {
        send_json(['success' => false, 'message' => 'device, temp and humidity are required'], 400);
    }

    try {
        $pdo = get_pdo();
        $stmt = $pdo->prepare('INSERT INTO sensor_logs (device_name, temperature, humidity, created_at) VALUES (:device,:temperature,:humidity,:created_at)');
        $received_time = date('Y-m-d H:i:s');
        $stmt->execute([':device' => $device, ':temperature' => $temp, ':humidity' => $humidity, ':created_at' => $received_time]);
        send_json([
            'success' => true,
            'message' => 'Sensor data saved successfully',
            'data' => ['id' => $pdo->lastInsertId(), 'device' => $device, 'temperature' => $temp, 'humidity' => $humidity, 'created_at' => $received_time],
        ]);
    } catch (Throwable $error) {
        send_json(['success' => false, 'message' => 'Failed to save sensor data'], 500);
    }
}

send_json(['success' => false, 'message' => 'Only GET and POST methods are allowed'], 405);
