<?php

declare(strict_types=1);

$options = getopt('', ['requests:', 'devices:', 'base-url:']);
$totalRequests = (int) ($options['requests'] ?? 1000);
$deviceCount = (int) ($options['devices'] ?? 5);
$baseUrl = $options['base-url'] ?? 'http://127.0.0.1/es-git-training/rover-telemetry-backend/public';

$ranges = [
    'temperature_c' => [-40, 85],
    'humidity_pct' => [0, 100],
    'gas_ppm' => [0, 10000],
    'distance_cm' => [2, 400],
];

function buildPayload(string $deviceUid, array $ranges): string
{
    $payload = ['device_uid' => $deviceUid, 'auto_brake' => false];
    foreach ($ranges as $field => [$min, $max]) {
        $payload[$field] = round($min + mt_rand() / mt_getrandmax() * ($max - $min), 2);
    }

    return json_encode($payload);
}

$latenciesMs = [];
$success = 0;
$failure = 0;
$startedAt = microtime(true);

for ($i = 0; $i < $totalRequests; $i++) {
    $deviceUid = 'loadtest-rover-' . ($i % $deviceCount);
    $requestStartedAt = microtime(true);

    $ch = curl_init("{$baseUrl}/api/v1/telemetry");
    curl_setopt_array($ch, [
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => buildPayload($deviceUid, $ranges),
        CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
        CURLOPT_RETURNTRANSFER => true,
    ]);
    curl_exec($ch);
    $status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    $latenciesMs[] = (microtime(true) - $requestStartedAt) * 1000;
    $status === 201 ? $success++ : $failure++;
}

$totalSeconds = microtime(true) - $startedAt;
sort($latenciesMs);
$p50 = $latenciesMs[(int) (count($latenciesMs) * 0.50)];
$p95 = $latenciesMs[(int) (count($latenciesMs) * 0.95)];

printf(
    "Load test: %d requests in %.2fs — %d succeeded, %d failed — p50 %.1fms, p95 %.1fms\n",
    $totalRequests, $totalSeconds, $success, $failure, $p50, $p95
);
