<?php

declare(strict_types=1);

namespace RoverTelemetry\Controllers;

use PDO;
use RoverTelemetry\Repositories\SensorLimitsRepository;

final class SensorLimitsGetController
{
    private SensorLimitsRepository $sensorLimits;

    public function __construct(PDO $pdo)
    {
        $this->sensorLimits = new SensorLimitsRepository($pdo);
    }

    public function get(): array
    {
        return ['status' => 200, 'body' => (object) $this->sensorLimits->allWithMetadata()];
    }
}
