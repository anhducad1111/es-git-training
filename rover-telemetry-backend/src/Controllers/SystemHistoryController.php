<?php

declare(strict_types=1);

namespace RoverTelemetry\Controllers;

use PDO;
use RoverTelemetry\Repositories\GatewayMetricsRepository;
use RoverTelemetry\Support\ApiException;

final class SystemHistoryController
{
    private GatewayMetricsRepository $gatewayMetrics;

    public function __construct(PDO $pdo)
    {
        $this->gatewayMetrics = new GatewayMetricsRepository($pdo);
    }

    public function history(array $query): array
    {
        if (!isset($query['start']) || !isset($query['end'])) {
            throw new ApiException(400, 'INVALID_PARAMETER', 'start and end are required');
        }

        $start = new \DateTimeImmutable($query['start'], new \DateTimeZone('UTC'));
        $end = new \DateTimeImmutable($query['end'], new \DateTimeZone('UTC'));
        $points = $this->gatewayMetrics->pointsInRange($start, $end);

        return [
            'status' => 200,
            'body' => [
                'resolution' => 'raw',
                'count' => count($points),
                'points' => array_map(fn($p) => [
                    'sampled_at' => (new \DateTimeImmutable($p['sampled_at'], new \DateTimeZone('UTC')))->format('Y-m-d\TH:i:s\Z'),
                    'cpu_load_percent' => (float) $p['cpu_load_percent'],
                    'cpu_temperature_c' => (float) $p['cpu_temperature_c'],
                    'memory_used_percent' => (float) $p['memory_used_percent'],
                    'disk_used_percent' => (float) $p['disk_used_percent'],
                    'ingest_rate_per_min' => (int) $p['ingest_rate_per_min'],
                    'database_size_mb' => (float) $p['database_size_mb'],
                ], $points),
            ],
        ];
    }
}
