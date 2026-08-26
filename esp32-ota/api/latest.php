<?php
declare(strict_types=1);
require_once dirname(__DIR__) . '/config.php';

require_key(OTA_DEVICE_KEY);

$target = ota_resolve_target_entry();
if ($target === null) {
    send_json(['success' => true, 'available' => false]);
}

$current = (string) ($_GET['current'] ?? '');
$comparison = ota_compare_versions($target['version'], $current);
if ($comparison === null) {
    // Non-numeric version strings: fall back to a plain equality check.
    $available = !hash_equals($target['version'], $current);
    $direction = $available ? 'unknown' : 'none';
} else {
    $available = $comparison !== 0;
    $direction = $comparison > 0 ? 'upgrade' : ($comparison < 0 ? 'downgrade' : 'none');
}

send_json([
    'success' => true,
    'available' => $available,
    'direction' => $direction,
    'id' => $target['id'],
    'version' => $target['version'],
    'info' => $target['info'],
    'client' => $target['client'],
    'url' => OTA_PUBLIC_BASE_URL . '/api/download.php?id=' . $target['id'],
    'sha256' => hash_file('sha256', $target['path']),
    'size' => $target['size'],
]);
