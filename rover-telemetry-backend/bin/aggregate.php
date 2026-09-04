<?php

declare(strict_types=1);

require __DIR__ . '/../src/autoload.php';

use RoverTelemetry\Config;
use RoverTelemetry\Database;
use RoverTelemetry\Repositories\RoverRepository;
use RoverTelemetry\Repositories\SummaryRepository;

$config = Config::fromEnv();
$pdo = Database::connection($config);
$rovers = (new RoverRepository($pdo))->all();
$summaries = new SummaryRepository($pdo);

$now = new \DateTimeImmutable('now', new \DateTimeZone('UTC'));
$currentMinute = $now->setTime((int) $now->format('H'), (int) $now->format('i'), 0);
$currentHour = $now->setTime((int) $now->format('H'), 0, 0);
$currentDay = $now->setTime(0, 0, 0);

foreach ($rovers as $rover) {
    $deviceId = (int) $rover['id'];

    for ($i = 4; $i >= 0; $i--) {
        $summaries->recomputeBucket($deviceId, 'minute', $currentMinute->modify("-{$i} minutes"));
    }
    for ($i = 1; $i >= 0; $i--) {
        $summaries->recomputeBucket($deviceId, 'hour', $currentHour->modify("-{$i} hours"));
    }
    $summaries->recomputeBucket($deviceId, 'day', $currentDay);
}

file_put_contents(__DIR__ . '/../storage/aggregate.lastrun', $now->format('Y-m-d\TH:i:s\Z'));

echo "Aggregated " . count($rovers) . " rover(s) at {$now->format('Y-m-d H:i:s')} UTC\n";
