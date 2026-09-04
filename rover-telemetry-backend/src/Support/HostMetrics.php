<?php

declare(strict_types=1);

namespace RoverTelemetry\Support;

use PDO;

final class HostMetrics
{
    public static function collect(PDO $pdo, string $dbName): array
    {
        return [
            'cpu_load_percent' => self::cpuLoadPercent(),
            'cpu_temperature_c' => self::cpuTemperatureC(),
            'memory_used_percent' => self::memoryUsedPercent(),
            'disk_used_percent' => self::diskUsedPercent(),
            'ingest_rate_per_min' => self::ingestRatePerMin($pdo),
            'database_size_mb' => self::databaseSizeMb($pdo, $dbName),
        ];
    }

    private static function cpuLoadPercent(): float
    {
        if (!is_readable('/proc/loadavg')) {
            return 0.0;
        }
        $contents = file_get_contents('/proc/loadavg');
        $parts = explode(' ', trim((string) $contents));
        $cores = max(1, (int) shell_exec('nproc') ?: 1);

        return round(((float) $parts[0]) / $cores * 100, 1);
    }

    private static function cpuTemperatureC(): float
    {
        if (!is_readable('/sys/class/thermal/thermal_zone0/temp')) {
            return 0.0;
        }

        return round(((int) trim((string) file_get_contents('/sys/class/thermal/thermal_zone0/temp'))) / 1000, 1);
    }

    private static function memoryUsedPercent(): float
    {
        if (!is_readable('/proc/meminfo')) {
            return 0.0;
        }
        $lines = file('/proc/meminfo');
        $values = [];
        foreach ($lines as $line) {
            if (preg_match('/^(MemTotal|MemAvailable):\s+(\d+)/', $line, $m)) {
                $values[$m[1]] = (int) $m[2];
            }
        }
        if (!isset($values['MemTotal'], $values['MemAvailable']) || $values['MemTotal'] === 0) {
            return 0.0;
        }

        return round((1 - $values['MemAvailable'] / $values['MemTotal']) * 100, 1);
    }

    private static function diskUsedPercent(): float
    {
        $total = @disk_total_space('/');
        $free = @disk_free_space('/');
        if (!$total) {
            return 0.0;
        }

        return round((1 - $free / $total) * 100, 1);
    }

    private static function ingestRatePerMin(PDO $pdo): int
    {
        $stmt = $pdo->query(
            'SELECT COUNT(*) FROM telemetry_readings WHERE recorded_at >= (UTC_TIMESTAMP() - INTERVAL 1 MINUTE)'
        );

        return (int) $stmt->fetchColumn();
    }

    private static function databaseSizeMb(PDO $pdo, string $dbName): float
    {
        $stmt = $pdo->prepare(
            'SELECT ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) FROM information_schema.TABLES WHERE table_schema = :db'
        );
        $stmt->execute(['db' => $dbName]);
        $size = $stmt->fetchColumn();

        return $size !== null ? (float) $size : 0.0;
    }
}
