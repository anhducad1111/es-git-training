<?php

declare(strict_types=1);

namespace RoverTelemetry\Repositories;

use PDO;

final class FirmwareRepository
{
    public function __construct(private readonly PDO $pdo)
    {
    }

    public function buildStoragePath(string $version, string $originalFilename): string
    {
        $safeVersion = preg_replace('/[^A-Za-z0-9._-]/', '_', $version) ?? 'unknown';
        $safeFilename = preg_replace('/[^A-Za-z0-9._-]/', '_', $originalFilename) ?? 'file';

        return sprintf('%s/%s', $safeVersion, $safeFilename);
    }

    public function findByVersion(string $version): ?array
    {
        $stmt = $this->pdo->prepare('SELECT * FROM firmware_releases WHERE version = :version');
        $stmt->execute(['version' => $version]);
        $row = $stmt->fetch();

        return $row === false ? null : $row;
    }

    public function create(
        string $version,
        string $filePath,
        int $fileSizeBytes,
        string $mimeType,
        ?string $fileHash,
        ?string $releaseNotes,
    ): array {
        $stmt = $this->pdo->prepare(
            'INSERT INTO firmware_releases (version, file_path, file_size_bytes, mime_type, file_hash, release_notes) '
            . 'VALUES (:version, :file_path, :file_size_bytes, :mime_type, :file_hash, :release_notes)'
        );
        $stmt->execute([
            'version' => $version,
            'file_path' => $filePath,
            'file_size_bytes' => $fileSizeBytes,
            'mime_type' => $mimeType,
            'file_hash' => $fileHash,
            'release_notes' => $releaseNotes,
        ]);

        return $this->find((int) $this->pdo->lastInsertId());
    }

    public function find(int $id): ?array
    {
        $stmt = $this->pdo->prepare('SELECT * FROM firmware_releases WHERE id = :id');
        $stmt->execute(['id' => $id]);
        $row = $stmt->fetch();

        return $row === false ? null : $row;
    }

    public function all(): array
    {
        return $this->pdo
            ->query('SELECT * FROM firmware_releases ORDER BY created_at DESC, id DESC')
            ->fetchAll();
    }

    public function latest(): ?array
    {
        $row = $this->pdo
            ->query('SELECT * FROM firmware_releases ORDER BY created_at DESC, id DESC LIMIT 1')
            ->fetch();

        return $row === false ? null : $row;
    }
}
