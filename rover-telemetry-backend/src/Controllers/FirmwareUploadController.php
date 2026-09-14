<?php

declare(strict_types=1);

namespace RoverTelemetry\Controllers;

use PDO;
use RoverTelemetry\Config;
use RoverTelemetry\Repositories\FirmwareRepository;
use RoverTelemetry\Support\ApiException;

final class FirmwareUploadController
{
    private FirmwareRepository $firmware;

    public function __construct(PDO $pdo, private readonly Config $config)
    {
        $this->firmware = new FirmwareRepository($pdo);
    }

    public function upload(array $body, array $file): array
    {
        $version = trim((string) ($body['version'] ?? ''));
        if ($version === '') {
            throw new ApiException(422, 'MISSING_FIELD', "'version' is required");
        }

        if (!isset($file['tmp_name']) || !is_uploaded_file($file['tmp_name'])) {
            throw new ApiException(400, 'MALFORMED_PAYLOAD', "A 'file' field with an uploaded file is required");
        }

        if ($this->firmware->findByVersion($version) !== null) {
            throw new ApiException(409, 'ALREADY_EXISTS', "Firmware version '{$version}' already exists");
        }

        $releaseNotes = isset($body['release_notes']) ? (string) $body['release_notes'] : null;
        $originalFilename = $file['name'] ?? 'firmware.bin';
        $mimeType = $file['type'] ?: 'application/octet-stream';

        $relativePath = $this->firmware->buildStoragePath($version, $originalFilename);
        $absolutePath = $this->resolveAbsolutePath($relativePath);
        @mkdir(dirname($absolutePath), 0777, true);

        if (!move_uploaded_file($file['tmp_name'], $absolutePath)) {
            throw new ApiException(500, 'INTERNAL_ERROR', 'Failed to store uploaded file');
        }

        $fileHash = hash_file('sha256', $absolutePath) ?: null;
        $fileSizeBytes = (int) filesize($absolutePath);

        $record = $this->firmware->create($version, $relativePath, $fileSizeBytes, $mimeType, $fileHash, $releaseNotes);

        return [
            'status' => 201,
            'body' => [
                'id' => (int) $record['id'],
                'version' => $record['version'],
                'file_size_bytes' => (int) $record['file_size_bytes'],
                'mime_type' => $record['mime_type'],
                'file_hash' => $record['file_hash'],
                'release_notes' => $record['release_notes'],
                'created_at' => (new \DateTimeImmutable($record['created_at'], new \DateTimeZone('UTC')))->format('Y-m-d\TH:i:s\Z'),
            ],
        ];
    }

    private function resolveAbsolutePath(string $relativePath): string
    {
        return rtrim(__DIR__ . '/../../' . $this->config->firmwareStoragePath, '/') . '/' . $relativePath;
    }
}
