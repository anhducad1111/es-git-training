<?php

declare(strict_types=1);

namespace RoverTelemetry\Controllers;

use PDO;
use RoverTelemetry\Config;
use RoverTelemetry\Repositories\RoverRepository;
use RoverTelemetry\Repositories\SensorLimitsRepository;
use RoverTelemetry\Repositories\TelemetryRepository;
use RoverTelemetry\Support\ApiException;

final class RoverEventsController
{
    private RoverRepository $rovers;
    private TelemetryRepository $telemetry;
    private SensorLimitsRepository $sensorLimits;

    public function __construct(PDO $pdo, private readonly Config $config)
    {
        $this->rovers = new RoverRepository($pdo);
        $this->telemetry = new TelemetryRepository($pdo);
        $this->sensorLimits = new SensorLimitsRepository($pdo);
    }

    public function events(array $params, array $query): array
    {
        $rover = $this->rovers->findByDeviceUid($params['device_uid']);
        if ($rover === null) {
            throw new ApiException(404, 'NOT_FOUND', "Unknown device_uid '{$params['device_uid']}'");
        }

        $since = isset($query['since'])
            ? new \DateTimeImmutable($query['since'], new \DateTimeZone('UTC'))
            : new \DateTimeImmutable('-24 hours', new \DateTimeZone('UTC'));
        $limit = isset($query['limit']) ? max(1, (int) $query['limit']) : 100;

        $rows = $this->telemetry->rangeReadings((int) $rover['id'], $since, new \DateTimeImmutable('now', new \DateTimeZone('UTC')), 'asc');
        $ranges = $this->sensorLimits->all();
        $expected = $this->config->expectedIntervalSeconds;

        $events = [];
        $previousBrake = 0;
        $previousAt = null;
        foreach ($rows as $row) {
            $at = new \DateTimeImmutable($row['recorded_at'], new \DateTimeZone('UTC'));

            if ($previousAt !== null) {
                $gapSeconds = $at->getTimestamp() - $previousAt->getTimestamp();
                if ($gapSeconds > 2 * $expected) {
                    $events[] = ['at' => $this->isoZ($at), 'type' => 'reconnected', 'gap_seconds' => $gapSeconds];
                }
            }

            foreach (['temperature_c', 'humidity_pct', 'gas_ppm', 'distance_cm'] as $field) {
                if ($row[$field] === null || !isset($ranges[$field])) {
                    continue;
                }
                [$min, $max] = $ranges[$field];
                $value = (float) $row[$field];
                if ($value < $min || $value > $max) {
                    $events[] = ['at' => $this->isoZ($at), 'type' => 'threshold_exceeded', 'sensor' => $field, 'value' => $value, 'limit' => $value > $max ? $max : $min];
                }
            }

            $currentBrake = (int) $row['auto_brake'];
            if ($previousBrake === 0 && $currentBrake === 1) {
                $events[] = ['at' => $this->isoZ($at), 'type' => 'auto_brake_engaged', 'value' => $row['distance_cm'] !== null ? (float) $row['distance_cm'] : null];
            } elseif ($previousBrake === 1 && $currentBrake === 0) {
                $events[] = ['at' => $this->isoZ($at), 'type' => 'auto_brake_cleared'];
            }
            $previousBrake = $currentBrake;
            $previousAt = $at;
        }

        $events = array_reverse($events);

        return ['status' => 200, 'body' => ['events' => array_slice($events, 0, $limit)]];
    }

    private function isoZ(\DateTimeImmutable $at): string
    {
        return $at->format('Y-m-d\TH:i:s\Z');
    }
}
