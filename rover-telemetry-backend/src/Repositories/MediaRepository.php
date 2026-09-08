<?php

declare(strict_types=1);

namespace RoverTelemetry\Repositories;

use PDO;

final class MediaRepository
{
    public function __construct(private readonly PDO $pdo)
    {
    }

    public function buildStoragePath(string $deviceUid, \DateTimeImmutable $capturedAt, string $originalFilename): string
    {
        $safeFilename = preg_replace('/[^A-Za-z0-9._-]/', '_', $originalFilename) ?? 'file';

        return sprintf(
            '%s/%s/%s/%s/%s_%s',
            $deviceUid,
            $capturedAt->format('Y'),
            $capturedAt->format('m'),
            $capturedAt->format('d'),
            $capturedAt->format('H-i-s-v'),
            $safeFilename,
        );
    }

    public function create(
        int $deviceId,
        string $mediaType,
        string $filePath,
        \DateTimeImmutable $capturedAt,
        int $fileSizeBytes,
        string $mimeType,
        ?string $originalFilename,
        ?string $fileHash,
    ): array {
        $stmt = $this->pdo->prepare(
            'INSERT INTO media_files (device_id, media_type, file_path, captured_at, file_size_bytes, mime_type, original_filename, file_hash) '
            . 'VALUES (:device_id, :media_type, :file_path, :captured_at, :file_size_bytes, :mime_type, :original_filename, :file_hash)'
        );
        $stmt->execute([
            'device_id' => $deviceId,
            'media_type' => $mediaType,
            'file_path' => $filePath,
            'captured_at' => $capturedAt->format('Y-m-d H:i:s.v'),
            'file_size_bytes' => $fileSizeBytes,
            'mime_type' => $mimeType,
            'original_filename' => $originalFilename,
            'file_hash' => $fileHash,
        ]);

        return $this->find((int) $this->pdo->lastInsertId(), $deviceId);
    }

    public function listForRover(int $deviceId, ?string $mediaType, ?\DateTimeImmutable $start, ?\DateTimeImmutable $end, int $limit): array
    {
        $sql = 'SELECT * FROM media_files WHERE device_id = :device_id';
        $params = ['device_id' => $deviceId];
        if ($mediaType !== null) {
            $sql .= ' AND media_type = :media_type';
            $params['media_type'] = $mediaType;
        }
        if ($start !== null) {
            $sql .= ' AND captured_at >= :start';
            $params['start'] = $start->format('Y-m-d H:i:s.v');
        }
        if ($end !== null) {
            $sql .= ' AND captured_at <= :end';
            $params['end'] = $end->format('Y-m-d H:i:s.v');
        }
        $sql .= ' ORDER BY captured_at DESC LIMIT :limit';

        $stmt = $this->pdo->prepare($sql);
        foreach ($params as $key => $value) {
            $stmt->bindValue($key, $value);
        }
        $stmt->bindValue('limit', $limit, PDO::PARAM_INT);
        $stmt->execute();

        return $stmt->fetchAll();
    }

    public function find(int $id, int $deviceId): ?array
    {
        $stmt = $this->pdo->prepare('SELECT * FROM media_files WHERE id = :id AND device_id = :device_id');
        $stmt->execute(['id' => $id, 'device_id' => $deviceId]);
        $row = $stmt->fetch();

        return $row === false ? null : $row;
    }

    public function delete(int $id, int $deviceId): bool
    {
        $stmt = $this->pdo->prepare('DELETE FROM media_files WHERE id = :id AND device_id = :device_id');
        $stmt->execute(['id' => $id, 'device_id' => $deviceId]);

        return $stmt->rowCount() > 0;
    }
}
