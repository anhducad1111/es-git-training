<?php
declare(strict_types=1);
require_once dirname(__DIR__) . '/config.php';

if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    send_json(['success' => false, 'message' => 'Use GET to list firmware history.'], 405);
}
require_key(OTA_ADMIN_KEY);

$rows = array_map(static function (array $entry): array {
    $timestamp = DateTime::createFromFormat('YmdHis', $entry['timestamp'], new DateTimeZone('Asia/Ho_Chi_Minh'));
    return [
        'id' => $entry['id'],
        'filename' => $entry['filename'],
        'version' => $entry['version'],
        'info' => $entry['info'],
        'client' => $entry['client'],
        'size' => $entry['size'],
        'timestamp' => $timestamp !== false ? $timestamp->format('Y-m-d H:i:s') : $entry['timestamp'],
    ];
}, ota_list_entries());

send_json(['success' => true, 'timezone' => 'Asia/Ho_Chi_Minh (UTC+7)', 'data' => $rows]);
