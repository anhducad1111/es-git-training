<?php

declare(strict_types=1);

namespace RoverTelemetry\Tests\Integration;

use RoverTelemetry\Repositories\SensorLimitsRepository;
use RoverTelemetry\Tests\Support\DatabaseTestCase;

final class SensorLimitsRepositoryTest extends DatabaseTestCase
{
    public function test_all_returns_min_max_pairs_for_validator_use(): void
    {
        $repository = new SensorLimitsRepository($this->pdo);

        $ranges = $repository->all();

        $this->assertSame([-40.0, 85.0], $ranges['temperature_c']);
        $this->assertSame([2.0, 400.0], $ranges['distance_cm']);
    }

    public function test_all_with_metadata_includes_updated_at(): void
    {
        $repository = new SensorLimitsRepository($this->pdo);

        $metadata = $repository->allWithMetadata();

        $this->assertSame(-40.0, $metadata['temperature_c']['min']);
        $this->assertSame(85.0, $metadata['temperature_c']['max']);
        $this->assertArrayHasKey('updated_at', $metadata['temperature_c']);
    }

    public function test_update_changes_bounds_and_returns_updated_row(): void
    {
        $repository = new SensorLimitsRepository($this->pdo);

        $updated = $repository->update('temperature_c', -30.0, 80.0);

        $this->assertSame(-30.0, (float) $updated['min_value']);
        $this->assertSame(80.0, (float) $updated['max_value']);
        $ranges = $repository->all();
        $this->assertSame([-30.0, 80.0], $ranges['temperature_c']);
    }

    public function test_update_unknown_field_returns_null(): void
    {
        $repository = new SensorLimitsRepository($this->pdo);

        $this->assertNull($repository->update('does_not_exist', 0.0, 1.0));
    }
}
