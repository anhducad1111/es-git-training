<?php

declare(strict_types=1);

namespace RoverTelemetry\Repositories;

use PDO;

final class TelemetryRepository
{
    public function __construct(private readonly PDO $pdo)
    {
    }

    public function insert(
        int $deviceId,
        \DateTimeImmutable $recordedAt,
        ?float $temperatureC,
        ?float $humidityPct,
        ?float $gasPpm,
        ?float $distanceCm,
        int $autoBrake,
    ): void {
        $stmt = $this->pdo->prepare(
            'INSERT INTO telemetry_readings (device_id, recorded_at, temperature_c, humidity_pct, gas_ppm, distance_cm, auto_brake) '
            . 'VALUES (:device_id, :recorded_at, :temperature_c, :humidity_pct, :gas_ppm, :distance_cm, :auto_brake)'
        );
        $stmt->execute([
            'device_id' => $deviceId,
            'recorded_at' => $recordedAt->format('Y-m-d H:i:s.v'),
            'temperature_c' => $temperatureC,
            'humidity_pct' => $humidityPct,
            'gas_ppm' => $gasPpm,
            'distance_cm' => $distanceCm,
            'auto_brake' => $autoBrake,
        ]);
    }

    public function latest(int $deviceId): ?array
    {
        $stmt = $this->pdo->prepare(
            'SELECT device_id, recorded_at, temperature_c, humidity_pct, gas_ppm, distance_cm, auto_brake '
            . 'FROM telemetry_readings WHERE device_id = :device_id ORDER BY recorded_at DESC LIMIT 1'
        );
        $stmt->execute(['device_id' => $deviceId]);
        $row = $stmt->fetch();

        return $row === false ? null : $row;
    }

    public function lastNReadings(int $deviceId, int $limit, string $order = 'desc'): array
    {
        $direction = strtolower($order) === 'asc' ? 'ASC' : 'DESC';
        $stmt = $this->pdo->prepare(
            "SELECT recorded_at, temperature_c, humidity_pct, gas_ppm, distance_cm, auto_brake "
            . "FROM telemetry_readings WHERE device_id = :device_id ORDER BY recorded_at {$direction} LIMIT :limit"
        );
        $stmt->bindValue('device_id', $deviceId, PDO::PARAM_INT);
        $stmt->bindValue('limit', $limit, PDO::PARAM_INT);
        $stmt->execute();

        return $stmt->fetchAll();
    }

    public function rangeReadings(
        int $deviceId,
        \DateTimeImmutable $start,
        \DateTimeImmutable $end,
        string $order = 'asc',
        ?int $limit = null,
    ): array {
        $direction = strtolower($order) === 'desc' ? 'DESC' : 'ASC';
        $sql = "SELECT recorded_at, temperature_c, humidity_pct, gas_ppm, distance_cm, auto_brake "
            . "FROM telemetry_readings WHERE device_id = :device_id AND recorded_at BETWEEN :start AND :end "
            . "ORDER BY recorded_at {$direction}";
        if ($limit !== null) {
            $sql .= ' LIMIT :limit';
        }

        $stmt = $this->pdo->prepare($sql);
        $stmt->bindValue('device_id', $deviceId, PDO::PARAM_INT);
        $stmt->bindValue('start', $start->format('Y-m-d H:i:s.v'));
        $stmt->bindValue('end', $end->format('Y-m-d H:i:s.v'));
        if ($limit !== null) {
            $stmt->bindValue('limit', $limit, PDO::PARAM_INT);
        }
        $stmt->execute();

        return $stmt->fetchAll();
    }

    public function countInRange(int $deviceId, \DateTimeImmutable $start, \DateTimeImmutable $end): int
    {
        $stmt = $this->pdo->prepare(
            'SELECT COUNT(*) FROM telemetry_readings WHERE device_id = :device_id AND recorded_at BETWEEN :start AND :end'
        );
        $stmt->execute([
            'device_id' => $deviceId,
            'start' => $start->format('Y-m-d H:i:s.v'),
            'end' => $end->format('Y-m-d H:i:s.v'),
        ]);

        return (int) $stmt->fetchColumn();
    }

    public function streamRange(PDO $unbufferedPdo, int $deviceId, \DateTimeImmutable $start, \DateTimeImmutable $end): \Generator
    {
        $stmt = $unbufferedPdo->prepare(
            'SELECT recorded_at, temperature_c, humidity_pct, gas_ppm, distance_cm, auto_brake '
            . 'FROM telemetry_readings WHERE device_id = :device_id AND recorded_at BETWEEN :start AND :end ORDER BY recorded_at ASC'
        );
        $stmt->execute([
            'device_id' => $deviceId,
            'start' => $start->format('Y-m-d H:i:s.v'),
            'end' => $end->format('Y-m-d H:i:s.v'),
        ]);

        while ($row = $stmt->fetch()) {
            yield $row;
        }
    }
}
