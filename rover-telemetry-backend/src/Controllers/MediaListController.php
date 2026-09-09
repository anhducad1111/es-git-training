<?php

declare(strict_types=1);

namespace RoverTelemetry\Controllers;

use PDO;
use RoverTelemetry\Repositories\MediaRepository;
use RoverTelemetry\Repositories\RoverRepository;
use RoverTelemetry\Support\ApiException;

final class MediaListController
{
    private RoverRepository $rovers;
    private MediaRepository $media;

    public function __construct(PDO $pdo)
    {
        $this->rovers = new RoverRepository($pdo);
        $this->media = new MediaRepository($pdo);
    }

    public function list(array $params, array $query): array
    {
        $rover = $this->rovers->findByDeviceUid($params['device_uid']);
        if ($rover === null) {
            throw new ApiException(404, 'NOT_FOUND', "Unknown device_uid '{$params['device_uid']}'");
        }

        $mediaType = isset($query['media_type']) && in_array($query['media_type'], ['photo', 'video'], true) ? $query['media_type'] : null;
        $start = isset($query['start']) ? new \DateTimeImmutable($query['start'], new \DateTimeZone('UTC')) : null;
        $end = isset($query['end']) ? new \DateTimeImmutable($query['end'], new \DateTimeZone('UTC')) : null;
        $limit = isset($query['limit']) ? min(500, max(1, (int) $query['limit'])) : 100;

        $rows = $this->media->listForRover((int) $rover['id'], $mediaType, $start, $end, $limit);

        return [
            'status' => 200,
            'body' => [
                'device_uid' => $rover['device_uid'],
                'count' => count($rows),
                'media' => array_map(fn($row) => [
                    'id' => (int) $row['id'],
                    'media_type' => $row['media_type'],
                    'captured_at' => (new \DateTimeImmutable($row['captured_at'], new \DateTimeZone('UTC')))->format('Y-m-d\TH:i:s.v\Z'),
                    'file_size_bytes' => (int) $row['file_size_bytes'],
                    'mime_type' => $row['mime_type'],
                ], $rows),
            ],
        ];
    }
}
