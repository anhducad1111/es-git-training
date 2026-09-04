<?php

declare(strict_types=1);

namespace RoverTelemetry\Tests\Unit;

use PHPUnit\Framework\TestCase;
use RoverTelemetry\Support\ApiException;

final class ApiExceptionTest extends TestCase
{
    public function test_to_array_matches_standard_error_shape(): void
    {
        $exception = new ApiException(404, 'NOT_FOUND', 'Unknown device_uid');

        $this->assertSame(
            ['error' => ['code' => 'NOT_FOUND', 'message' => 'Unknown device_uid', 'request_id' => 'req-123']],
            $exception->toArray('req-123')
        );
        $this->assertSame(404, $exception->httpStatus);
        $this->assertSame('NOT_FOUND', $exception->errorCode);
    }
}
