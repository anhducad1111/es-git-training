<?php
declare(strict_types=1);
require_once dirname(__DIR__) . '/config.php';

require_key(OTA_DEVICE_KEY);

$latest = ota_latest_entry();
if ($latest === null) {
    send_json(['success' => true, 'available' => false]);
}

$current = (string) ($_GET['current'] ?? '');
$available = !hash_equals($latest['version'], $current);

send_json([
    'success' => true,
    'available' => $available,
    'id' => $latest['id'],
    'version' => $latest['version'],
    'info' => $latest['info'],
    'client' => $latest['client'],
    'url' => OTA_PUBLIC_BASE_URL . '/api/download.php?id=' . $latest['id'],
    'sha256' => hash_file('sha256', $latest['path']),
    'size' => $latest['size'],
]);
