<?php

declare(strict_types=1);

require __DIR__ . '/../src/autoload.php';

$env = [
    'DB_HOST' => '127.0.0.1',
    'DB_PORT' => '3306',
    'DB_NAME' => 'rover_telemetry_test',
    'DB_USER' => 'root',
    'DB_PASSWORD' => '',
    'ONLINE_THRESHOLD_SECONDS' => '15',
    'DEGRADED_THRESHOLD_SECONDS' => '60',
    'RAW_RETENTION_DAYS' => '90',
    'VALIDATION_ERROR_RETENTION_DAYS' => '30',
    'GATEWAY_METRICS_RETENTION_DAYS' => '365',
    'EXPECTED_INTERVAL_SECONDS' => '5',
    'CPU_TEMP_WARNING_C' => '80',
    'DISK_USED_WARNING_PERCENT' => '90',
    'MEMORY_USED_WARNING_PERCENT' => '90',
    'MEDIA_STORAGE_PATH' => 'storage/media_test',
];

foreach ($env as $key => $value) {
    putenv("{$key}={$value}");
    $_SERVER[$key] = $value;
}
