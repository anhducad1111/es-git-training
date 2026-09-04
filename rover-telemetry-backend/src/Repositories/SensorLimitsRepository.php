<?php

declare(strict_types=1);

namespace RoverTelemetry\Repositories;

use PDO;

final class SensorLimitsRepository
{
    public function __construct(private readonly PDO $pdo)
    {
    }

    public function all(): array
    {
        $rows = $this->pdo->query('SELECT field, min_value, max_value FROM sensor_limits')->fetchAll();
        $ranges = [];
        foreach ($rows as $row) {
            $ranges[$row['field']] = [(float) $row['min_value'], (float) $row['max_value']];
        }

        return $ranges;
    }

    public function allWithMetadata(): array
    {
        $rows = $this->pdo->query('SELECT field, min_value, max_value, updated_at FROM sensor_limits')->fetchAll();
        $result = [];
        foreach ($rows as $row) {
            $result[$row['field']] = [
                'min' => (float) $row['min_value'],
                'max' => (float) $row['max_value'],
                'updated_at' => (new \DateTimeImmutable($row['updated_at'], new \DateTimeZone('UTC')))->format('Y-m-d\TH:i:s\Z'),
            ];
        }

        return $result;
    }

    public function get(string $field): ?array
    {
        $stmt = $this->pdo->prepare('SELECT field, min_value, max_value, updated_at FROM sensor_limits WHERE field = :field');
        $stmt->execute(['field' => $field]);
        $row = $stmt->fetch();

        return $row === false ? null : $row;
    }

    public function update(string $field, float $min, float $max): ?array
    {
        if ($this->get($field) === null) {
            return null;
        }

        $stmt = $this->pdo->prepare('UPDATE sensor_limits SET min_value = :min, max_value = :max WHERE field = :field');
        $stmt->execute(['min' => $min, 'max' => $max, 'field' => $field]);

        return $this->get($field);
    }
}
