<?php

declare(strict_types=1);

namespace RoverTelemetry\Tests\Integration;

use RoverTelemetry\Repositories\RoverRepository;
use RoverTelemetry\Repositories\SummaryRepository;
use RoverTelemetry\Repositories\TelemetryRepository;
use RoverTelemetry\Tests\Support\HttpTestCase;

final class RoverReadingsResolutionHttpTest extends HttpTestCase
{
    public function test_short_range_auto_resolves_to_raw(): void
    {
        $rover = (new RoverRepository($this->pdo))->getOrCreateByDeviceUid('rover-001');
        $deviceId = (int) $rover['id'];
        $telemetry = new TelemetryRepository($this->pdo);
        $start = new \DateTimeImmutable('2026-09-03T09:00:00Z');
        for ($i = 0; $i < 5; $i++) {
            $telemetry->insert($deviceId, $start->modify("+{$i} seconds"), 20.0 + $i, 50.0, 100.0, 50.0, 0);
        }

        $response = $this->request('GET', '/api/v1/rovers/rover-001/readings?start=2026-09-03T09:00:00Z&end=2026-09-03T09:00:10Z');

        $body = json_decode($response['body'], true);
        $this->assertSame('raw', $body['resolution']);
        $this->assertSame(5, $body['count']);
        $this->assertArrayHasKey('raw_rows_in_range', $body['query']);
    }

    public function test_gap_longer_than_twice_expected_interval_is_reported(): void
    {
        $rover = (new RoverRepository($this->pdo))->getOrCreateByDeviceUid('rover-001');
        $deviceId = (int) $rover['id'];
        $telemetry = new TelemetryRepository($this->pdo);
        $telemetry->insert($deviceId, new \DateTimeImmutable('2026-09-03T09:00:00Z'), 20.0, 50.0, 100.0, 50.0, 0);
        $telemetry->insert($deviceId, new \DateTimeImmutable('2026-09-03T09:05:00Z'), 21.0, 50.0, 100.0, 50.0, 0);

        $response = $this->request('GET', '/api/v1/rovers/rover-001/readings?start=2026-09-03T09:00:00Z&end=2026-09-03T09:06:00Z');

        $body = json_decode($response['body'], true);
        $this->assertNotEmpty($body['gaps']);
        $this->assertSame(300, $body['gaps'][0]['duration_seconds']);
    }

    public function test_explicit_raw_is_accepted_when_actual_row_count_fits_the_cap(): void
    {
        // A wide date range with no seeded data has an actual raw_rows_in_range of 0,
        // which fits the cap — resolution=raw is a request about the requested tier, not
        // an automatic range-width rejection, so this must still succeed.
        (new RoverRepository($this->pdo))->getOrCreateByDeviceUid('rover-001');

        $response = $this->request(
            'GET',
            '/api/v1/rovers/rover-001/readings?start=2026-01-01T00:00:00Z&end=2026-09-01T00:00:00Z&resolution=raw'
        );

        $this->assertSame(200, $response['status']);
        $this->assertSame('raw', json_decode($response['body'], true)['resolution']);
    }

    public function test_explicit_raw_over_cap_is_rejected(): void
    {
        $rover = (new RoverRepository($this->pdo))->getOrCreateByDeviceUid('rover-001');
        $deviceId = (int) $rover['id'];
        $telemetry = new TelemetryRepository($this->pdo);
        $start = new \DateTimeImmutable('2026-09-03T00:00:00Z');
        for ($i = 0; $i < 5001; $i++) {
            $telemetry->insert($deviceId, $start->modify("+{$i} seconds"), 20.0, 50.0, 100.0, 50.0, 0);
        }

        $response = $this->request(
            'GET',
            '/api/v1/rovers/rover-001/readings?start=2026-09-03T00:00:00Z&end=2026-09-04T00:00:00Z&resolution=raw'
        );

        $this->assertSame(400, $response['status']);
        $this->assertSame('INVALID_PARAMETER', json_decode($response['body'], true)['error']['code']);
    }

    public function test_minute_resolution_returns_avg_min_max_shape(): void
    {
        $rover = (new RoverRepository($this->pdo))->getOrCreateByDeviceUid('rover-001');
        $deviceId = (int) $rover['id'];
        $bucketStart = new \DateTimeImmutable('2026-09-03T09:00:00Z');
        (new TelemetryRepository($this->pdo))->insert($deviceId, $bucketStart->modify('+10 seconds'), 24.8, 50.0, 100.0, 50.0, 0);
        (new SummaryRepository($this->pdo))->recomputeBucket($deviceId, 'minute', $bucketStart);

        $response = $this->request(
            'GET',
            '/api/v1/rovers/rover-001/readings?start=2026-09-03T09:00:00Z&end=2026-09-03T09:00:00Z&resolution=minute'
        );

        $body = json_decode($response['body'], true);
        $this->assertSame('minute', $body['resolution']);
        $this->assertArrayHasKey('avg', $body['readings'][0]['temperature_c']);
    }
}
