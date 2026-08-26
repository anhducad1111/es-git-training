<?php
declare(strict_types=1);
require_once dirname(__DIR__) . '/config.php';

require_key(OTA_DEVICE_KEY);

try {
    $pdo = new PDO(
        'mysql:host=localhost;dbname=mini_db;charset=utf8mb4',
        'root',
        '',
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
    );
    $latest = $pdo->query('SELECT id, ver, version_information, LENGTH(`file`) AS size, SHA2(`file`, 256) AS sha256 FROM storage ORDER BY `timestamp` DESC, id DESC LIMIT 1')->fetch(PDO::FETCH_ASSOC);
} catch (Throwable $error) {
    send_json(['success' => false, 'message' => 'Failed to check firmware.'], 500);
}

if ($latest === false) {
    send_json(['success' => true, 'available' => false]);
}

$current = (string) ($_GET['current'] ?? '');
$available = !hash_equals((string) $latest['ver'], $current);
send_json([
    'success' => true,
    'available' => $available,
    'version' => $latest['ver'],
    'version_information' => $latest['version_information'],
    'url' => OTA_PUBLIC_BASE_URL . '/api/download.php?id=' . $latest['id'],
    'sha256' => $latest['sha256'],
    'size' => (int) $latest['size'],
]);
