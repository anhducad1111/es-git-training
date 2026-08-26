<?php
declare(strict_types=1);
require_once dirname(__DIR__) . '/config.php';

require_key(OTA_DEVICE_KEY);

$id = (int) ($_GET['id'] ?? 0);
if ($id < 1) {
    send_json(['success' => false, 'message' => 'A valid id is required.'], 400);
}

try {
    $pdo = new PDO(
        'mysql:host=localhost;dbname=mini_db;charset=utf8mb4',
        'root',
        '',
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
    );
    $stmt = $pdo->prepare('SELECT ver, `file` FROM storage WHERE id = :id');
    $stmt->bindValue(':id', $id, PDO::PARAM_INT);
    $stmt->execute();
    $row = $stmt->fetch(PDO::FETCH_ASSOC);
} catch (Throwable $error) {
    send_json(['success' => false, 'message' => 'Failed to load firmware.'], 500);
}

if ($row === false) {
    send_json(['success' => false, 'message' => 'Firmware not found.'], 404);
}

header('Content-Type: application/octet-stream');
header('Content-Length: ' . strlen($row['file']));
header('Content-Disposition: attachment; filename="firmware-' . $row['ver'] . '.bin"');
header('Cache-Control: no-store');
echo $row['file'];
