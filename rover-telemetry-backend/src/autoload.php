<?php

declare(strict_types=1);

spl_autoload_register(function (string $class): void {
    $map = [
        'RoverTelemetry\\Tests\\' => __DIR__ . '/../tests/',
        'RoverTelemetry\\' => __DIR__ . '/',
    ];

    foreach ($map as $prefix => $baseDir) {
        if (str_starts_with($class, $prefix)) {
            $relative = substr($class, strlen($prefix));
            $file = $baseDir . str_replace('\\', '/', $relative) . '.php';
            if (is_file($file)) {
                require $file;
            }
            return;
        }
    }
});
