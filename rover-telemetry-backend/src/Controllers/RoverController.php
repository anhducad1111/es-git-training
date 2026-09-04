<?php

declare(strict_types=1);

namespace RoverTelemetry\Controllers;

use PDO;
use RoverTelemetry\Config;
use RoverTelemetry\Repositories\RoverRepository;
use RoverTelemetry\Repositories\SummaryRepository;
use RoverTelemetry\Repositories\TelemetryRepository;
use RoverTelemetry\Support\ApiException;

final class RoverController
{
    private RoverRepository $rovers;
    private TelemetryRepository $telemetry;
    private SummaryRepository $summaries;

    public function __construct(PDO $pdo, private readonly Config $config)
    {
        $this->rovers = new RoverRepository($pdo);
        $this->telemetry = new TelemetryRepository($pdo);
        $this->summaries = new SummaryRepository($pdo);
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

    public function readings(array $params, array $query): array
    {
        $rover = $this->rovers->findByDeviceUid($params['device_uid']);
        if ($rover === null) {
            throw new ApiException(404, 'NOT_FOUND', "Unknown device_uid '{$params['device_uid']}'");
        }

        $limit = isset($query['limit']) ? (int) $query['limit'] : 100;
        if ($limit < 1 || $limit > 5000) {
            throw new ApiException(400, 'INVALID_PARAMETER', 'limit must be between 1 and 5000');
        }
        $order = strtolower($query['order'] ?? 'desc') === 'asc' ? 'asc' : 'desc';

        $rows = $this->telemetry->lastNReadings((int) $rover['id'], $limit, $order);

        return [
            'status' => 200,
            'body' => [
                'device_uid' => $rover['device_uid'],
                'count' => count($rows),
                'readings' => array_map([$this, 'formatReadingRow'], $rows),
            ],
        ];
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
            'temperature_c' => $this->minAvgMax($bucket, 'temp'),
            'humidity_pct' => $this->minAvgMax($bucket, 'hum'),
            'gas_ppm' => $this->minAvgMax($bucket, 'gas'),
            'distance_cm' => $this->minAvgMax($bucket, 'dist'),
            'obstacle_events' => (int) $bucket['obstacle_events'],
        ];
    }

    private function minAvgMax(array $bucket, string $prefix): array
    {
        return [
            'min' => $bucket["{$prefix}_min"] !== null ? (float) $bucket["{$prefix}_min"] : null,
            'avg' => $bucket["{$prefix}_avg"] !== null ? (float) $bucket["{$prefix}_avg"] : null,
            'max' => $bucket["{$prefix}_max"] !== null ? (float) $bucket["{$prefix}_max"] : null,
        ];
    }

    private function formatReadingRow(array $row): array
    {
        return [
            'recorded_at' => (new \DateTimeImmutable($row['recorded_at'], new \DateTimeZone('UTC')))->format('Y-m-d\TH:i:s.v\Z'),
            'temperature_c' => $row['temperature_c'] !== null ? (float) $row['temperature_c'] : null,
            'humidity_pct' => $row['humidity_pct'] !== null ? (float) $row['humidity_pct'] : null,
            'gas_ppm' => $row['gas_ppm'] !== null ? (float) $row['gas_ppm'] : null,
            'distance_cm' => $row['distance_cm'] !== null ? (float) $row['distance_cm'] : null,
            'auto_brake' => (bool) $row['auto_brake'],
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
