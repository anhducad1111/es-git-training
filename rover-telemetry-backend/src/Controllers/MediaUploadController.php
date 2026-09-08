<?php

declare(strict_types=1);

namespace RoverTelemetry\Controllers;

use PDO;
use RoverTelemetry\Config;
use RoverTelemetry\Repositories\MediaRepository;
use RoverTelemetry\Repositories\RoverRepository;
use RoverTelemetry\Support\ApiException;

final class MediaUploadController
{
    private RoverRepository $rovers;
    private MediaRepository $media;

    public function __construct(PDO $pdo, private readonly Config $config)
    {
        $this->rovers = new RoverRepository($pdo);
        $this->media = new MediaRepository($pdo);
    }

    public function upload(array $params, array $file): array
    {
        $rover = $this->rovers->getOrCreateByDeviceUid($params['device_uid']);

        if (!isset($file['tmp_name']) || !is_uploaded_file($file['tmp_name'])) {
            throw new ApiException(400, 'MALFORMED_PAYLOAD', "A 'file' field with an uploaded file is required");
        }

        $capturedAt = new \DateTimeImmutable('now', new \DateTimeZone('UTC'));
        $originalFilename = $file['name'] ?? 'upload';
        $mimeType = $file['type'] ?: 'application/octet-stream';
        $mediaType = str_starts_with($mimeType, 'video/') ? 'video' : 'photo';

        $relativePath = $this->media->buildStoragePath($rover['device_uid'], $capturedAt, $originalFilename);
        $absolutePath = $this->resolveAbsolutePath($relativePath);
        @mkdir(dirname($absolutePath), 0777, true);

        if (!move_uploaded_file($file['tmp_name'], $absolutePath)) {
            throw new ApiException(500, 'INTERNAL_ERROR', 'Failed to store uploaded file');
        }

        $fileHash = hash_file('sha256', $absolutePath) ?: null;
        $fileSizeBytes = (int) filesize($absolutePath);

        $record = $this->media->create(
            (int) $rover['id'], $mediaType, $relativePath, $capturedAt, $fileSizeBytes, $mimeType, $originalFilename, $fileHash
        );

        return [
            'status' => 201,
            'body' => [
                'id' => (int) $record['id'],
                'device_uid' => $rover['device_uid'],
                'media_type' => $record['media_type'],
                'file_path' => $record['file_path'],
                'captured_at' => $capturedAt->format('Y-m-d\TH:i:s.v\Z'),
                'file_size_bytes' => (int) $record['file_size_bytes'],
                'mime_type' => $record['mime_type'],
            ],
        ];
    }

    private function resolveAbsolutePath(string $relativePath): string
    {
        return rtrim(__DIR__ . '/../../' . $this->config->mediaStoragePath, '/') . '/' . $relativePath;
    }
}
