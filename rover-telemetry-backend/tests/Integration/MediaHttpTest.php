<?php

declare(strict_types=1);

namespace RoverTelemetry\Tests\Integration;

use RoverTelemetry\Tests\Support\HttpTestCase;

final class MediaHttpTest extends HttpTestCase
{
    private function uploadSampleFile(string $deviceUid = 'rover-001'): array
    {
        $tmpFile = tempnam(sys_get_temp_dir(), 'media-test');
        file_put_contents($tmpFile, str_repeat('x', 1024));

        $ch = curl_init(self::$baseUrl . "/api/v1/rovers/{$deviceUid}/media");
        curl_setopt_array($ch, [
            CURLOPT_POST => true,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_HEADER => true,
            CURLOPT_POSTFIELDS => ['file' => new \CURLFile($tmpFile, 'image/jpeg', 'snapshot.jpg')],
        ]);
        $raw = curl_exec($ch);
        $status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $headerSize = curl_getinfo($ch, CURLINFO_HEADER_SIZE);
        curl_close($ch);
        unlink($tmpFile);

        return ['status' => $status, 'body' => json_decode(substr($raw, $headerSize), true)];
    }

    public function test_upload_stores_file_and_returns_metadata(): void
    {
        $result = $this->uploadSampleFile();

        $this->assertSame(201, $result['status']);
        $this->assertSame('photo', $result['body']['media_type']);
        $this->assertSame('image/jpeg', $result['body']['mime_type']);
        $this->assertSame(1024, $result['body']['file_size_bytes']);
        $this->assertSame(1, (int) $this->pdo->query('SELECT COUNT(*) FROM media_files')->fetchColumn());
    }

    public function test_list_returns_uploaded_media_without_file_path(): void
    {
        $this->uploadSampleFile();

        $response = $this->request('GET', '/api/v1/rovers/rover-001/media');

        $body = json_decode($response['body'], true);
        $this->assertSame(1, $body['count']);
        $this->assertArrayNotHasKey('file_path', $body['media'][0]);
    }

    public function test_serve_streams_the_stored_bytes(): void
    {
        $uploaded = $this->uploadSampleFile();
        $id = $uploaded['body']['id'];

        $response = $this->request('GET', "/api/v1/rovers/rover-001/media/{$id}");

        $this->assertSame(200, $response['status']);
        $this->assertSame(1024, strlen($response['body']));
    }

    public function test_delete_removes_row_and_file(): void
    {
        $uploaded = $this->uploadSampleFile();
        $id = $uploaded['body']['id'];

        $response = $this->request('DELETE', "/api/v1/rovers/rover-001/media/{$id}");

        $this->assertSame(204, $response['status']);
        $this->assertSame(0, (int) $this->pdo->query('SELECT COUNT(*) FROM media_files')->fetchColumn());

        $followUp = $this->request('GET', "/api/v1/rovers/rover-001/media/{$id}");
        $this->assertSame(404, $followUp['status']);
    }

    public function test_serve_unknown_id_returns_404(): void
    {
        (new \RoverTelemetry\Repositories\RoverRepository($this->pdo))->getOrCreateByDeviceUid('rover-001');

        $response = $this->request('GET', '/api/v1/rovers/rover-001/media/999999');

        $this->assertSame(404, $response['status']);
    }
}
