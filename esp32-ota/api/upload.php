<?php
declare(strict_types=1);
require_once dirname(__DIR__) . '/config.php';

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    send_json(['success' => false, 'message' => 'Use POST to upload a firmware file.'], 405);
}
require_key(OTA_ADMIN_KEY);

if (!isset($_FILES['firmware']) || !is_array($_FILES['firmware']) || $_FILES['firmware']['error'] !== UPLOAD_ERR_OK) {
    send_json(['success' => false, 'message' => 'Select a valid firmware file.'], 400);
}

$version = trim((string) ($_POST['version'] ?? ''));
if (!preg_match('/^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/', $version)) {
    send_json(['success' => false, 'message' => 'Version may contain letters, numbers, dots, underscores, and hyphens.'], 400);
}

$versionInformation = trim((string) ($_POST['version_information'] ?? ''));
if (mb_strlen($versionInformation) > 255) {
    send_json(['success' => false, 'message' => 'version_information is limited to 255 characters.'], 400);
}

$clientName = trim((string) ($_POST['client'] ?? ''));
if (mb_strlen($clientName) > 64) {
    send_json(['success' => false, 'message' => 'client is limited to 64 characters.'], 400);
}

$upload = $_FILES['firmware'];
if ($upload['size'] < 1 || $upload['size'] > OTA_MAX_FIRMWARE_BYTES) {
    send_json(['success' => false, 'message' => 'Firmware file size is invalid.'], 400);
}

$binary = file_get_contents($upload['tmp_name']);
if ($binary === false || strlen($binary) !== (int) $upload['size']) {
    send_json(['success' => false, 'message' => 'Could not read the uploaded file.'], 500);
}

try {
    $pdo = new PDO(
        'mysql:host=localhost;dbname=mini_db;charset=utf8mb4',
        'root',
        '',
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
    );
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
        'message' => 'Firmware stored in the database.',
        'id' => $newId,
        'version' => $version,
        'version_information' => $versionInformation === '' ? null : $versionInformation,
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
