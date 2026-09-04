<?php

declare(strict_types=1);

namespace RoverTelemetry\Tests\Integration;

use RoverTelemetry\Repositories\RoverRepository;
use RoverTelemetry\Repositories\SummaryRepository;
use RoverTelemetry\Repositories\TelemetryRepository;
use RoverTelemetry\Tests\Support\DatabaseTestCase;

final class SummaryRepositoryTest extends DatabaseTestCase
{
    public function test_recompute_bucket_aggregates_min_avg_max_and_sample_count(): void
    {
        $rover = (new RoverRepository($this->pdo))->getOrCreateByDeviceUid('rover-001');
        $deviceId = (int) $rover['id'];
        $telemetry = new TelemetryRepository($this->pdo);
        $bucketStart = new \DateTimeImmutable('2026-09-03T10:00:00Z');
        $telemetry->insert($deviceId, $bucketStart->modify('+1 second'), 20.0, 50.0, 100.0, 50.0, 0);
        $telemetry->insert($deviceId, $bucketStart->modify('+30 seconds'), 24.0, 60.0, 120.0, 60.0, 0);

        $repository = new SummaryRepository($this->pdo);
        $repository->recomputeBucket($deviceId, 'minute', $bucketStart);

        $buckets = $repository->bucketsInRange($deviceId, 'minute', $bucketStart, $bucketStart);
        $this->assertCount(1, $buckets);
        $this->assertSame(2, (int) $buckets[0]['sample_count']);
        $this->assertEqualsWithDelta(20.0, (float) $buckets[0]['temp_min'], 0.001);
        $this->assertEqualsWithDelta(24.0, (float) $buckets[0]['temp_max'], 0.001);
        $this->assertEqualsWithDelta(22.0, (float) $buckets[0]['temp_avg'], 0.001);
    }

    public function test_recompute_bucket_leaves_stats_null_when_sensor_not_carried(): void
    {
        $rover = (new RoverRepository($this->pdo))->getOrCreateByDeviceUid('rover-001');
        $deviceId = (int) $rover['id'];
        $telemetry = new TelemetryRepository($this->pdo);
        $bucketStart = new \DateTimeImmutable('2026-09-03T10:00:00Z');
        $telemetry->insert($deviceId, $bucketStart->modify('+1 second'), 20.0, null, null, 50.0, 0);

        $repository = new SummaryRepository($this->pdo);
        $repository->recomputeBucket($deviceId, 'minute', $bucketStart);

        $buckets = $repository->bucketsInRange($deviceId, 'minute', $bucketStart, $bucketStart);
        $this->assertNull($buckets[0]['hum_avg']);
        $this->assertNull($buckets[0]['gas_avg']);
    }

    public function test_recompute_bucket_counts_rising_edges_not_active_rows(): void
    {
        $rover = (new RoverRepository($this->pdo))->getOrCreateByDeviceUid('rover-001');
        $deviceId = (int) $rover['id'];
        $telemetry = new TelemetryRepository($this->pdo);
        $bucketStart = new \DateTimeImmutable('2026-09-03T10:00:00Z');
        $telemetry->insert($deviceId, $bucketStart->modify('+1 second'), 20.0, 50.0, 100.0, 50.0, 0);
        $telemetry->insert($deviceId, $bucketStart->modify('+2 seconds'), 20.0, 50.0, 100.0, 50.0, 1);
        $telemetry->insert($deviceId, $bucketStart->modify('+3 seconds'), 20.0, 50.0, 100.0, 50.0, 1);
        $telemetry->insert($deviceId, $bucketStart->modify('+4 seconds'), 20.0, 50.0, 100.0, 50.0, 0);
        $telemetry->insert($deviceId, $bucketStart->modify('+5 seconds'), 20.0, 50.0, 100.0, 50.0, 1);

        $repository = new SummaryRepository($this->pdo);
        $repository->recomputeBucket($deviceId, 'minute', $bucketStart);

        $buckets = $repository->bucketsInRange($deviceId, 'minute', $bucketStart, $bucketStart);
        $this->assertSame(2, (int) $buckets[0]['obstacle_events']);
    }

    public function test_recompute_bucket_is_idempotent_on_rerun(): void
    {
        $rover = (new RoverRepository($this->pdo))->getOrCreateByDeviceUid('rover-001');
        $deviceId = (int) $rover['id'];
        $telemetry = new TelemetryRepository($this->pdo);
        $bucketStart = new \DateTimeImmutable('2026-09-03T10:00:00Z');
        $telemetry->insert($deviceId, $bucketStart->modify('+1 second'), 20.0, 50.0, 100.0, 50.0, 0);

        $repository = new SummaryRepository($this->pdo);
        $repository->recomputeBucket($deviceId, 'minute', $bucketStart);
        $repository->recomputeBucket($deviceId, 'minute', $bucketStart);

        $this->assertSame(1, (int) $this->pdo->query('SELECT COUNT(*) FROM telemetry_summaries')->fetchColumn());
    }
}
