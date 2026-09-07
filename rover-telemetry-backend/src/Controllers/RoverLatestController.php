<?php

declare(strict_types=1);

namespace RoverTelemetry\Controllers;

use PDO;
use RoverTelemetry\Repositories\RoverRepository;
use RoverTelemetry\Repositories\TelemetryRepository;
use RoverTelemetry\Support\ApiException;

final class RoverLatestController
{
    private RoverRepository $rovers;
    private TelemetryRepository $telemetry;

    public function __construct(PDO $pdo)
    {
        $this->rovers = new RoverRepository($pdo);
        $this->telemetry = new TelemetryRepository($pdo);
    }

    public function latest(array $params): array
    {
        $rover = $this->rovers->findByDeviceUid($params['device_uid']);
        if ($rover === null) {
            throw new ApiException(404, 'NOT_FOUND', "Unknown device_uid '{$params['device_uid']}'");
        }

        $reading = $this->telemetry->latest((int) $rover['id']);
        if ($reading === null) {
            throw new ApiException(404, 'NOT_FOUND', "Rover '{$rover['device_uid']}' has never reported");
        }

        $recordedAt = new \DateTimeImmutable($reading['recorded_at'], new \DateTimeZone('UTC'));
        $now = new \DateTimeImmutable('now', new \DateTimeZone('UTC'));

        return [
            'status' => 200,
            'body' => [
                'device_uid' => $rover['device_uid'],
                'recorded_at' => $recordedAt->format('Y-m-d\TH:i:s.v\Z'),
                'age_seconds' => round((float) $now->format('U.v') - (float) $recordedAt->format('U.v'), 1),
                'temperature_c' => $reading['temperature_c'] !== null ? (float) $reading['temperature_c'] : null,
                'humidity_pct' => $reading['humidity_pct'] !== null ? (float) $reading['humidity_pct'] : null,
                'gas_ppm' => $reading['gas_ppm'] !== null ? (float) $reading['gas_ppm'] : null,
                'distance_cm' => $reading['distance_cm'] !== null ? (float) $reading['distance_cm'] : null,
                'auto_brake' => (bool) $reading['auto_brake'],
            ],
        ];
    }
}
