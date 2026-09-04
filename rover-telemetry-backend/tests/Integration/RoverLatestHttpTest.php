<?php

declare(strict_types=1);

namespace RoverTelemetry\Tests\Integration;

use RoverTelemetry\Repositories\RoverRepository;
use RoverTelemetry\Repositories\TelemetryRepository;
use RoverTelemetry\Tests\Support\HttpTestCase;

final class RoverLatestHttpTest extends HttpTestCase
{
    public function test_returns_latest_reading_with_age(): void
    {
        $rovers = new RoverRepository($this->pdo);
        $rover = $rovers->getOrCreateByDeviceUid('rover-001');
        $telemetry = new TelemetryRepository($this->pdo);
        $telemetry->insert((int) $rover['id'], new \DateTimeImmutable('-3 seconds', new \DateTimeZone('UTC')), 25.4, 61.2, 128.0, 34.5, 0);

        $response = $this->request('GET', '/api/v1/rovers/rover-001/latest');

        $this->assertSame(200, $response['status']);
        $body = json_decode($response['body'], true);
        $this->assertSame(25.4, $body['temperature_c']);
        $this->assertGreaterThanOrEqual(3.0, $body['age_seconds']);
        $this->assertLessThan(5.0, $body['age_seconds']);
    }

    public function test_sensor_not_carried_by_rover_returns_null_not_omitted(): void
    {
        $rovers = new RoverRepository($this->pdo);
        $rover = $rovers->getOrCreateByDeviceUid('rover-001');
        (new TelemetryRepository($this->pdo))->insert((int) $rover['id'], new \DateTimeImmutable('now', new \DateTimeZone('UTC')), 25.4, null, null, 34.5, 0);

        $response = $this->request('GET', '/api/v1/rovers/rover-001/latest');

        $body = json_decode($response['body'], true);
        $this->assertArrayHasKey('humidity_pct', $body);
        $this->assertNull($body['humidity_pct']);
    }

    public function test_unknown_device_uid_returns_404(): void
    {
        $response = $this->request('GET', '/api/v1/rovers/does-not-exist/latest');

        $this->assertSame(404, $response['status']);
        $this->assertSame('NOT_FOUND', json_decode($response['body'], true)['error']['code']);
    }

    public function test_rover_that_never_reported_returns_404(): void
    {
        (new RoverRepository($this->pdo))->getOrCreateByDeviceUid('rover-silent');

        $response = $this->request('GET', '/api/v1/rovers/rover-silent/latest');

        $this->assertSame(404, $response['status']);
    }
}
