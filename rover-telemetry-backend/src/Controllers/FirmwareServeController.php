<?php

declare(strict_types=1);

namespace RoverTelemetry\Controllers;

use PDO;
use RoverTelemetry\Config;
use RoverTelemetry\Repositories\FirmwareRepository;
use RoverTelemetry\Support\ApiException;

final class FirmwareServeController
{
    private FirmwareRepository $firmware;

    public function __construct(PDO $pdo, private readonly Config $config)
    {
        $this->firmware = new FirmwareRepository($pdo);
    }

    public function serve(array $params): ?array
    {
        $record = $this->firmware->find((int) $params['id']);
        if ($record === null) {
            throw new ApiException(404, 'NOT_FOUND', 'Firmware release not found');
        }

        $absolutePath = $this->resolveAbsolutePath($record['file_path']);
        if (!is_file($absolutePath)) {
            throw new ApiException(404, 'NOT_FOUND', 'Firmware record exists but the file is missing on disk');
        }

        header('Content-Type: ' . $record['mime_type']);
        header('Content-Length: ' . $record['file_size_bytes']);
        header('Content-Disposition: attachment; filename="' . basename($record['file_path']) . '"');
        readfile($absolutePath);

        return null;
    }

    private function resolveAbsolutePath(string $relativePath): string
    {
        return rtrim(__DIR__ . '/../../' . $this->config->firmwareStoragePath, '/') . '/' . $relativePath;
    }
}
