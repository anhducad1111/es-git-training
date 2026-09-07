<?php

declare(strict_types=1);

namespace RoverTelemetry\Tests\Integration;

use RoverTelemetry\Repositories\RoverRepository;
use RoverTelemetry\Repositories\TelemetryRepository;
use RoverTelemetry\Tests\Support\HttpTestCase;

final class RoverEventsHttpTest extends HttpTestCase
{
    public function test_brake_hold_produces_one_engaged_and_one_cleared_event(): void
    {
        $rover = (new RoverRepository($this->pdo))->getOrCreateByDeviceUid('rover-001');
        $deviceId = (int) $rover['id'];
        $telemetry = new TelemetryRepository($this->pdo);
        $start = new \DateTimeImmutable('-2 hours', new \DateTimeZone('UTC'));
        $telemetry->insert($deviceId, $start, 20.0, 50.0, 100.0, 50.0, 0);
        $telemetry->insert($deviceId, $start->modify('+1 second'), 20.0, 50.0, 100.0, 18.4, 1);
        $telemetry->insert($deviceId, $start->modify('+2 seconds'), 20.0, 50.0, 100.0, 18.0, 1);
        $telemetry->insert($deviceId, $start->modify('+3 seconds'), 20.0, 50.0, 100.0, 50.0, 0);

        $response = $this->request('GET', '/api/v1/rovers/rover-001/events');

        $body = json_decode($response['body'], true);
        $types = array_column($body['events'], 'type');
        $this->assertSame(1, count(array_filter($types, fn($t) => $t === 'auto_brake_engaged')));
        $this->assertSame(1, count(array_filter($types, fn($t) => $t === 'auto_brake_cleared')));
    }

    public function test_threshold_exceeded_event_reports_the_breaching_sensor(): void
    {
        $rover = (new RoverRepository($this->pdo))->getOrCreateByDeviceUid('rover-001');
        $deviceId = (int) $rover['id'];
        $this->pdo->exec("UPDATE sensor_limits SET max_value = 400 WHERE field = 'gas_ppm'");
        (new TelemetryRepository($this->pdo))->insert($deviceId, new \DateTimeImmutable('-1 hour', new \DateTimeZone('UTC')), 20.0, 50.0, 402.0, 50.0, 0);

        $response = $this->request('GET', '/api/v1/rovers/rover-001/events');

        $body = json_decode($response['body'], true);
        $event = array_values(array_filter($body['events'], fn($e) => $e['type'] === 'threshold_exceeded'))[0];
        $this->assertSame('gas_ppm', $event['sensor']);
        $this->assertEqualsWithDelta(402.0, (float) $event['value'], 0.001);
    }

    public function test_gap_beyond_twice_expected_interval_reports_reconnected(): void
    {
        $rover = (new RoverRepository($this->pdo))->getOrCreateByDeviceUid('rover-001');
        $deviceId = (int) $rover['id'];
        $telemetry = new TelemetryRepository($this->pdo);
        $telemetry->insert($deviceId, new \DateTimeImmutable('-1 hour', new \DateTimeZone('UTC')), 20.0, 50.0, 100.0, 50.0, 0);
        $telemetry->insert($deviceId, new \DateTimeImmutable('-1 hour +372 seconds', new \DateTimeZone('UTC')), 20.0, 50.0, 100.0, 50.0, 0);

        $response = $this->request('GET', '/api/v1/rovers/rover-001/events');

        $body = json_decode($response['body'], true);
        $reconnected = array_values(array_filter($body['events'], fn($e) => $e['type'] === 'reconnected'));
        $this->assertNotEmpty($reconnected);
        $this->assertSame(372, $reconnected[0]['gap_seconds']);
    }

    public function test_unknown_device_uid_returns_404(): void
    {
        $response = $this->request('GET', '/api/v1/rovers/does-not-exist/events');

        $this->assertSame(404, $response['status']);
    }
}
