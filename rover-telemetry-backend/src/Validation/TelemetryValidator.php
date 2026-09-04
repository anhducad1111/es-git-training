<?php

declare(strict_types=1);

namespace RoverTelemetry\Validation;

use RoverTelemetry\Support\ApiException;

final class TelemetryValidator
{
    private const SENSOR_FIELDS = ['temperature_c', 'humidity_pct', 'gas_ppm', 'distance_cm'];

    public function validate(array $payload, array $enabledSensors, array $ranges): array
    {
        $deviceUid = $payload['device_uid'] ?? null;
        if (!is_string($deviceUid) || $deviceUid === '') {
            throw new ApiException(422, 'MISSING_FIELD', "Field 'device_uid' is required");
        }

        if (!array_key_exists('auto_brake', $payload) || $payload['auto_brake'] === null) {
            throw new ApiException(422, 'MISSING_FIELD', "Field 'auto_brake' is required");
        }

        $clean = ['device_uid' => $deviceUid];

        foreach (self::SENSOR_FIELDS as $field) {
            $isEnabled = in_array($field, $enabledSensors, true);
            $present = array_key_exists($field, $payload) && $payload[$field] !== null;

            if (!$present) {
                if ($isEnabled) {
                    throw new ApiException(422, 'MISSING_FIELD', "Field '{$field}' is required for this rover");
                }
                $clean[$field] = null;
                continue;
            }

            $value = $payload[$field];
            if (!is_numeric($value)) {
                throw new ApiException(422, 'OUT_OF_RANGE', "Field '{$field}' must be numeric");
            }
            $value = (float) $value;
            [$min, $max] = $ranges[$field];
            if ($value < $min || $value > $max) {
                throw new ApiException(422, 'OUT_OF_RANGE', "{$field} must be between {$min} and {$max}, got {$value}");
            }
            $clean[$field] = $value;
        }

        $autoBrake = $payload['auto_brake'];
        if (!in_array($autoBrake, [0, 1, true, false], true)) {
            throw new ApiException(422, 'OUT_OF_RANGE', "Field 'auto_brake' must be a boolean or 0/1");
        }
        $clean['auto_brake'] = $autoBrake ? 1 : 0;

        return $clean;
    }
}
