<?php

declare(strict_types=1);

namespace RoverTelemetry\Support;

use RuntimeException;

final class ApiException extends RuntimeException
{
    public function __construct(
        public readonly int $httpStatus,
        public readonly string $errorCode,
        string $message,
    ) {
        parent::__construct($message);
    }

    public function toArray(string $requestId): array
    {
        return [
            'error' => [
                'code' => $this->errorCode,
                'message' => $this->getMessage(),
                'request_id' => $requestId,
            ],
        ];
    }
}
