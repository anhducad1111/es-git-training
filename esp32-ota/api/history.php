<?php
declare(strict_types=1);
require_once dirname(__DIR__) . '/config.php';

if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    send_json(['success' => false, 'message' => 'Use GET to list firmware history.'], 405);
}
require_key(OTA_ADMIN_KEY);

try {
    $pdo = new PDO(
        'mysql:host=localhost;dbname=mini_db;charset=utf8mb4',
        'root',
        '',
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
    );
    $stmt = $pdo->query(
        "SELECT id, ver, version_information, client, LENGTH(`file`) AS size, " .
        "CONVERT_TZ(`timestamp`, @@session.time_zone, '+07:00') AS `timestamp` " .
        'FROM storage ORDER BY `timestamp` DESC, id DESC'
    );
    $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);
} catch (Throwable $error) {
    send_json(['success' => false, 'message' => 'Failed to load firmware history.'], 500);
}

send_json(['success' => true, 'timezone' => 'Asia/Ho_Chi_Minh (UTC+7)', 'data' => $rows]);
