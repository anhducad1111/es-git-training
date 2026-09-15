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

        $this->streamWithRangeSupport($absolutePath, (int) $record['file_size_bytes'], $record['mime_type']);

        return null;
    }

    // Browsers need Range/206 support to play video served this way: an MP4 whose
    // 'moov' atom sits at the end of the file (the common case for recordings not
    // post-processed with "faststart") can only be played by seeking straight to that
    // tail region rather than downloading sequentially from byte 0. Without this, the
    // <video> tag (and its thumbnail) silently fails even though the file downloads and
    // plays fine in a desktop player that just reads the whole file.
    private function streamWithRangeSupport(string $absolutePath, int $fileSize, string $mimeType): void
    {
        header('Content-Type: ' . $mimeType);
        header('Accept-Ranges: bytes');

        $start = 0;
        $end = $fileSize - 1;
        $rangeHeader = $_SERVER['HTTP_RANGE'] ?? null;

        if ($rangeHeader !== null && preg_match('/bytes=(\d*)-(\d*)/', $rangeHeader, $m)) {
            $start = $m[1] === '' ? 0 : (int) $m[1];
            $end = $m[2] === '' ? $fileSize - 1 : (int) $m[2];
            if ($m[1] === '' && $m[2] !== '') {
                // Suffix range, e.g. "bytes=-500" = last 500 bytes.
                $start = max(0, $fileSize - (int) $m[2]);
                $end = $fileSize - 1;
            }
            if ($start > $end || $start >= $fileSize) {
                header('Content-Range: bytes */' . $fileSize);
                http_response_code(416);
                return;
            }
            $end = min($end, $fileSize - 1);
            http_response_code(206);
            header("Content-Range: bytes {$start}-{$end}/{$fileSize}");
        }

        $length = $end - $start + 1;
        header('Content-Length: ' . $length);

        $stream = fopen($absolutePath, 'rb');
        fseek($stream, $start);
        $remaining = $length;
        while ($remaining > 0 && !feof($stream)) {
            $chunk = fread($stream, min(8192, $remaining));
            if ($chunk === false) {
                break;
            }
            echo $chunk;
            $remaining -= strlen($chunk);
        }
        fclose($stream);
    }

    private function resolveAbsolutePath(string $relativePath): string
    {
        return rtrim(__DIR__ . '/../../' . $this->config->mediaStoragePath, '/') . '/' . $relativePath;
    }
}
