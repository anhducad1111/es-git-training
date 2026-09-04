<?php

declare(strict_types=1);

namespace RoverTelemetry\Tests\Support;

use PDO;
use PHPUnit\Framework\TestCase;
use RoverTelemetry\Config;
use RoverTelemetry\Database;

abstract class DatabaseTestCase extends TestCase
{
    protected PDO $pdo;
    protected Config $config;

    protected function setUp(): void
    {
        $this->config = Config::fromEnv();
        Database::reset();
        $this->pdo = Database::connection($this->config);

        $this->pdo->exec('SET FOREIGN_KEY_CHECKS=0');
        foreach (['telemetry_readings', 'telemetry_summaries', 'validation_errors', 'media_files', 'gateway_metrics', 'rovers'] as $table) {
            $this->pdo->exec("TRUNCATE TABLE {$table}");
        }
        $this->pdo->exec('SET FOREIGN_KEY_CHECKS=1');

        $this->pdo->exec(
            "INSERT INTO sensor_limits (field, min_value, max_value) VALUES "
            . "('temperature_c', -40, 85), ('humidity_pct', 0, 100), ('gas_ppm', 0, 10000), ('distance_cm', 2, 400) "
            . "ON DUPLICATE KEY UPDATE min_value = VALUES(min_value), max_value = VALUES(max_value)"
        );

        $this->clearMediaTestStorage();
    }

    private function clearMediaTestStorage(): void
    {
        $root = __DIR__ . '/../../' . $this->config->mediaStoragePath;
        if (!is_dir($root)) {
            return;
        }
        $iterator = new \RecursiveIteratorIterator(
            new \RecursiveDirectoryIterator($root, \FilesystemIterator::SKIP_DOTS),
            \RecursiveIteratorIterator::CHILD_FIRST
        );
        foreach ($iterator as $item) {
            $item->isDir() ? @rmdir($item->getPathname()) : @unlink($item->getPathname());
        }
    }
}
