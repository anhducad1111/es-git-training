<?php

declare(strict_types=1);

namespace RoverTelemetry\Controllers;

use PDO;
use RoverTelemetry\Repositories\RoverRepository;
use RoverTelemetry\Repositories\TelemetryRepository;
use RoverTelemetry\Support\ApiException;
use RoverTelemetry\Support\ReadingFormatter;

final class RoverExportController
{
    private RoverRepository $rovers;
    private TelemetryRepository $telemetry;

    public function __construct(PDO $pdo)
    {
        $this->rovers = new RoverRepository($pdo);
        $this->telemetry = new TelemetryRepository($pdo);
    }

    public function export(array $params, array $query, PDO $unbufferedPdo): ?array
    {
        $rover = $this->rovers->findByDeviceUid($params['device_uid']);
        if ($rover === null) {
            throw new ApiException(404, 'NOT_FOUND', "Unknown device_uid '{$params['device_uid']}'");
        }
        if (!isset($query['start']) || !isset($query['end'])) {
            throw new ApiException(400, 'INVALID_PARAMETER', 'start and end are required');
        }

        $start = new \DateTimeImmutable($query['start'], new \DateTimeZone('UTC'));
        $end = new \DateTimeImmutable($query['end'], new \DateTimeZone('UTC'));
        $format = ($query['format'] ?? 'csv') === 'json' ? 'json' : 'csv';

        set_time_limit(0);

        if ($format === 'csv') {
            header('Content-Type: text/csv');
            header("Content-Disposition: attachment; filename=\"{$rover['device_uid']}-export.csv\"");
            echo "device_uid,recorded_at,temperature_c,humidity_pct,gas_ppm,distance_cm,auto_brake\n";
            foreach ($this->telemetry->streamRange($unbufferedPdo, (int) $rover['id'], $start, $end) as $row) {
                $recordedAt = (new \DateTimeImmutable($row['recorded_at'], new \DateTimeZone('UTC')))->format('Y-m-d\TH:i:s.v\Z');
                echo implode(',', [
                    $rover['device_uid'],
                    $recordedAt,
                    $row['temperature_c'] ?? '',
                    $row['humidity_pct'] ?? '',
                    $row['gas_ppm'] ?? '',
                    $row['distance_cm'] ?? '',
                    (int) $row['auto_brake'],
                ]) . "\n";
            }
        } else {
            header('Content-Type: application/json');
            echo '[';
            $first = true;
            foreach ($this->telemetry->streamRange($unbufferedPdo, (int) $rover['id'], $start, $end) as $row) {
                echo ($first ? '' : ',') . json_encode(ReadingFormatter::formatRow($row));
                $first = false;
            }
            echo ']';
        }

        return null;
    }
}
