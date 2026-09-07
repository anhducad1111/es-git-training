<?php

declare(strict_types=1);

namespace RoverTelemetry\Controllers;

use PDO;
use RoverTelemetry\Config;
use RoverTelemetry\Support\HostMetrics;

final class SystemController
{
    public function __construct(private readonly PDO $pdo, private readonly Config $config)
    {
    }

    public function system(): array
    {
        $metrics = HostMetrics::collect($this->pdo, $this->config->dbName);
        $rowCount = (int) $this->pdo->query('SELECT COUNT(*) FROM telemetry_readings')->fetchColumn();

        $warnings = [];
        if ($metrics['cpu_temperature_c'] > $this->config->cpuTempWarningC) {
            $warnings[] = ['metric' => 'cpu_temperature_c', 'value' => $metrics['cpu_temperature_c'], 'limit' => $this->config->cpuTempWarningC];
        }
        if ($metrics['disk_used_percent'] > $this->config->diskUsedWarningPercent) {
            $warnings[] = ['metric' => 'disk_used_percent', 'value' => $metrics['disk_used_percent'], 'limit' => $this->config->diskUsedWarningPercent];
        }
        if ($metrics['memory_used_percent'] > $this->config->memoryUsedWarningPercent) {
            $warnings[] = ['metric' => 'memory_used_percent', 'value' => $metrics['memory_used_percent'], 'limit' => $this->config->memoryUsedWarningPercent];
        }

        return [
            'status' => 200,
            'body' => [
                'cpu_load_percent' => $metrics['cpu_load_percent'],
                'cpu_temperature_c' => $metrics['cpu_temperature_c'],
                'memory' => ['used_percent' => $metrics['memory_used_percent']],
                'disk' => ['used_percent' => $metrics['disk_used_percent']],
                'ingest_rate_per_minute' => $metrics['ingest_rate_per_min'],
                'database' => ['size_mb' => $metrics['database_size_mb'], 'row_count' => $rowCount],
                'services' => [
                    'api' => 'ok',
                    'database' => 'ok',
                    'aggregate_job' => $this->jobStatus('aggregate'),
                    'retention_job' => $this->jobStatus('retention'),
                ],
                'warnings' => $warnings,
            ],
        ];
    }

    private function jobStatus(string $job): array
    {
        $markerFile = __DIR__ . "/../../storage/{$job}.lastrun";
        if (!is_file($markerFile)) {
            return ['status' => 'never_run', 'last_run' => null];
        }

        return ['status' => 'ok', 'last_run' => trim((string) file_get_contents($markerFile))];
    }
}
