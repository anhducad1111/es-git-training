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
