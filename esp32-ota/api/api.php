<?php
declare(strict_types=1);
require_once dirname(__DIR__) . '/config.php';

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

        $upload = $_FILES['file'];
        if ($upload['size'] < 1 || $upload['size'] > OTA_MAX_FIRMWARE_BYTES) {
            send_json(['success' => false, 'message' => 'Firmware file size is invalid.'], 400);
        }

        $extension = pathinfo($upload['name'], PATHINFO_EXTENSION);
        $baseName = pathinfo($upload['name'], PATHINFO_FILENAME);
        $parts = explode('-', $baseName);
        if (count($parts) !== 4) {
            send_json(['success' => false, 'message' => 'File name must be "filename-version-info-client.<ext>".'], 400);
        }
        [$filename, $version, $info, $client] = $parts;
        if (
            $filename === '' || !preg_match('/^[A-Za-z0-9]+$/', $filename)
            || $version === '' || !preg_match('/^[A-Za-z0-9_]+$/', $version)
            || $info === '' || !preg_match('/^[A-Za-z0-9]+$/', $info)
            || $client === '' || !preg_match('/^[A-Za-z0-9]+$/', $client)
        ) {
            send_json(['success' => false, 'message' => 'filename, info, and client must be alphanumeric only; version may also contain underscores (e.g. 1_1_1).'], 400);
        }

        if (!is_dir(OTA_FIRMWARE_DIRECTORY) && !mkdir(OTA_FIRMWARE_DIRECTORY, 0755, true) && !is_dir(OTA_FIRMWARE_DIRECTORY)) {
            send_json(['success' => false, 'message' => 'Could not create firmware directory.'], 500);
        }

        $id = ota_next_id();
        $timestamp = ota_timestamp();
        $ext = $extension !== '' ? '.' . $extension : '';
        $storedName = "{$id}-{$filename}-{$version}-{$info}-{$client}-{$timestamp}{$ext}";
        $destination = OTA_FIRMWARE_DIRECTORY . DIRECTORY_SEPARATOR . $storedName;

        if (!move_uploaded_file($upload['tmp_name'], $destination)) {
            send_json(['success' => false, 'message' => 'Could not save the firmware file.'], 500);
        }

        $removedFiles = ota_prune_old_files();

        send_json([
            'success' => true,
            'message' => 'Firmware saved.',
            'id' => $id,
            'filename' => $filename,
            'version' => $version,
            'info' => $info,
            'client' => $client,
            'timestamp' => $timestamp,
            'stored_as' => $storedName,
            'size' => (int) $upload['size'],
            'removed_old_files' => $removedFiles,
        ], 201);
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
