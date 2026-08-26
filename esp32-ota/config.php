<?php
declare(strict_types=1);

// Change all values below before using this outside a trusted local network.
const OTA_PUBLIC_BASE_URL = 'http://192.168.1.116/esp32-ota';
const OTA_ADMIN_KEY = 'shodai-haru-2026-8-25';
const OTA_DEVICE_KEY = 'ota-device-2026-8-25';
const OTA_MAX_FIRMWARE_BYTES = 2_000_000;
const OTA_FIRMWARE_DIRECTORY = __DIR__ . DIRECTORY_SEPARATOR . 'firmware';

function send_json(array $data, int $status = 200): never {
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    echo json_encode($data, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    exit;
}

function supplied_key(): string {
    return (string) ($_SERVER['HTTP_X_OTA_KEY'] ?? $_POST['ota_key'] ?? '');
}

function require_key(string $expected): void {
    if ($expected === '' || str_starts_with($expected, 'replace-with-') || !hash_equals($expected, supplied_key())) {
        send_json(['success' => false, 'message' => 'Unauthorized'], 401);
    }
}
