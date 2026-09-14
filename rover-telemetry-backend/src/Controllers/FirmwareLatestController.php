<?php

declare(strict_types=1);

namespace RoverTelemetry\Controllers;

use PDO;
use RoverTelemetry\Repositories\FirmwareRepository;
use RoverTelemetry\Support\ApiException;

final class FirmwareLatestController
{
    private FirmwareRepository $firmware;

    public function __construct(PDO $pdo)
    {
        $this->firmware = new FirmwareRepository($pdo);
    }

    public function latest(): array
    {
        $row = $this->firmware->latest();
        if ($row === null) {
            throw new ApiException(404, 'NOT_FOUND', 'No firmware has been uploaded yet');
        }

        return [
            'status' => 200,
            'body' => [
                'id' => (int) $row['id'],
                'version' => $row['version'],
                'file_size_bytes' => (int) $row['file_size_bytes'],
                'mime_type' => $row['mime_type'],
                'file_hash' => $row['file_hash'],
                'release_notes' => $row['release_notes'],
                'created_at' => (new \DateTimeImmutable($row['created_at'], new \DateTimeZone('UTC')))->format('Y-m-d\TH:i:s\Z'),
            ],
        ];
    }
}
