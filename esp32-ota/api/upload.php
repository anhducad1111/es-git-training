<?php
declare(strict_types=1);
require_once dirname(__DIR__) . '/config.php';

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    send_json(['success' => false, 'message' => 'Use POST to upload a firmware file.'], 405);
}
require_key(OTA_ADMIN_KEY);

if (!isset($_FILES['firmware']) || !is_array($_FILES['firmware']) || $_FILES['firmware']['error'] !== UPLOAD_ERR_OK) {
    send_json(['success' => false, 'message' => 'Select a valid .bin firmware file.'], 400);
}

$version = trim((string) ($_POST['version'] ?? ''));
if (!preg_match('/^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/', $version)) {
    send_json(['success' => false, 'message' => 'Version may contain letters, numbers, dots, underscores, and hyphens.'], 400);
}

$upload = $_FILES['firmware'];
if ($upload['size'] < 1 || $upload['size'] > OTA_MAX_FIRMWARE_BYTES) {
    send_json(['success' => false, 'message' => 'Firmware file size is invalid.'], 400);
}

$handle = fopen($upload['tmp_name'], 'rb');
$magic = $handle === false ? false : fread($handle, 1);
if ($handle !== false) fclose($handle);
if ($magic !== "\xE9") {
    send_json(['success' => false, 'message' => 'This does not appear to be an ESP32 firmware binary.'], 400);
}

if (!is_dir(OTA_FIRMWARE_DIRECTORY) && !mkdir(OTA_FIRMWARE_DIRECTORY, 0755, true) && !is_dir(OTA_FIRMWARE_DIRECTORY)) {
    send_json(['success' => false, 'message' => 'Could not create firmware directory.'], 500);
}

$filename = 'firmware-' . $version . '.bin';
$destination = OTA_FIRMWARE_DIRECTORY . DIRECTORY_SEPARATOR . $filename;
if (!move_uploaded_file($upload['tmp_name'], $destination)) {
    send_json(['success' => false, 'message' => 'Could not save the firmware file.'], 500);
}

$manifest = [
    'version' => $version,
    'filename' => $filename,
    'size' => filesize($destination),
    'sha256' => hash_file('sha256', $destination),
    'uploaded_at' => gmdate('c'),
];
if (file_put_contents(OTA_FIRMWARE_DIRECTORY . DIRECTORY_SEPARATOR . 'manifest.json', json_encode($manifest, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES), LOCK_EX) === false) {
    send_json(['success' => false, 'message' => 'Firmware saved, but manifest could not be written.'], 500);
}

send_json(['success' => true, 'message' => 'Firmware published.', 'firmware' => $manifest]);
