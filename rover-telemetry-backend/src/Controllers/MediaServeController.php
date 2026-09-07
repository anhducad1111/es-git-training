<?php

declare(strict_types=1);

namespace RoverTelemetry\Controllers;

use PDO;
use RoverTelemetry\Config;
use RoverTelemetry\Repositories\MediaRepository;
use RoverTelemetry\Repositories\RoverRepository;
use RoverTelemetry\Support\ApiException;

final class MediaServeController
{
    private RoverRepository $rovers;
    private MediaRepository $media;

    public function __construct(PDO $pdo, private readonly Config $config)
    {
        $this->rovers = new RoverRepository($pdo);
        $this->media = new MediaRepository($pdo);
    }

    public function serve(array $params): ?array
    {
        $rover = $this->rovers->findByDeviceUid($params['device_uid']);
        $record = $rover !== null ? $this->media->find((int) $params['id'], (int) $rover['id']) : null;
        if ($record === null) {
            throw new ApiException(404, 'NOT_FOUND', 'Media not found for this rover');
        }

        $absolutePath = $this->resolveAbsolutePath($record['file_path']);
        if (!is_file($absolutePath)) {
            throw new ApiException(404, 'NOT_FOUND', 'Media record exists but the file is missing on disk');
        }

        header('Content-Type: ' . $record['mime_type']);
        header('Content-Length: ' . $record['file_size_bytes']);
        readfile($absolutePath);

        return null;
    }

    private function resolveAbsolutePath(string $relativePath): string
    {
        return rtrim(__DIR__ . '/../../' . $this->config->mediaStoragePath, '/') . '/' . $relativePath;
    }
}
