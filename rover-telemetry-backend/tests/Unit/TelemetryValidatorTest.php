<?php

declare(strict_types=1);

namespace RoverTelemetry\Tests\Unit;

use PHPUnit\Framework\TestCase;
use RoverTelemetry\Support\ApiException;
use RoverTelemetry\Validation\TelemetryValidator;

final class TelemetryValidatorTest extends TestCase
{
    private function allSensors(): array
    {
        return ['temperature_c', 'humidity_pct', 'gas_ppm', 'distance_cm'];
    }

    private function ranges(): array
    {
        return [
            'temperature_c' => [-40.0, 85.0],
            'humidity_pct' => [0.0, 100.0],
            'gas_ppm' => [0.0, 10000.0],
            'distance_cm' => [2.0, 400.0],
        ];
    }

    private function validPayload(array $overrides = []): array
    {
        return array_merge([
            'device_uid' => 'rover-001',
            'temperature_c' => 25.4,
            'humidity_pct' => 61.2,
            'gas_ppm' => 128.0,
            'distance_cm' => 34.5,
            'auto_brake' => false,
        ], $overrides);
    }

    public function test_valid_payload_normalizes_correctly(): void
    {
        $validator = new TelemetryValidator();

        $clean = $validator->validate($this->validPayload(), $this->allSensors(), $this->ranges());

        $this->assertSame('rover-001', $clean['device_uid']);
        $this->assertSame(25.4, $clean['temperature_c']);
        $this->assertSame(0, $clean['auto_brake']);
        $this->assertArrayNotHasKey('recorded_at', $clean);
    }

    public function test_missing_device_uid_is_rejected(): void
    {
        $validator = new TelemetryValidator();
        $payload = $this->validPayload();
        unset($payload['device_uid']);

        $this->expectException(ApiException::class);
        try {
            $validator->validate($payload, $this->allSensors(), $this->ranges());
        } catch (ApiException $e) {
            $this->assertSame(422, $e->httpStatus);
            $this->assertSame('MISSING_FIELD', $e->errorCode);
            throw $e;
        }
    }

    public function test_recorded_at_in_payload_is_ignored_not_rejected(): void
    {
        $validator = new TelemetryValidator();
        $payload = $this->validPayload(['recorded_at' => '1970-01-01T00:00:00Z']);

        $clean = $validator->validate($payload, $this->allSensors(), $this->ranges());

        $this->assertArrayNotHasKey('recorded_at', $clean);
    }

    public function test_sensor_not_in_enabled_list_is_optional_and_stored_as_null(): void
    {
        $validator = new TelemetryValidator();
        $payload = $this->validPayload();
        unset($payload['gas_ppm'], $payload['distance_cm']);

        $clean = $validator->validate($payload, ['temperature_c', 'humidity_pct'], $this->ranges());

        $this->assertNull($clean['gas_ppm']);
        $this->assertNull($clean['distance_cm']);
        $this->assertSame(25.4, $clean['temperature_c']);
    }

    public function test_sensor_in_enabled_list_but_missing_is_rejected(): void
    {
        $validator = new TelemetryValidator();
        $payload = $this->validPayload();
        unset($payload['humidity_pct']);

        $this->expectException(ApiException::class);
        try {
            $validator->validate($payload, ['temperature_c', 'humidity_pct'], $this->ranges());
        } catch (ApiException $e) {
            $this->assertSame('MISSING_FIELD', $e->errorCode);
            throw $e;
        }
    }

    public function test_temperature_above_range_is_rejected(): void
    {
        $validator = new TelemetryValidator();

        $this->expectException(ApiException::class);
        try {
            $validator->validate($this->validPayload(['temperature_c' => 150]), $this->allSensors(), $this->ranges());
        } catch (ApiException $e) {
            $this->assertSame('OUT_OF_RANGE', $e->errorCode);
            throw $e;
        }
    }

    public function test_range_check_uses_the_supplied_ranges_not_hard_coded_defaults(): void
    {
        $validator = new TelemetryValidator();
        $narrowRanges = array_merge($this->ranges(), ['temperature_c' => [0.0, 10.0]]);

        $this->expectException(ApiException::class);
        $validator->validate($this->validPayload(['temperature_c' => 25.4]), $this->allSensors(), $narrowRanges);
    }

    public function test_auto_brake_must_be_boolean_or_zero_one(): void
    {
        $validator = new TelemetryValidator();

        $this->expectException(ApiException::class);
        $validator->validate($this->validPayload(['auto_brake' => 'yes']), $this->allSensors(), $this->ranges());
    }
}
