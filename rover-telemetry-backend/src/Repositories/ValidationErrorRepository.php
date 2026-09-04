<?php

declare(strict_types=1);

namespace RoverTelemetry\Repositories;

use PDO;

final class ValidationErrorRepository
{
    public function __construct(private readonly PDO $pdo)
    {
    }

    public function log(?string $deviceUid, string $errorCode, string $detail, string $rawPayload): void
    {
        $stmt = $this->pdo->prepare(
            'INSERT INTO validation_errors (device_uid, received_at, error_code, detail, raw_payload) '
            . 'VALUES (:device_uid, :received_at, :error_code, :detail, :raw_payload)'
        );
        $stmt->execute([
            'device_uid' => $deviceUid,
            'received_at' => (new \DateTimeImmutable('now', new \DateTimeZone('UTC')))->format('Y-m-d H:i:s.v'),
            'error_code' => $errorCode,
            'detail' => mb_substr($detail, 0, 255),
            'raw_payload' => mb_substr($rawPayload, 0, 4096),
        ]);
    }
}
