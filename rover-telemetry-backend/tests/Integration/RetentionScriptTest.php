<?php

declare(strict_types=1);

namespace RoverTelemetry\Tests\Integration;

use RoverTelemetry\Repositories\RoverRepository;
use RoverTelemetry\Repositories\TelemetryRepository;
use RoverTelemetry\Repositories\ValidationErrorRepository;
use RoverTelemetry\Tests\Support\DatabaseTestCase;

final class RetentionScriptTest extends DatabaseTestCase
{
    public function test_retention_removes_old_raw_readings_but_keeps_recent_ones(): void
    {
        $rover = (new RoverRepository($this->pdo))->getOrCreateByDeviceUid('rover-001');
        $deviceId = (int) $rover['id'];
        $telemetry = new TelemetryRepository($this->pdo);
        $telemetry->insert($deviceId, new \DateTimeImmutable('-100 days', new \DateTimeZone('UTC')), 20.0, 50.0, 100.0, 50.0, 0);
        $telemetry->insert($deviceId, new \DateTimeImmutable('-1 day', new \DateTimeZone('UTC')), 20.0, 50.0, 100.0, 50.0, 0);

        $output = shell_exec(
            'cd "' . dirname(__DIR__, 2) . '" && "C:/xampp/php/php.exe" bin/retention.php'
        );

        $this->assertStringContainsString('removed', (string) $output);
        $this->assertSame(1, (int) $this->pdo->query('SELECT COUNT(*) FROM telemetry_readings')->fetchColumn());
        $this->assertTrue(is_file(dirname(__DIR__, 2) . '/storage/retention.lastrun'));
    }

    public function test_retention_removes_old_validation_errors(): void
    {
        $repository = new ValidationErrorRepository($this->pdo);
        $repository->log('rover-001', 'OUT_OF_RANGE', 'old', '{}');
        $this->pdo->exec("UPDATE validation_errors SET received_at = DATE_SUB(UTC_TIMESTAMP(), INTERVAL 40 DAY)");

        shell_exec('cd "' . dirname(__DIR__, 2) . '" && "C:/xampp/php/php.exe" bin/retention.php');

        $this->assertSame(0, (int) $this->pdo->query('SELECT COUNT(*) FROM validation_errors')->fetchColumn());
    }
}
