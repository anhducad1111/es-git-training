<?php

declare(strict_types=1);

namespace RoverTelemetry\Tests\Integration;

use RoverTelemetry\Repositories\RoverRepository;
use RoverTelemetry\Repositories\TelemetryRepository;
use RoverTelemetry\Repositories\ValidationErrorRepository;
use RoverTelemetry\Tests\Support\DatabaseTestCase;

final class TelemetryRepositoryTest extends DatabaseTestCase
{
    private function makeRoverId(): int
    {
        $rover = (new RoverRepository($this->pdo))->getOrCreateByDeviceUid('rover-001');
        return (int) $rover['id'];
    }

    public function test_insert_stores_new_reading(): void
    {
        $repository = new TelemetryRepository($this->pdo);
        $deviceId = $this->makeRoverId();

        $repository->insert($deviceId, new \DateTimeImmutable('2026-09-03T10:00:00.123Z'), 25.4, 61.2, 128.0, 34.5, 0);

        $latest = $repository->latest($deviceId);
        $this->assertEqualsWithDelta(25.4, (float) $latest['temperature_c'], 0.001);
    }

    public function test_insert_accepts_null_sensor_values(): void
    {
        $repository = new TelemetryRepository($this->pdo);
        $deviceId = $this->makeRoverId();

        $repository->insert($deviceId, new \DateTimeImmutable('2026-09-03T10:00:00.000Z'), 25.4, null, null, 34.5, 0);

        $latest = $repository->latest($deviceId);
        $this->assertNull($latest['humidity_pct']);
        $this->assertNull($latest['gas_ppm']);
    }

    public function test_insert_two_different_timestamps_stores_two_rows(): void
    {
        $repository = new TelemetryRepository($this->pdo);
        $deviceId = $this->makeRoverId();

        $repository->insert($deviceId, new \DateTimeImmutable('2026-09-03T10:00:00.100Z'), 25.4, 61.2, 128.0, 34.5, 0);
        $repository->insert($deviceId, new \DateTimeImmutable('2026-09-03T10:00:00.200Z'), 25.5, 61.3, 129.0, 34.6, 0);

        $this->assertSame(2, (int) $this->pdo->query('SELECT COUNT(*) FROM telemetry_readings')->fetchColumn());
    }

    public function test_insert_same_key_twice_throws(): void
    {
        $repository = new TelemetryRepository($this->pdo);
        $deviceId = $this->makeRoverId();
        $recordedAt = new \DateTimeImmutable('2026-09-03T10:00:00.123Z');

        $repository->insert($deviceId, $recordedAt, 25.4, 61.2, 128.0, 34.5, 0);

        $this->expectException(\PDOException::class);
        $repository->insert($deviceId, $recordedAt, 99.0, 99.0, 99.0, 99.0, 1);
    }

    public function test_count_in_range_matches_range_readings(): void
    {
        $repository = new TelemetryRepository($this->pdo);
        $deviceId = $this->makeRoverId();
        $repository->insert($deviceId, new \DateTimeImmutable('2026-09-03T09:00:00.000Z'), 18.0, 50.0, 100.0, 50.0, 0);
        $repository->insert($deviceId, new \DateTimeImmutable('2026-09-03T10:00:00.000Z'), 20.0, 50.0, 100.0, 50.0, 0);
        $repository->insert($deviceId, new \DateTimeImmutable('2026-09-03T11:00:00.000Z'), 22.0, 50.0, 100.0, 50.0, 0);

        $count = $repository->countInRange(
            $deviceId,
            new \DateTimeImmutable('2026-09-03T09:30:00.000Z'),
            new \DateTimeImmutable('2026-09-03T10:30:00.000Z'),
        );

        $this->assertSame(1, $count);
    }

    public function test_validation_error_is_logged(): void
    {
        $repository = new ValidationErrorRepository($this->pdo);

        $repository->log('rover-001', 'OUT_OF_RANGE', 'temperature_c must be between -40 and 85, got 150', '{"temperature_c":150}');

        $this->assertSame(1, (int) $this->pdo->query('SELECT COUNT(*) FROM validation_errors')->fetchColumn());
    }
}
