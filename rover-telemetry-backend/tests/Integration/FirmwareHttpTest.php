<?php

declare(strict_types=1);

namespace RoverTelemetry\Tests\Integration;

use RoverTelemetry\Tests\Support\HttpTestCase;

final class FirmwareHttpTest extends HttpTestCase
{
    private function uploadSampleFirmware(string $version = '1.0.0', string $releaseNotes = ''): array
    {
        $tmpFile = tempnam(sys_get_temp_dir(), 'firmware-test');
        file_put_contents($tmpFile, str_repeat('x', 2048));

        $fields = ['version' => $version, 'file' => new \CURLFile($tmpFile, 'application/octet-stream', 'firmware.bin')];
        if ($releaseNotes !== '') {
            $fields['release_notes'] = $releaseNotes;
        }

        $ch = curl_init(self::$baseUrl . '/api/v1/firmware');
        curl_setopt_array($ch, [
            CURLOPT_POST => true,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_HEADER => true,
            CURLOPT_POSTFIELDS => $fields,
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
        $result = $this->uploadSampleFirmware('1.0.0', 'Initial release');

        $this->assertSame(201, $result['status']);
        $this->assertSame('1.0.0', $result['body']['version']);
        $this->assertSame(2048, $result['body']['file_size_bytes']);
        $this->assertSame('Initial release', $result['body']['release_notes']);
        $this->assertSame(1, (int) $this->pdo->query('SELECT COUNT(*) FROM firmware_releases')->fetchColumn());
    }

    public function test_upload_without_version_returns_422(): void
    {
        $tmpFile = tempnam(sys_get_temp_dir(), 'firmware-test');
        file_put_contents($tmpFile, 'x');

        $ch = curl_init(self::$baseUrl . '/api/v1/firmware');
        curl_setopt_array($ch, [
            CURLOPT_POST => true,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_POSTFIELDS => ['file' => new \CURLFile($tmpFile, 'application/octet-stream', 'firmware.bin')],
        ]);
        $raw = curl_exec($ch);
        $status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        unlink($tmpFile);

        $this->assertSame(422, $status);
        $this->assertSame('MISSING_FIELD', json_decode($raw, true)['error']['code']);
    }

    public function test_upload_duplicate_version_returns_409(): void
    {
        $this->uploadSampleFirmware('1.0.0');
        $result = $this->uploadSampleFirmware('1.0.0');

        $this->assertSame(409, $result['status']);
        $this->assertSame('ALREADY_EXISTS', $result['body']['error']['code']);
    }

    public function test_list_returns_uploaded_firmware_newest_first(): void
    {
        $this->uploadSampleFirmware('1.0.0');
        $this->uploadSampleFirmware('1.1.0');

        $response = $this->request('GET', '/api/v1/firmware');

        $body = json_decode($response['body'], true);
        $this->assertSame(2, $body['count']);
        $this->assertSame('1.1.0', $body['firmware'][0]['version']);
    }

    public function test_latest_returns_most_recently_uploaded_version(): void
    {
        $this->uploadSampleFirmware('1.0.0');
        $this->uploadSampleFirmware('1.1.0');

        $response = $this->request('GET', '/api/v1/firmware/latest');

        $body = json_decode($response['body'], true);
        $this->assertSame(200, $response['status']);
        $this->assertSame('1.1.0', $body['version']);
    }

    public function test_latest_returns_404_when_no_firmware_uploaded(): void
    {
        $response = $this->request('GET', '/api/v1/firmware/latest');

        $this->assertSame(404, $response['status']);
    }

    public function test_download_streams_the_stored_bytes(): void
    {
        $uploaded = $this->uploadSampleFirmware('1.0.0');
        $id = $uploaded['body']['id'];

        $response = $this->request('GET', "/api/v1/firmware/{$id}/download");

        $this->assertSame(200, $response['status']);
        $this->assertSame(2048, strlen($response['body']));
    }

    public function test_download_unknown_id_returns_404(): void
    {
        $response = $this->request('GET', '/api/v1/firmware/999999/download');

        $this->assertSame(404, $response['status']);
    }
}
