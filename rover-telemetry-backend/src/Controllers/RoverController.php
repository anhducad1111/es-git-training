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

    private const RESOLUTION_CAP = 5000;

    public function readings(array $params, array $query): array
    {
        $rover = $this->rovers->findByDeviceUid($params['device_uid']);
        if ($rover === null) {
            throw new ApiException(404, 'NOT_FOUND', "Unknown device_uid '{$params['device_uid']}'");
        }
        $deviceId = (int) $rover['id'];

        if (!isset($query['start']) || !isset($query['end'])) {
            return $this->readingsLimitMode($rover, $deviceId, $query);
        }

        $start = new \DateTimeImmutable($query['start'], new \DateTimeZone('UTC'));
        $end = new \DateTimeImmutable($query['end'], new \DateTimeZone('UTC'));
        if ($start > $end) {
            throw new ApiException(400, 'INVALID_PARAMETER', 'start must not be after end');
        }

        $queryStartedAt = microtime(true);
        $rawCount = $this->telemetry->countInRange($deviceId, $start, $end);

        $requested = $query['resolution'] ?? 'auto';
        $resolution = $this->resolveResolution($requested, $rawCount);

        if ($resolution === 'raw') {
            $rows = $this->telemetry->rangeReadings($deviceId, $start, $end, 'asc');
            [$points, $gaps, $bucketsPopulated, $count] = $this->buildRawSeries($rows, $start, $end);
        } else {
            $buckets = $this->summaries->bucketsInRange($deviceId, $resolution, $start, $end);
            [$points, $gaps, $bucketsPopulated, $count] = $this->buildBucketSeries($buckets, $resolution, $start, $end);
        }

        return [
            'status' => 200,
            'body' => [
                'device_uid' => $rover['device_uid'],
                'resolution' => $resolution,
                'count' => $count,
                'buckets_populated' => $bucketsPopulated,
                'gaps' => $gaps,
                'query' => [
                    'raw_rows_in_range' => $rawCount,
                    'query_time_ms' => (int) round((microtime(true) - $queryStartedAt) * 1000),
                ],
                'readings' => $points,
            ],
        ];
    }

    private function readingsLimitMode(array $rover, int $deviceId, array $query): array
    {
        $limit = isset($query['limit']) ? (int) $query['limit'] : 100;
        if ($limit < 1 || $limit > self::RESOLUTION_CAP) {
            throw new ApiException(400, 'INVALID_PARAMETER', 'limit must be between 1 and 5000');
        }
        $order = strtolower($query['order'] ?? 'desc') === 'asc' ? 'asc' : 'desc';
        $rows = $this->telemetry->lastNReadings($deviceId, $limit, $order);

        return [
            'status' => 200,
            'body' => [
                'device_uid' => $rover['device_uid'],
                'count' => count($rows),
                'readings' => array_map([$this, 'formatReadingRow'], $rows),
            ],
        ];
    }

    private function resolveResolution(string $requested, int $rawCount): string
    {
        if ($requested === 'raw') {
            if ($rawCount > self::RESOLUTION_CAP) {
                throw new ApiException(400, 'INVALID_PARAMETER', 'raw resolution would exceed the 5000-point cap for this range');
            }
            return 'raw';
        }
        if (in_array($requested, ['minute', 'hour', 'day'], true)) {
            return $requested;
        }
        if ($requested !== 'auto') {
            throw new ApiException(400, 'INVALID_PARAMETER', 'resolution must be one of auto, raw, minute, hour, day');
        }

        if ($rawCount <= self::RESOLUTION_CAP) {
            return 'raw';
        }

        return 'minute';
    }

    private function buildRawSeries(array $rows, \DateTimeImmutable $start, \DateTimeImmutable $end): array
    {
        $points = array_map([$this, 'formatReadingRow'], $rows);
        $gaps = [];
        $expected = $this->config->expectedIntervalSeconds;
        $previous = $start;
        foreach ($rows as $row) {
            $at = new \DateTimeImmutable($row['recorded_at'], new \DateTimeZone('UTC'));
            $intervalSeconds = $at->getTimestamp() - $previous->getTimestamp();
            if ($previous !== $start && $intervalSeconds > 2 * $expected) {
                $gaps[] = $this->formatGap($previous, $at, $expected);
            }
            $previous = $at;
        }

        return [$points, $gaps, count($rows), count($rows)];
    }

    private function buildBucketSeries(array $buckets, string $granularity, \DateTimeImmutable $start, \DateTimeImmutable $end): array
    {
        $bucketSeconds = ['minute' => 60, 'hour' => 3600, 'day' => 86400][$granularity];
        $byStart = [];
        foreach ($buckets as $bucket) {
            $byStart[$bucket['bucket_start']] = $bucket;
        }

        $points = [];
        $gaps = [];
        $populated = 0;
        $cursor = $start;
        $gapStart = null;
        while ($cursor <= $end) {
            $key = $cursor->format('Y-m-d H:i:s');
            if (isset($byStart[$key])) {
                $populated++;
                if ($gapStart !== null) {
                    $gaps[] = $this->formatGap($gapStart, $cursor, $bucketSeconds);
                    $gapStart = null;
                }
                $points[] = [
                    'recorded_at' => $cursor->format('Y-m-d\TH:i:s\Z'),
                    'temperature_c' => $this->minAvgMax($byStart[$key], 'temp'),
                    'humidity_pct' => $this->minAvgMax($byStart[$key], 'hum'),
                    'gas_ppm' => $this->minAvgMax($byStart[$key], 'gas'),
                    'distance_cm' => $this->minAvgMax($byStart[$key], 'dist'),
                ];
            } elseif ($gapStart === null) {
                $gapStart = $cursor;
            }
            $cursor = $cursor->modify("+{$bucketSeconds} seconds");
        }
        if ($gapStart !== null) {
            $gaps[] = $this->formatGap($gapStart, $cursor, $bucketSeconds);
        }

        $totalBuckets = (int) ceil(($end->getTimestamp() - $start->getTimestamp()) / $bucketSeconds) + 1;

        return [$points, $gaps, $populated, $totalBuckets];
    }

    private function formatGap(\DateTimeImmutable $start, \DateTimeImmutable $end, int $unitSeconds): array
    {
        $durationSeconds = $end->getTimestamp() - $start->getTimestamp();

        return [
            'start' => $start->format('Y-m-d\TH:i:s\Z'),
            'end' => $end->format('Y-m-d\TH:i:s\Z'),
            'duration_seconds' => $durationSeconds,
            'missing_readings' => (int) round($durationSeconds / $unitSeconds),
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
