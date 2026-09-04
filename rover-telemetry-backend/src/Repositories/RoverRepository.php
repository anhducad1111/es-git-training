<?php

declare(strict_types=1);

namespace RoverTelemetry\Repositories;

use PDO;

final class RoverRepository
{
    public function __construct(private readonly PDO $pdo)
    {
    }

    public function getOrCreateByDeviceUid(string $deviceUid): array
    {
        $rover = $this->findByDeviceUid($deviceUid);
        if ($rover !== null) {
            return $rover;
        }

        $insert = $this->pdo->prepare('INSERT INTO rovers (device_uid) VALUES (:device_uid)');
        $insert->execute(['device_uid' => $deviceUid]);

        return $this->findByDeviceUid($deviceUid);
    }

    public function findByDeviceUid(string $deviceUid): ?array
    {
        $stmt = $this->pdo->prepare(
            'SELECT id, device_uid, name, firmware_version, enabled_sensors, last_seen_at, created_at FROM rovers WHERE device_uid = :device_uid'
        );
        $stmt->execute(['device_uid' => $deviceUid]);
        $row = $stmt->fetch();

        return $row === false ? null : $row;
    }

    public function all(): array
    {
        return $this->pdo
            ->query('SELECT id, device_uid, name, firmware_version, enabled_sensors, last_seen_at, created_at FROM rovers ORDER BY id')
            ->fetchAll();
    }

    public function updateLastSeen(int $id, \DateTimeImmutable $at): void
    {
        $stmt = $this->pdo->prepare('UPDATE rovers SET last_seen_at = :at WHERE id = :id');
        $stmt->execute(['at' => $at->format('Y-m-d H:i:s.v'), 'id' => $id]);
    }
}
