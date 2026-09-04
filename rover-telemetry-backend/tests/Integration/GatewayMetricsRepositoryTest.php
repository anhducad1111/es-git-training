<?php

declare(strict_types=1);

namespace RoverTelemetry\Tests\Integration;

use RoverTelemetry\Repositories\GatewayMetricsRepository;
use RoverTelemetry\Tests\Support\DatabaseTestCase;

final class GatewayMetricsRepositoryTest extends DatabaseTestCase
{
    public function test_sample_and_read_back_in_range(): void
    {
        $repository = new GatewayMetricsRepository($this->pdo);
        $at = new \DateTimeImmutable('2026-09-03T09:05:00Z');

        $repository->sample([
            'cpu_load_percent' => 23.5, 'cpu_temperature_c' => 52.1, 'memory_used_percent' => 27.9,
            'disk_used_percent' => 35.6, 'ingest_rate_per_min' => 60, 'database_size_mb' => 412.7,
        ], $at);

        $points = $repository->pointsInRange(new \DateTimeImmutable('2026-09-03T09:00:00Z'), new \DateTimeImmutable('2026-09-03T09:10:00Z'));
        $this->assertCount(1, $points);
        $this->assertEqualsWithDelta(52.1, (float) $points[0]['cpu_temperature_c'], 0.001);
    }

    public function test_sample_same_minute_twice_upserts_not_duplicates(): void
    {
        $repository = new GatewayMetricsRepository($this->pdo);
        $at = new \DateTimeImmutable('2026-09-03T09:05:00Z');

        $repository->sample(['cpu_load_percent' => 10.0, 'cpu_temperature_c' => 40.0, 'memory_used_percent' => 20.0, 'disk_used_percent' => 30.0, 'ingest_rate_per_min' => 5, 'database_size_mb' => 100.0], $at);
        $repository->sample(['cpu_load_percent' => 90.0, 'cpu_temperature_c' => 70.0, 'memory_used_percent' => 80.0, 'disk_used_percent' => 90.0, 'ingest_rate_per_min' => 50, 'database_size_mb' => 105.0], $at);

        $this->assertSame(1, (int) $this->pdo->query('SELECT COUNT(*) FROM gateway_metrics')->fetchColumn());
    }
}
