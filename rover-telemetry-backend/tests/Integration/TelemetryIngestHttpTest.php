<?php

declare(strict_types=1);

namespace RoverTelemetry\Tests\Integration;

use RoverTelemetry\Tests\Support\HttpTestCase;

final class TelemetryIngestHttpTest extends HttpTestCase
{
    private function validPayload(array $overrides = []): array
    {
        return array_merge([
            'device_uid' => 'rover-001',
            'temperature_c' => 25.4,
            'humidity_pct' => 61.2,
            'gas_ppm' => 128.0,
            'distance_cm' => 34.5,
            'auto_brake' => false,
        ], $overrides);
    }

    public function test_valid_telemetry_is_stored_and_returns_201_with_gateway_stamped_time(): void
    {
        $before = new \DateTimeImmutable('now', new \DateTimeZone('UTC'));
        $response = $this->request('POST', '/api/v1/telemetry', $this->validPayload());
        $after = new \DateTimeImmutable('now', new \DateTimeZone('UTC'));

        $this->assertSame(201, $response['status']);
        $body = json_decode($response['body'], true);
        $this->assertTrue($body['success']);
        $this->assertSame('rover-001', $body['device_uid']);
        $this->assertArrayNotHasKey('duplicate', $body);
        $recordedAt = new \DateTimeImmutable($body['recorded_at']);
        $this->assertGreaterThanOrEqual($before->getTimestamp(), $recordedAt->getTimestamp());
        $this->assertLessThanOrEqual($after->getTimestamp() + 1, $recordedAt->getTimestamp());
        $this->assertSame(1, (int) $this->pdo->query('SELECT COUNT(*) FROM telemetry_readings')->fetchColumn());
    }

    public function test_recorded_at_in_the_request_body_is_ignored(): void
    {
        $response = $this->request('POST', '/api/v1/telemetry', $this->validPayload(['recorded_at' => '1970-01-01T00:00:00Z']));

        $this->assertSame(201, $response['status']);
        $body = json_decode($response['body'], true);
        $this->assertGreaterThan(1700000000, (new \DateTimeImmutable($body['recorded_at']))->getTimestamp());
    }

    public function test_retrying_the_same_payload_stores_two_distinct_rows(): void
    {
        $payload = $this->validPayload();

        $first = $this->request('POST', '/api/v1/telemetry', $payload);
        usleep(2000);
        $second = $this->request('POST', '/api/v1/telemetry', $payload);

        $this->assertSame(201, $first['status']);
        $this->assertSame(201, $second['status']);
        $firstAt = json_decode($first['body'], true)['recorded_at'];
        $secondAt = json_decode($second['body'], true)['recorded_at'];
        $this->assertNotSame($firstAt, $secondAt);
        $this->assertSame(2, (int) $this->pdo->query('SELECT COUNT(*) FROM telemetry_readings')->fetchColumn());
    }

    public function test_ingest_updates_rover_last_seen_at(): void
    {
        $this->request('POST', '/api/v1/telemetry', $this->validPayload());

        $lastSeen = $this->pdo->query("SELECT last_seen_at FROM rovers WHERE device_uid = 'rover-001'")->fetchColumn();
        $this->assertNotNull($lastSeen);
    }

    public function test_out_of_range_temperature_returns_422_and_is_logged(): void
    {
        $response = $this->request('POST', '/api/v1/telemetry', $this->validPayload(['temperature_c' => 150]));

        $this->assertSame(422, $response['status']);
        $this->assertSame('OUT_OF_RANGE', json_decode($response['body'], true)['error']['code']);
        $this->assertSame(1, (int) $this->pdo->query('SELECT COUNT(*) FROM validation_errors')->fetchColumn());
        $this->assertSame(0, (int) $this->pdo->query('SELECT COUNT(*) FROM telemetry_readings')->fetchColumn());
    }

    public function test_omitted_optional_sensor_is_stored_as_null_not_rejected(): void
    {
        $this->request('POST', '/api/v1/telemetry', $this->validPayload(['device_uid' => 'rover-002']));
        $this->pdo->exec("UPDATE rovers SET enabled_sensors = 'temperature_c' WHERE device_uid = 'rover-002'");

        $response = $this->request('POST', '/api/v1/telemetry', [
            'device_uid' => 'rover-002',
            'temperature_c' => 26.0,
            'auto_brake' => false,
        ]);

        $this->assertSame(201, $response['status']);
        $row = $this->pdo->query(
            "SELECT humidity_pct, gas_ppm, distance_cm FROM telemetry_readings ORDER BY recorded_at DESC LIMIT 1"
        )->fetch();
        $this->assertNull($row['humidity_pct']);
        $this->assertNull($row['gas_ppm']);
        $this->assertNull($row['distance_cm']);
    }

    public function test_missing_field_returns_422(): void
    {
        $payload = $this->validPayload();
        unset($payload['humidity_pct']);

        $response = $this->request('POST', '/api/v1/telemetry', $payload);

        $this->assertSame(422, $response['status']);
        $this->assertSame('MISSING_FIELD', json_decode($response['body'], true)['error']['code']);
    }

    public function test_malformed_json_returns_400_and_service_keeps_running(): void
    {
        $ch = curl_init(self::$baseUrl . '/api/v1/telemetry');
        curl_setopt_array($ch, [
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => '{not valid json',
            CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
            CURLOPT_RETURNTRANSFER => true,
        ]);
        $raw = curl_exec($ch);
        $status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        $this->assertSame(400, $status);
        $this->assertSame('MALFORMED_PAYLOAD', json_decode($raw, true)['error']['code']);

        $followUp = $this->request('POST', '/api/v1/telemetry', $this->validPayload());
        $this->assertSame(201, $followUp['status']);
    }
}
