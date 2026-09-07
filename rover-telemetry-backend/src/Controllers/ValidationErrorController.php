<?php

declare(strict_types=1);

namespace RoverTelemetry\Controllers;

use PDO;
use RoverTelemetry\Support\ApiException;

final class ValidationErrorController
{
    public function __construct(private readonly PDO $pdo)
    {
    }

    public function summary(array $query): array
    {
        $window = $query['window'] ?? '24h';
        $hours = $this->parseWindowToHours($window);
        $since = (new \DateTimeImmutable('now', new \DateTimeZone('UTC')))->modify("-{$hours} hours");

        $stmt = $this->pdo->prepare(
            'SELECT error_code, COUNT(*) AS c FROM validation_errors WHERE received_at >= :since GROUP BY error_code'
        );
        $stmt->execute(['since' => $since->format('Y-m-d H:i:s.v')]);

        $byCode = [];
        $total = 0;
        foreach ($stmt->fetchAll() as $row) {
            $byCode[$row['error_code']] = (int) $row['c'];
            $total += (int) $row['c'];
        }

        return ['status' => 200, 'body' => ['window' => $window, 'total' => $total, 'by_code' => (object) $byCode]];
    }

    private function parseWindowToHours(string $window): int
    {
        if (!preg_match('/^(\d+)([hd])$/', $window, $m)) {
            throw new ApiException(400, 'INVALID_PARAMETER', "window must look like '24h' or '7d'");
        }

        return $m[2] === 'd' ? ((int) $m[1]) * 24 : (int) $m[1];
    }
}
