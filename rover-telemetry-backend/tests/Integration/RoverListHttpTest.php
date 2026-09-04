<?php

declare(strict_types=1);

namespace RoverTelemetry\Tests\Integration;

use RoverTelemetry\Repositories\RoverRepository;
use RoverTelemetry\Tests\Support\HttpTestCase;

final class RoverListHttpTest extends HttpTestCase
{
    public function test_lists_rovers_with_derived_status(): void
    {
        $rovers = new RoverRepository($this->pdo);
        $online = $rovers->getOrCreateByDeviceUid('rover-online');
        $offline = $rovers->getOrCreateByDeviceUid('rover-offline');
        $rovers->updateLastSeen((int) $online['id'], new \DateTimeImmutable('now', new \DateTimeZone('UTC')));
        $rovers->updateLastSeen((int) $offline['id'], new \DateTimeImmutable('-5 minutes', new \DateTimeZone('UTC')));

        $response = $this->request('GET', '/api/v1/rovers');

        $this->assertSame(200, $response['status']);
        $body = json_decode($response['body'], true);
        $byUid = array_column($body, null, 'device_uid');
        $this->assertSame('ONLINE', $byUid['rover-online']['status']);
        $this->assertSame('OFFLINE', $byUid['rover-offline']['status']);
    }

    public function test_never_reported_rover_is_offline_with_null_last_reading(): void
    {
        (new RoverRepository($this->pdo))->getOrCreateByDeviceUid('rover-new');

        $response = $this->request('GET', '/api/v1/rovers');

        $body = json_decode($response['body'], true);
        $byUid = array_column($body, null, 'device_uid');
        $this->assertSame('OFFLINE', $byUid['rover-new']['status']);
        $this->assertNull($byUid['rover-new']['last_reading_at']);
    }
}
