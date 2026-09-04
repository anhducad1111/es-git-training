<?php

declare(strict_types=1);

namespace RoverTelemetry\Tests\Unit;

use PHPUnit\Framework\TestCase;
use RoverTelemetry\Config;

final class ConfigTest extends TestCase
{
    public function test_from_env_reads_test_database_settings(): void
    {
        $config = Config::fromEnv();

        $this->assertSame('rover_telemetry_test', $config->dbName);
        $this->assertSame(15, $config->onlineThresholdSeconds);
        $this->assertSame(90, $config->rawRetentionDays);
        $this->assertSame(5, $config->expectedIntervalSeconds);
        $this->assertSame(80.0, $config->cpuTempWarningC);
        $this->assertSame('storage/media_test', $config->mediaStoragePath);
    }
}
