<?php

declare(strict_types=1);

namespace RoverTelemetry\Tests\Integration;

use RoverTelemetry\Repositories\GatewayMetricsRepository;
use RoverTelemetry\Tests\Support\HttpTestCase;

final class SystemHistoryHttpTest extends HttpTestCase
{
    public function test_returns_points_in_order_with_a_gap_for_missing_samples(): void
    {
        $repository = new GatewayMetricsRepository($this->pdo);
        $repository->sample(['cpu_load_percent' => 10.0, 'cpu_temperature_c' => 40.0, 'memory_used_percent' => 20.0, 'disk_used_percent' => 30.0, 'ingest_rate_per_min' => 5, 'database_size_mb' => 100.0], new \DateTimeImmutable('2026-09-03T09:00:00Z'));
        $repository->sample(['cpu_load_percent' => 12.0, 'cpu_temperature_c' => 41.0, 'memory_used_percent' => 21.0, 'disk_used_percent' => 30.0, 'ingest_rate_per_min' => 6, 'database_size_mb' => 100.1], new \DateTimeImmutable('2026-09-03T09:01:00Z'));

        $response = $this->request('GET', '/api/v1/system/history?start=2026-09-03T09:00:00Z&end=2026-09-03T09:10:00Z');

        $this->assertSame(200, $response['status']);
        $body = json_decode($response['body'], true);
        $this->assertSame(2, $body['count']);
        $this->assertLessThan($body['points'][1]['sampled_at'], $body['points'][0]['sampled_at']);
    }

    public function test_missing_start_or_end_is_rejected(): void
    {
        $response = $this->request('GET', '/api/v1/system/history');

        $this->assertSame(400, $response['status']);
        $this->assertSame('INVALID_PARAMETER', json_decode($response['body'], true)['error']['code']);
    }
}
