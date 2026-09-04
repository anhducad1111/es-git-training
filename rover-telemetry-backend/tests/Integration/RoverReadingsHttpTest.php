<?php

declare(strict_types=1);

namespace RoverTelemetry\Tests\Integration;

use RoverTelemetry\Repositories\RoverRepository;
use RoverTelemetry\Repositories\TelemetryRepository;
use RoverTelemetry\Tests\Support\HttpTestCase;

final class RoverReadingsHttpTest extends HttpTestCase
{
    private function seedReadings(string $deviceUid, int $count): int
    {
        $rovers = new RoverRepository($this->pdo);
        $rover = $rovers->getOrCreateByDeviceUid($deviceUid);
        $telemetry = new TelemetryRepository($this->pdo);
        $start = new \DateTimeImmutable('-10 minutes', new \DateTimeZone('UTC'));
        for ($i = 0; $i < $count; $i++) {
            $telemetry->insert((int) $rover['id'], $start->modify("+{$i} seconds"), 20.0 + $i * 0.1, 50.0, 100.0, 50.0, 0);
        }

        return (int) $rover['id'];
    }

    public function test_default_limit_returns_most_recent_100_descending(): void
    {
        $this->seedReadings('rover-001', 150);

        $response = $this->request('GET', '/api/v1/rovers/rover-001/readings');

        $this->assertSame(200, $response['status']);
        $body = json_decode($response['body'], true);
        $this->assertSame(100, $body['count']);
        $this->assertGreaterThan($body['readings'][1]['recorded_at'], $body['readings'][0]['recorded_at']);
    }

    public function test_explicit_limit_and_ascending_order(): void
    {
        $this->seedReadings('rover-001', 10);

        $response = $this->request('GET', '/api/v1/rovers/rover-001/readings?limit=5&order=asc');

        $body = json_decode($response['body'], true);
        $this->assertSame(5, $body['count']);
        $this->assertLessThan($body['readings'][1]['recorded_at'], $body['readings'][0]['recorded_at']);
    }

    public function test_limit_over_5000_is_rejected(): void
    {
        $this->seedReadings('rover-001', 1);

        $response = $this->request('GET', '/api/v1/rovers/rover-001/readings?limit=5001');

        $this->assertSame(400, $response['status']);
        $this->assertSame('INVALID_PARAMETER', json_decode($response['body'], true)['error']['code']);
    }

    public function test_unknown_device_uid_returns_404(): void
    {
        $response = $this->request('GET', '/api/v1/rovers/does-not-exist/readings');

        $this->assertSame(404, $response['status']);
    }
}
