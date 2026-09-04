<?php

declare(strict_types=1);

namespace RoverTelemetry;

final class Config
{
    public function __construct(
        public readonly string $dbHost,
        public readonly int $dbPort,
        public readonly string $dbName,
        public readonly string $dbUser,
        public readonly string $dbPassword,
        public readonly int $onlineThresholdSeconds,
        public readonly int $degradedThresholdSeconds,
        public readonly int $rawRetentionDays,
        public readonly int $validationErrorRetentionDays,
        public readonly int $gatewayMetricsRetentionDays,
        public readonly int $expectedIntervalSeconds,
        public readonly float $cpuTempWarningC,
        public readonly float $diskUsedWarningPercent,
        public readonly float $memoryUsedWarningPercent,
        public readonly string $mediaStoragePath,
    ) {
    }

    public static function fromEnv(): self
    {
        return new self(
            dbHost: getenv('DB_HOST') ?: '127.0.0.1',
            dbPort: (int) (getenv('DB_PORT') ?: 3306),
            dbName: getenv('DB_NAME') ?: 'rover_telemetry',
            dbUser: getenv('DB_USER') ?: 'root',
            dbPassword: getenv('DB_PASSWORD') ?: '',
            onlineThresholdSeconds: (int) (getenv('ONLINE_THRESHOLD_SECONDS') ?: 15),
            degradedThresholdSeconds: (int) (getenv('DEGRADED_THRESHOLD_SECONDS') ?: 60),
            rawRetentionDays: (int) (getenv('RAW_RETENTION_DAYS') ?: 90),
            validationErrorRetentionDays: (int) (getenv('VALIDATION_ERROR_RETENTION_DAYS') ?: 30),
            gatewayMetricsRetentionDays: (int) (getenv('GATEWAY_METRICS_RETENTION_DAYS') ?: 365),
            expectedIntervalSeconds: (int) (getenv('EXPECTED_INTERVAL_SECONDS') ?: 5),
            cpuTempWarningC: (float) (getenv('CPU_TEMP_WARNING_C') ?: 80.0),
            diskUsedWarningPercent: (float) (getenv('DISK_USED_WARNING_PERCENT') ?: 90.0),
            memoryUsedWarningPercent: (float) (getenv('MEMORY_USED_WARNING_PERCENT') ?: 90.0),
            mediaStoragePath: getenv('MEDIA_STORAGE_PATH') ?: 'storage/media',
        );
    }
}
