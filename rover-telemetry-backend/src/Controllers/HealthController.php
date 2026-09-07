<?php

declare(strict_types=1);

namespace RoverTelemetry\Controllers;

use PDO;

final class HealthController
{
    private static float $startedAt;

    public function __construct(private readonly PDO $pdo)
    {
        self::$startedAt ??= microtime(true);
    }

    public function health(): array
    {
        try {
            $this->pdo->query('SELECT 1');
            $databaseOk = true;
        } catch (\Throwable) {
            $databaseOk = false;
        }

        return [
            'status' => $databaseOk ? 200 : 503,
            'body' => [
                'status' => $databaseOk ? 'ok' : 'error',
                'database' => $databaseOk ? 'ok' : 'error',
                'api' => 'ok',
                'uptime_seconds' => (int) round(microtime(true) - self::$startedAt),
            ],
        ];
    }
}
