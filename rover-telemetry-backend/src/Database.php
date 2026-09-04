<?php

declare(strict_types=1);

namespace RoverTelemetry;

use PDO;

final class Database
{
    private static ?PDO $instance = null;

    public static function connection(Config $config): PDO
    {
        if (self::$instance !== null) {
            return self::$instance;
        }

        self::$instance = self::newConnection($config, buffered: true);

        return self::$instance;
    }

    public static function newConnection(Config $config, bool $buffered = true): PDO
    {
        $dsn = sprintf(
            'mysql:host=%s;port=%d;dbname=%s;charset=utf8mb4',
            $config->dbHost,
            $config->dbPort,
            $config->dbName
        );

        return new PDO($dsn, $config->dbUser, $config->dbPassword, [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::MYSQL_ATTR_USE_BUFFERED_QUERY => $buffered,
        ]);
    }

    public static function reset(): void
    {
        self::$instance = null;
    }
}
