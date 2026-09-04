<?php

declare(strict_types=1);

namespace RoverTelemetry\Repositories;

use PDO;

final class SummaryRepository
{
    private const BUCKET_SECONDS = ['minute' => 60, 'hour' => 3600, 'day' => 86400];

    public function __construct(private readonly PDO $pdo)
    {
    }

    public function recomputeBucket(int $deviceId, string $granularity, \DateTimeImmutable $bucketStart): void
    {
        $seconds = self::BUCKET_SECONDS[$granularity];
        $bucketEnd = $bucketStart->modify("+{$seconds} seconds");

        $stmt = $this->pdo->prepare(
            'SELECT recorded_at, temperature_c, humidity_pct, gas_ppm, distance_cm, auto_brake '
            . 'FROM telemetry_readings WHERE device_id = :device_id AND recorded_at >= :start AND recorded_at < :end '
            . 'ORDER BY recorded_at ASC'
        );
        $stmt->execute([
            'device_id' => $deviceId,
            'start' => $bucketStart->format('Y-m-d H:i:s.v'),
            'end' => $bucketEnd->format('Y-m-d H:i:s.v'),
        ]);
        $rows = $stmt->fetchAll();

        $stats = $this->computeStats($rows);

        $upsert = $this->pdo->prepare(
            'INSERT INTO telemetry_summaries (device_id, granularity, bucket_start, sample_count, '
            . 'temp_min, temp_avg, temp_max, hum_min, hum_avg, hum_max, gas_min, gas_avg, gas_max, '
            . 'dist_min, dist_avg, dist_max, obstacle_events, computed_at) VALUES '
            . '(:device_id, :granularity, :bucket_start, :sample_count, :temp_min, :temp_avg, :temp_max, '
            . ':hum_min, :hum_avg, :hum_max, :gas_min, :gas_avg, :gas_max, :dist_min, :dist_avg, :dist_max, '
            . ':obstacle_events, :computed_at) '
            . 'ON DUPLICATE KEY UPDATE sample_count = VALUES(sample_count), '
            . 'temp_min = VALUES(temp_min), temp_avg = VALUES(temp_avg), temp_max = VALUES(temp_max), '
            . 'hum_min = VALUES(hum_min), hum_avg = VALUES(hum_avg), hum_max = VALUES(hum_max), '
            . 'gas_min = VALUES(gas_min), gas_avg = VALUES(gas_avg), gas_max = VALUES(gas_max), '
            . 'dist_min = VALUES(dist_min), dist_avg = VALUES(dist_avg), dist_max = VALUES(dist_max), '
            . 'obstacle_events = VALUES(obstacle_events), computed_at = VALUES(computed_at)'
        );
        $upsert->execute([
            'device_id' => $deviceId,
            'granularity' => $granularity,
            'bucket_start' => $bucketStart->format('Y-m-d H:i:s'),
            'sample_count' => count($rows),
            'temp_min' => $stats['temp']['min'], 'temp_avg' => $stats['temp']['avg'], 'temp_max' => $stats['temp']['max'],
            'hum_min' => $stats['hum']['min'], 'hum_avg' => $stats['hum']['avg'], 'hum_max' => $stats['hum']['max'],
            'gas_min' => $stats['gas']['min'], 'gas_avg' => $stats['gas']['avg'], 'gas_max' => $stats['gas']['max'],
            'dist_min' => $stats['dist']['min'], 'dist_avg' => $stats['dist']['avg'], 'dist_max' => $stats['dist']['max'],
            'obstacle_events' => $this->countRisingEdges($rows),
            'computed_at' => (new \DateTimeImmutable('now', new \DateTimeZone('UTC')))->format('Y-m-d H:i:s'),
        ]);
    }

    public function bucketsInRange(int $deviceId, string $granularity, \DateTimeImmutable $start, \DateTimeImmutable $end): array
    {
        $stmt = $this->pdo->prepare(
            'SELECT * FROM telemetry_summaries WHERE device_id = :device_id AND granularity = :granularity '
            . 'AND bucket_start BETWEEN :start AND :end ORDER BY bucket_start ASC'
        );
        $stmt->execute([
            'device_id' => $deviceId,
            'granularity' => $granularity,
            'start' => $start->format('Y-m-d H:i:s'),
            'end' => $end->format('Y-m-d H:i:s'),
        ]);

        return $stmt->fetchAll();
    }

    private function computeStats(array $rows): array
    {
        $fields = ['temp' => 'temperature_c', 'hum' => 'humidity_pct', 'gas' => 'gas_ppm', 'dist' => 'distance_cm'];
        $stats = [];
        foreach ($fields as $key => $column) {
            $values = array_values(array_filter(
                array_map(fn($row) => $row[$column] !== null ? (float) $row[$column] : null, $rows),
                fn($v) => $v !== null
            ));
            $stats[$key] = count($values) > 0
                ? ['min' => min($values), 'avg' => array_sum($values) / count($values), 'max' => max($values)]
                : ['min' => null, 'avg' => null, 'max' => null];
        }

        return $stats;
    }

    private function countRisingEdges(array $rows): int
    {
        $edges = 0;
        $previous = 0;
        foreach ($rows as $row) {
            $current = (int) $row['auto_brake'];
            if ($previous === 0 && $current === 1) {
                $edges++;
            }
            $previous = $current;
        }

        return $edges;
    }
}
