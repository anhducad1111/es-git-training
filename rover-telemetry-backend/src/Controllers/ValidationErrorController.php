<?php

declare(strict_types=1);

namespace RoverTelemetry\Controllers;

use PDO;
use RoverTelemetry\Repositories\ValidationErrorRepository;
use RoverTelemetry\Support\ApiException;

final class ValidationErrorController
{
    private ValidationErrorRepository $repository;

    public function __construct(private readonly PDO $pdo)
    {
        $this->repository = new ValidationErrorRepository($pdo);
    }

    public function list(array $query): array
    {
        $window = $query['window'] ?? '24h';
        $hours = $this->parseWindowToHours($window);
        $since = (new \DateTimeImmutable('now', new \DateTimeZone('UTC')))->modify("-{$hours} hours");
        $errorCode = isset($query['error_code']) && $query['error_code'] !== '' ? $query['error_code'] : null;
        $limit = isset($query['limit']) ? max(1, min(200, (int) $query['limit'])) : 50;

        $rows = $this->repository->listSince($since, $errorCode, $limit);

        $errors = array_map(static fn (array $row) => [
            'id' => (int) $row['id'],
            'device_uid' => $row['device_uid'],
            'received_at' => str_replace(' ', 'T', $row['received_at']) . 'Z',
            'error_code' => $row['error_code'],
            'detail' => $row['detail'],
            'raw_payload' => $row['raw_payload'],
        ], $rows);

        return ['status' => 200, 'body' => ['window' => $window, 'count' => count($errors), 'errors' => $errors]];
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
