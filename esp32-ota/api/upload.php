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

$upload = $_FILES['firmware'];
if ($upload['size'] < 1 || $upload['size'] > OTA_MAX_FIRMWARE_BYTES) {
    send_json(['success' => false, 'message' => 'Firmware file size is invalid.'], 400);
}

$extension = pathinfo($upload['name'], PATHINFO_EXTENSION);
$filename = preg_replace('/[^A-Za-z0-9]/', '', pathinfo($upload['name'], PATHINFO_FILENAME));
if ($filename === '') {
    $filename = 'file';
}

$version = trim((string) ($_POST['version'] ?? ''));
$info = trim((string) ($_POST['info'] ?? ''));
$client = trim((string) ($_POST['client'] ?? ''));
if (
    $version === '' || !preg_match('/^[A-Za-z0-9_]+$/', $version)
    || $info === '' || !preg_match('/^[A-Za-z0-9]+$/', $info)
    || $client === '' || !preg_match('/^[A-Za-z0-9]+$/', $client)
) {
    send_json(['success' => false, 'message' => 'version, info, and client are required; info and client must be alphanumeric only, version may also contain underscores (e.g. 1_1_1).'], 400);
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
