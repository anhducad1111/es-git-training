<?php

declare(strict_types=1);

$options = getopt('', ['device:', 'count:', 'interval-ms:', 'base-url:']);
$deviceUid = $options['device'] ?? 'sim-rover-001';
$count = (int) ($options['count'] ?? 100);
$intervalMs = (int) ($options['interval-ms'] ?? 1000);
$baseUrl = $options['base-url'] ?? 'http://127.0.0.1/es-git-training/rover-telemetry-backend/public';

$ranges = [
    'temperature_c' => [-40, 85],
    'humidity_pct' => [0, 100],
    'gas_ppm' => [0, 10000],
    'distance_cm' => [2, 400],
];

$sent = 0;
$failed = 0;

for ($i = 0; $i < $count; $i++) {
    $payload = ['device_uid' => $deviceUid, 'auto_brake' => (mt_rand(0, 20) === 0)];
    foreach ($ranges as $field => [$min, $max]) {
        $payload[$field] = round($min + mt_rand() / mt_getrandmax() * ($max - $min), 2);
    }

    $ch = curl_init("{$baseUrl}/api/v1/telemetry");
    curl_setopt_array($ch, [
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => json_encode($payload),
        CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
        CURLOPT_RETURNTRANSFER => true,
    ]);
    curl_exec($ch);
    $status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    $status === 201 ? $sent++ : $failed++;

    if ($intervalMs > 0 && $i < $count - 1) {
        usleep($intervalMs * 1000);
    }
}

echo "Simulated {$deviceUid}: {$sent} sent, {$failed} failed\n";
