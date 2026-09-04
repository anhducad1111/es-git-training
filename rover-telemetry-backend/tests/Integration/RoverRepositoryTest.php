<?php

declare(strict_types=1);

namespace RoverTelemetry\Tests\Integration;

use RoverTelemetry\Repositories\RoverRepository;
use RoverTelemetry\Tests\Support\DatabaseTestCase;

final class RoverRepositoryTest extends DatabaseTestCase
{
    public function test_get_or_create_registers_unknown_device_once_with_default_sensors(): void
    {
        $repository = new RoverRepository($this->pdo);

        $first = $repository->getOrCreateByDeviceUid('rover-001');
        $second = $repository->getOrCreateByDeviceUid('rover-001');

        $this->assertSame($first['id'], $second['id']);
        $this->assertSame(1, (int) $this->pdo->query('SELECT COUNT(*) FROM rovers')->fetchColumn());
        $this->assertSame(
            ['temperature_c', 'humidity_pct', 'gas_ppm', 'distance_cm'],
            explode(',', $first['enabled_sensors'])
        );
        $this->assertNull($first['last_seen_at']);
    }

    public function test_find_by_device_uid_returns_null_when_missing(): void
    {
        $repository = new RoverRepository($this->pdo);

        $this->assertNull($repository->findByDeviceUid('does-not-exist'));
    }

    public function test_all_lists_registered_rovers(): void
    {
        $repository = new RoverRepository($this->pdo);
        $repository->getOrCreateByDeviceUid('rover-001');
        $repository->getOrCreateByDeviceUid('rover-002');

        $this->assertCount(2, $repository->all());
    }

    public function test_update_last_seen_persists_timestamp(): void
    {
        $repository = new RoverRepository($this->pdo);
        $rover = $repository->getOrCreateByDeviceUid('rover-001');
        $at = new \DateTimeImmutable('2026-09-04T10:00:00.123Z');

        $repository->updateLastSeen((int) $rover['id'], $at);

        $refreshed = $repository->findByDeviceUid('rover-001');
        $this->assertSame('2026-09-04 10:00:00.123', $refreshed['last_seen_at']);
    }
}
