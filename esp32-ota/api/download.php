<?php
declare(strict_types=1);
require_once dirname(__DIR__) . '/config.php';

require_key(OTA_DEVICE_KEY);

$id = (int) ($_GET['id'] ?? 0);
if ($id < 1) {
    send_json(['success' => false, 'message' => 'A valid id is required.'], 400);
}

$entry = ota_find_entry($id);
if ($entry === null) {
    send_json(['success' => false, 'message' => 'Firmware not found.'], 404);
}

header('Content-Type: application/octet-stream');
header('Content-Length: ' . $entry['size']);
header('Content-Disposition: attachment; filename="' . basename($entry['path']) . '"');
header('Cache-Control: no-store');
readfile($entry['path']);
