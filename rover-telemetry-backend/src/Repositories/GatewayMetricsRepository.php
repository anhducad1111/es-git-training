<?php

declare(strict_types=1);

namespace RoverTelemetry\Repositories;

use PDO;

final class GatewayMetricsRepository
{
    public function __construct(private readonly PDO $pdo)
    {
    }

    public function sample(array $metrics, \DateTimeImmutable $sampledAt): void
    {
        $stmt = $this->pdo->prepare(
            'INSERT INTO gateway_metrics (sampled_at, cpu_load_percent, cpu_temperature_c, memory_used_percent, disk_used_percent, ingest_rate_per_min, database_size_mb) '
            . 'VALUES (:sampled_at, :cpu_load_percent, :cpu_temperature_c, :memory_used_percent, :disk_used_percent, :ingest_rate_per_min, :database_size_mb) '
            . 'ON DUPLICATE KEY UPDATE cpu_load_percent = VALUES(cpu_load_percent), cpu_temperature_c = VALUES(cpu_temperature_c), '
            . 'memory_used_percent = VALUES(memory_used_percent), disk_used_percent = VALUES(disk_used_percent), '
            . 'ingest_rate_per_min = VALUES(ingest_rate_per_min), database_size_mb = VALUES(database_size_mb)'
        );
        $stmt->execute([
            'sampled_at' => $sampledAt->format('Y-m-d H:i:00'),
            'cpu_load_percent' => $metrics['cpu_load_percent'],
            'cpu_temperature_c' => $metrics['cpu_temperature_c'],
            'memory_used_percent' => $metrics['memory_used_percent'],
            'disk_used_percent' => $metrics['disk_used_percent'],
            'ingest_rate_per_min' => $metrics['ingest_rate_per_min'],
            'database_size_mb' => $metrics['database_size_mb'],
        ]);
    }

    public function pointsInRange(\DateTimeImmutable $start, \DateTimeImmutable $end): array
    {
        $stmt = $this->pdo->prepare(
            'SELECT * FROM gateway_metrics WHERE sampled_at BETWEEN :start AND :end ORDER BY sampled_at ASC'
        );
        $stmt->execute(['start' => $start->format('Y-m-d H:i:s'), 'end' => $end->format('Y-m-d H:i:s')]);

        return $stmt->fetchAll();
    }
}
