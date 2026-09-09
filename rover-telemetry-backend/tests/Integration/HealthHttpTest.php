<?php

declare(strict_types=1);

namespace RoverTelemetry\Tests\Integration;

use RoverTelemetry\Tests\Support\HttpTestCase;

final class HealthHttpTest extends HttpTestCase
{
    public function test_health_returns_ok(): void
    {
        $response = $this->request('GET', '/api/v1/health');

        $this->assertSame(200, $response['status']);
        $body = json_decode($response['body'], true);
        $this->assertSame('ok', $body['status']);
        $this->assertSame('ok', $body['database']);
        $this->assertIsInt($body['uptime_seconds']);
    }

    public function test_system_returns_expected_shape(): void
    {
        $response = $this->request('GET', '/api/v1/system');

        $this->assertSame(200, $response['status']);
        $body = json_decode($response['body'], true);
        $this->assertArrayHasKey('cpu_load_percent', $body);
        $this->assertArrayHasKey('services', $body);
        // retention.php has not been run manually against this project yet (Task 25),
        // so its marker file doesn't exist — aggregate.lastrun does (Tasks 14/17's
        // manual verification runs already created it), so that one is asserted 'ok'.
        $this->assertSame('never_run', $body['services']['retention_job']['status']);
        $this->assertSame('ok', $body['services']['aggregate_job']['status']);
        // Both marker files exist by the time this runs (Tasks 14/17 and 25's manual
        // verification runs have already created storage/aggregate.lastrun and
        // storage/retention.lastrun), so just check the shape rather than a specific
        // never_run/ok value that would depend on execution order across sessions.
        $this->assertContains($body['services']['aggregate_job']['status'], ['ok', 'never_run']);
        $this->assertContains($body['services']['retention_job']['status'], ['ok', 'never_run']);
        $this->assertArrayHasKey('last_run', $body['services']['aggregate_job']);
        $this->assertArrayHasKey('last_run', $body['services']['retention_job']);
        $this->assertIsArray($body['warnings']);
    }
}
