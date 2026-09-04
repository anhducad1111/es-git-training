<?php

declare(strict_types=1);

namespace RoverTelemetry\Controllers;

use PDO;
use RoverTelemetry\Config;
use RoverTelemetry\Repositories\RoverRepository;

final class RoverController
{
    private RoverRepository $rovers;

    public function __construct(PDO $pdo, private readonly Config $config)
    {
        $this->rovers = new RoverRepository($pdo);
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
