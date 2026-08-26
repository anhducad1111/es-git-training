<?php
declare(strict_types=1);
require_once dirname(__DIR__) . '/config.php';

require_key(OTA_DEVICE_KEY);
$manifestPath = OTA_FIRMWARE_DIRECTORY . DIRECTORY_SEPARATOR . 'manifest.json';
if (!is_file($manifestPath)) {
    send_json(['success' => true, 'available' => false]);
}

$manifest = json_decode((string) file_get_contents($manifestPath), true);
if (!is_array($manifest) || !isset($manifest['version'], $manifest['filename'], $manifest['sha256'], $manifest['size'])) {
    send_json(['success' => false, 'message' => 'Invalid firmware manifest'], 500);
}

$current = (string) ($_GET['current'] ?? '');
$available = !hash_equals((string) $manifest['version'], $current);
send_json([
    'success' => true,
    'available' => $available,
    'version' => $manifest['version'],
    'url' => OTA_PUBLIC_BASE_URL . '/firmware/' . rawurlencode((string) $manifest['filename']),
    'sha256' => $manifest['sha256'],
    'size' => $manifest['size'],
]);
