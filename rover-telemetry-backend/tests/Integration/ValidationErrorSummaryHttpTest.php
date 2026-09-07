<?php

declare(strict_types=1);

namespace RoverTelemetry\Tests\Integration;

use RoverTelemetry\Repositories\ValidationErrorRepository;
use RoverTelemetry\Tests\Support\HttpTestCase;

final class ValidationErrorSummaryHttpTest extends HttpTestCase
{
    public function test_counts_errors_within_window_by_code(): void
    {
        $repository = new ValidationErrorRepository($this->pdo);
        $repository->log('rover-001', 'OUT_OF_RANGE', 'too high', '{}');
        $repository->log('rover-001', 'OUT_OF_RANGE', 'too low', '{}');
        $repository->log('rover-002', 'MISSING_FIELD', 'no humidity', '{}');

        $response = $this->request('GET', '/api/v1/validation-errors/summary?window=24h');

        $this->assertSame(200, $response['status']);
        $body = json_decode($response['body'], true);
        $this->assertSame(3, $body['total']);
        $this->assertSame(2, $body['by_code']['OUT_OF_RANGE']);
        $this->assertSame(1, $body['by_code']['MISSING_FIELD']);
    }

    public function test_malformed_window_is_rejected(): void
    {
        $response = $this->request('GET', '/api/v1/validation-errors/summary?window=bogus');

        $this->assertSame(400, $response['status']);
    }
}
