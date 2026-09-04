<?php

declare(strict_types=1);

namespace RoverTelemetry\Tests\Integration;

use RoverTelemetry\Repositories\RoverRepository;
use RoverTelemetry\Repositories\SummaryRepository;
use RoverTelemetry\Repositories\TelemetryRepository;
use RoverTelemetry\Tests\Support\HttpTestCase;

final class RoverSummaryHttpTest extends HttpTestCase
{
    public function test_returns_day_bucket_with_known_stats(): void
    {
        $rovers = new RoverRepository($this->pdo);
        $rover = $rovers->getOrCreateByDeviceUid('rover-001');
        $deviceId = (int) $rover['id'];
        $telemetry = new TelemetryRepository($this->pdo);
        $dayStart = new \DateTimeImmutable('2026-09-03T00:00:00Z');
        $telemetry->insert($deviceId, $dayStart->modify('+1 hour'), 18.2, 40.0, 95.0, 4.0, 0);
        $telemetry->insert($deviceId, $dayStart->modify('+2 hours'), 31.7, 72.4, 402.0, 400.0, 1);
        (new SummaryRepository($this->pdo))->recomputeBucket($deviceId, 'day', $dayStart);

        $response = $this->request('GET', '/api/v1/rovers/rover-001/summary?granularity=day&start=2026-09-03&end=2026-09-03');

        $this->assertSame(200, $response['status']);
        $body = json_decode($response['body'], true);
        $this->assertCount(1, $body['buckets']);
        $this->assertSame(2, $body['buckets'][0]['sample_count']);
        $this->assertEqualsWithDelta(18.2, $body['buckets'][0]['temperature_c']['min'], 0.001);
        $this->assertEqualsWithDelta(31.7, $body['buckets'][0]['temperature_c']['max'], 0.001);
        $this->assertSame(1, $body['buckets'][0]['obstacle_events']);
    }

    public function test_missing_start_or_end_is_rejected(): void
    {
        (new RoverRepository($this->pdo))->getOrCreateByDeviceUid('rover-001');

        $response = $this->request('GET', '/api/v1/rovers/rover-001/summary?granularity=day');

        $this->assertSame(400, $response['status']);
        $this->assertSame('INVALID_PARAMETER', json_decode($response['body'], true)['error']['code']);
    }
}
