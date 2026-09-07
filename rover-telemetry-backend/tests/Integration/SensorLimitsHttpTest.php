<?php

declare(strict_types=1);

namespace RoverTelemetry\Tests\Integration;

use RoverTelemetry\Tests\Support\HttpTestCase;

final class SensorLimitsHttpTest extends HttpTestCase
{
    public function test_get_returns_all_four_fields_with_metadata(): void
    {
        $response = $this->request('GET', '/api/v1/config/sensor-limits');

        $this->assertSame(200, $response['status']);
        $body = json_decode($response['body'], true);
        $this->assertEqualsWithDelta(-40.0, (float) $body['temperature_c']['min'], 0.001);
        $this->assertArrayHasKey('updated_at', $body['temperature_c']);
    }

    public function test_put_updates_bounds_and_echoes_new_value(): void
    {
        $response = $this->request('PUT', '/api/v1/config/sensor-limits/temperature_c', ['min' => -30, 'max' => 80]);

        $this->assertSame(200, $response['status']);
        $body = json_decode($response['body'], true);
        $this->assertEqualsWithDelta(-30.0, (float) $body['min'], 0.001);
        $this->assertEqualsWithDelta(80.0, (float) $body['max'], 0.001);

        $reread = $this->request('GET', '/api/v1/config/sensor-limits');
        $this->assertEqualsWithDelta(-30.0, (float) json_decode($reread['body'], true)['temperature_c']['min'], 0.001);
    }

    public function test_put_with_min_not_less_than_max_is_rejected(): void
    {
        $response = $this->request('PUT', '/api/v1/config/sensor-limits/temperature_c', ['min' => 80, 'max' => 80]);

        $this->assertSame(400, $response['status']);
    }

    public function test_put_unknown_field_returns_404(): void
    {
        $response = $this->request('PUT', '/api/v1/config/sensor-limits/not_a_field', ['min' => 0, 'max' => 1]);

        $this->assertSame(404, $response['status']);
    }
}
