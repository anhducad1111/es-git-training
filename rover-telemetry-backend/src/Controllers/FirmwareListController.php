<?php

declare(strict_types=1);

namespace RoverTelemetry\Controllers;

use PDO;
use RoverTelemetry\Repositories\FirmwareRepository;

final class FirmwareListController
{
    private FirmwareRepository $firmware;

    public function __construct(PDO $pdo)
    {
        $this->firmware = new FirmwareRepository($pdo);
    }

    public function list(): array
    {
        $rows = $this->firmware->all();

        return [
            'status' => 200,
            'body' => [
                'count' => count($rows),
                'firmware' => array_map(fn($row) => $this->format($row), $rows),
            ],
        ];
    }

    private function format(array $row): array
    {
        return [
            'id' => (int) $row['id'],
            'version' => $row['version'],
            'file_size_bytes' => (int) $row['file_size_bytes'],
            'mime_type' => $row['mime_type'],
            'file_hash' => $row['file_hash'],
            'release_notes' => $row['release_notes'],
            'created_at' => (new \DateTimeImmutable($row['created_at'], new \DateTimeZone('UTC')))->format('Y-m-d\TH:i:s\Z'),
        ];
    }
}
