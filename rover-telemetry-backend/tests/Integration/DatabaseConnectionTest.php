<?php

declare(strict_types=1);

namespace RoverTelemetry\Tests\Integration;

use RoverTelemetry\Tests\Support\DatabaseTestCase;

final class DatabaseConnectionTest extends DatabaseTestCase
{
    public function test_connection_can_query_rovers_table(): void
    {
        $count = (int) $this->pdo->query('SELECT COUNT(*) FROM rovers')->fetchColumn();

        $this->assertSame(0, $count);
    }

    public function test_sensor_limits_are_reseeded_to_defaults(): void
    {
        $count = (int) $this->pdo->query('SELECT COUNT(*) FROM sensor_limits')->fetchColumn();

        $this->assertSame(4, $count);
    }
}
