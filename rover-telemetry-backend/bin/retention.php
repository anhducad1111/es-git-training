<?php

declare(strict_types=1);

require __DIR__ . '/../src/autoload.php';

use RoverTelemetry\Config;
use RoverTelemetry\Database;

function deleteInBatches(\PDO $pdo, string $sql, array $params): int
{
    $total = 0;
    $stmt = $pdo->prepare($sql);
    do {
        $stmt->execute($params);
        $deleted = $stmt->rowCount();
        $total += $deleted;
    } while ($deleted > 0);

    return $total;
}

$config = Config::fromEnv();
$pdo = Database::connection($config);
$now = new \DateTimeImmutable('now', new \DateTimeZone('UTC'));

$rawCutoff = $now->modify("-{$config->rawRetentionDays} days")->format('Y-m-d H:i:s.v');
$rawDeleted = deleteInBatches($pdo, 'DELETE FROM telemetry_readings WHERE recorded_at < :cutoff LIMIT 1000', ['cutoff' => $rawCutoff]);

$errorCutoff = $now->modify("-{$config->validationErrorRetentionDays} days")->format('Y-m-d H:i:s.v');
$errorsDeleted = deleteInBatches($pdo, 'DELETE FROM validation_errors WHERE received_at < :cutoff LIMIT 1000', ['cutoff' => $errorCutoff]);

$metricsCutoff = $now->modify("-{$config->gatewayMetricsRetentionDays} days")->format('Y-m-d H:i:s');
$metricsDeleted = deleteInBatches($pdo, 'DELETE FROM gateway_metrics WHERE sampled_at < :cutoff LIMIT 1000', ['cutoff' => $metricsCutoff]);

file_put_contents(__DIR__ . '/../storage/retention.lastrun', $now->format('Y-m-d\TH:i:s\Z'));

echo "Retention: removed {$rawDeleted} readings, {$errorsDeleted} validation errors, {$metricsDeleted} gateway metric samples\n";
