<?php

declare(strict_types=1);

namespace RoverTelemetry\Controllers;

use PDO;
use RoverTelemetry\Repositories\RoverRepository;
use RoverTelemetry\Repositories\SummaryRepository;
use RoverTelemetry\Support\ApiException;
use RoverTelemetry\Support\ReadingFormatter;

final class RoverSummaryController
{
    private RoverRepository $rovers;
    private SummaryRepository $summaries;

    public function __construct(PDO $pdo)
    {
        $this->rovers = new RoverRepository($pdo);
        $this->summaries = new SummaryRepository($pdo);
    }

    public function summary(array $params, array $query): array
    {
        $rover = $this->rovers->findByDeviceUid($params['device_uid']);
        if ($rover === null) {
            throw new ApiException(404, 'NOT_FOUND', "Unknown device_uid '{$params['device_uid']}'");
        }

        $granularity = $query['granularity'] ?? 'day';
        if (!in_array($granularity, ['minute', 'hour', 'day'], true)) {
            throw new ApiException(400, 'INVALID_PARAMETER', 'granularity must be minute, hour, or day');
        }
        if (!isset($query['start']) || !isset($query['end'])) {
            throw new ApiException(400, 'INVALID_PARAMETER', 'start and end are required');
        }

        $start = new \DateTimeImmutable($query['start'], new \DateTimeZone('UTC'));
        $end = new \DateTimeImmutable($query['end'], new \DateTimeZone('UTC'));
        if ($start > $end) {
            throw new ApiException(400, 'INVALID_PARAMETER', 'start must not be after end');
        }

        $buckets = $this->summaries->bucketsInRange((int) $rover['id'], $granularity, $start, $end);

        return [
            'status' => 200,
            'body' => [
                'device_uid' => $rover['device_uid'],
                'granularity' => $granularity,
                'buckets' => array_map([$this, 'formatSummaryBucket'], $buckets),
            ],
        ];
    }

    private function formatSummaryBucket(array $bucket): array
    {
        return [
            'bucket_start' => (new \DateTimeImmutable($bucket['bucket_start'], new \DateTimeZone('UTC')))->format('Y-m-d\TH:i:s\Z'),
            'sample_count' => (int) $bucket['sample_count'],
            'temperature_c' => ReadingFormatter::minAvgMax($bucket, 'temp'),
            'humidity_pct' => ReadingFormatter::minAvgMax($bucket, 'hum'),
            'gas_ppm' => ReadingFormatter::minAvgMax($bucket, 'gas'),
            'distance_cm' => ReadingFormatter::minAvgMax($bucket, 'dist'),
            'obstacle_events' => (int) $bucket['obstacle_events'],
        ];
    }
}
