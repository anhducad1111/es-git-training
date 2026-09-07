<?php

declare(strict_types=1);

namespace RoverTelemetry\Support;

final class ReadingFormatter
{
    public static function formatRow(array $row): array
    {
        return [
            'recorded_at' => (new \DateTimeImmutable($row['recorded_at'], new \DateTimeZone('UTC')))->format('Y-m-d\TH:i:s.v\Z'),
            'temperature_c' => $row['temperature_c'] !== null ? (float) $row['temperature_c'] : null,
            'humidity_pct' => $row['humidity_pct'] !== null ? (float) $row['humidity_pct'] : null,
            'gas_ppm' => $row['gas_ppm'] !== null ? (float) $row['gas_ppm'] : null,
            'distance_cm' => $row['distance_cm'] !== null ? (float) $row['distance_cm'] : null,
            'auto_brake' => (bool) $row['auto_brake'],
        ];
    }

    public static function minAvgMax(array $bucket, string $prefix): array
    {
        return [
            'min' => $bucket["{$prefix}_min"] !== null ? (float) $bucket["{$prefix}_min"] : null,
            'avg' => $bucket["{$prefix}_avg"] !== null ? (float) $bucket["{$prefix}_avg"] : null,
            'max' => $bucket["{$prefix}_max"] !== null ? (float) $bucket["{$prefix}_max"] : null,
        ];
    }
}
