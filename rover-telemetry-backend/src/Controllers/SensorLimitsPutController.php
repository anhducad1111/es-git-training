<?php

declare(strict_types=1);

namespace RoverTelemetry\Controllers;

use PDO;
use RoverTelemetry\Repositories\SensorLimitsRepository;
use RoverTelemetry\Support\ApiException;

final class SensorLimitsPutController
{
    private SensorLimitsRepository $sensorLimits;

    public function __construct(PDO $pdo)
    {
        $this->sensorLimits = new SensorLimitsRepository($pdo);
    }

    public function put(array $params, array $body): array
    {
        $field = $params['field'];
        if (!isset($body['min']) || !isset($body['max']) || !is_numeric($body['min']) || !is_numeric($body['max'])) {
            throw new ApiException(422, 'MISSING_FIELD', 'min and max are both required and must be numeric');
        }
        $min = (float) $body['min'];
        $max = (float) $body['max'];
        if ($min >= $max) {
            throw new ApiException(400, 'INVALID_PARAMETER', 'min must be less than max');
        }

        $updated = $this->sensorLimits->update($field, $min, $max);
        if ($updated === null) {
            throw new ApiException(404, 'NOT_FOUND', "Unknown sensor limits field '{$field}'");
        }

        return [
            'status' => 200,
            'body' => [
                'field' => $updated['field'],
                'min' => (float) $updated['min_value'],
                'max' => (float) $updated['max_value'],
                'updated_at' => (new \DateTimeImmutable($updated['updated_at'], new \DateTimeZone('UTC')))->format('Y-m-d\TH:i:s\Z'),
            ],
        ];
    }
}
