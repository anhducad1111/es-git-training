<?php

declare(strict_types=1);

namespace RoverTelemetry\Controllers;

use PDO;
use RoverTelemetry\Config;
use RoverTelemetry\Repositories\RoverRepository;
use RoverTelemetry\Repositories\TelemetryRepository;
use RoverTelemetry\Support\ApiException;

final class RoverController
{
    private RoverRepository $rovers;
    private TelemetryRepository $telemetry;

    public function __construct(PDO $pdo, private readonly Config $config)
    {
        $this->rovers = new RoverRepository($pdo);
        $this->telemetry = new TelemetryRepository($pdo);
    }

    public function list(): array
    {
        $now = new \DateTimeImmutable('now', new \DateTimeZone('UTC'));
        $body = array_map(function (array $rover) use ($now) {
            return [
                'device_uid' => $rover['device_uid'],
                'name' => $rover['name'],
                'firmware_version' => $rover['firmware_version'],
                'last_reading_at' => $rover['last_seen_at'] !== null
                    ? (new \DateTimeImmutable($rover['last_seen_at'], new \DateTimeZone('UTC')))->format('Y-m-d\TH:i:s.v\Z')
                    : null,
                'status' => $this->statusFor($rover['last_seen_at'], $now),
            ];
        }, $this->rovers->all());

        return ['status' => 200, 'body' => $body];
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

    private function statusFor(?string $lastSeenAt, \DateTimeImmutable $now): string
    {
        if ($lastSeenAt === null) {
            return 'OFFLINE';
        }

        $age = $now->getTimestamp() - (new \DateTimeImmutable($lastSeenAt, new \DateTimeZone('UTC')))->getTimestamp();

        if ($age <= $this->config->onlineThresholdSeconds) {
            return 'ONLINE';
        }
        if ($age <= $this->config->degradedThresholdSeconds) {
            return 'DEGRADED';
        }

        return 'OFFLINE';
    }
}
