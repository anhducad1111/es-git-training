<?php

declare(strict_types=1);

namespace RoverTelemetry\Controllers;

use PDO;
use RoverTelemetry\Repositories\RoverRepository;
use RoverTelemetry\Repositories\SensorLimitsRepository;
use RoverTelemetry\Repositories\TelemetryRepository;
use RoverTelemetry\Repositories\ValidationErrorRepository;
use RoverTelemetry\Support\ApiException;
use RoverTelemetry\Validation\TelemetryValidator;

final class TelemetryController
{
    private RoverRepository $rovers;
    private TelemetryRepository $telemetry;
    private ValidationErrorRepository $validationErrors;
    private SensorLimitsRepository $sensorLimits;
    private TelemetryValidator $validator;

    public function __construct(private readonly PDO $pdo)
    {
        $this->rovers = new RoverRepository($pdo);
        $this->telemetry = new TelemetryRepository($pdo);
        $this->validationErrors = new ValidationErrorRepository($pdo);
        $this->sensorLimits = new SensorLimitsRepository($pdo);
        $this->validator = new TelemetryValidator();
    }

    public function ingest(array $body): array
    {
        if (!isset($body['device_uid']) || !is_string($body['device_uid']) || $body['device_uid'] === '') {
            throw new ApiException(422, 'MISSING_FIELD', "Field 'device_uid' is required");
        }

        $rover = $this->rovers->getOrCreateByDeviceUid($body['device_uid']);
        $enabledSensors = explode(',', (string) $rover['enabled_sensors']);
        $ranges = $this->sensorLimits->all();

        try {
            $clean = $this->validator->validate($body, $enabledSensors, $ranges);
        } catch (ApiException $e) {
            $this->validationErrors->log($body['device_uid'], $e->errorCode, $e->getMessage(), json_encode($body) ?: '');
            throw $e;
        }

        // Stamped here, not read from the payload — spec §4.1: the ESP32 build has no RTC.
        $recordedAt = new \DateTimeImmutable('now', new \DateTimeZone('UTC'));

        $this->pdo->beginTransaction();
        try {
            $this->telemetry->insert(
                (int) $rover['id'],
                $recordedAt,
                $clean['temperature_c'],
                $clean['humidity_pct'],
                $clean['gas_ppm'],
                $clean['distance_cm'],
                $clean['auto_brake'],
            );
            $this->rovers->updateLastSeen((int) $rover['id'], $recordedAt);
            $this->pdo->commit();
        } catch (\Throwable $e) {
            $this->pdo->rollBack();
            throw $e;
        }

        return [
            'status' => 201,
            'body' => [
                'success' => true,
                'device_uid' => $rover['device_uid'],
                'recorded_at' => $recordedAt->format('Y-m-d\TH:i:s.v\Z'),
            ],
        ];
    }
}
