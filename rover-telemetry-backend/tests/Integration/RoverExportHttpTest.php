<?php

declare(strict_types=1);

namespace RoverTelemetry\Tests\Integration;

use RoverTelemetry\Repositories\RoverRepository;
use RoverTelemetry\Repositories\TelemetryRepository;
use RoverTelemetry\Tests\Support\HttpTestCase;

final class RoverExportHttpTest extends HttpTestCase
{
    private function seed(): void
    {
        $rover = (new RoverRepository($this->pdo))->getOrCreateByDeviceUid('rover-001');
        $telemetry = new TelemetryRepository($this->pdo);
        $telemetry->insert((int) $rover['id'], new \DateTimeImmutable('2026-09-03T10:00:00Z'), 25.4, 61.2, 128.0, 34.5, 0);
        $telemetry->insert((int) $rover['id'], new \DateTimeImmutable('2026-09-03T10:00:05Z'), 25.5, 61.3, 129.0, 34.6, 0);
    }

    public function test_csv_export_has_header_and_matching_row_count(): void
    {
        $this->seed();

        $response = $this->request('GET', '/api/v1/rovers/rover-001/export?format=csv&start=2026-09-03T00:00:00Z&end=2026-09-04T00:00:00Z');

        $this->assertSame(200, $response['status']);
        $this->assertStringContainsString('text/csv', $response['headers']);
        $lines = explode("\n", trim($response['body']));
        $this->assertSame('device_uid,recorded_at,temperature_c,humidity_pct,gas_ppm,distance_cm,auto_brake', $lines[0]);
        $this->assertCount(3, $lines);
    }

    public function test_json_export_returns_array_matching_row_count(): void
    {
        $this->seed();

        $response = $this->request('GET', '/api/v1/rovers/rover-001/export?format=json&start=2026-09-03T00:00:00Z&end=2026-09-04T00:00:00Z');

        $body = json_decode($response['body'], true);
        $this->assertCount(2, $body);
    }
}
