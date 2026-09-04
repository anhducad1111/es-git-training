<?php

declare(strict_types=1);

namespace RoverTelemetry;

use RoverTelemetry\Support\ApiException;

final class Router
{
    /** @var array<int, array{method: string, pattern: string, handler: callable}> */
    private array $routes = [];

    public function add(string $method, string $pattern, callable $handler): void
    {
        $this->routes[] = ['method' => strtoupper($method), 'pattern' => $pattern, 'handler' => $handler];
    }

    public function dispatch(string $method, string $path): mixed
    {
        foreach ($this->routes as $route) {
            if ($route['method'] !== strtoupper($method)) {
                continue;
            }
            if (preg_match('#^' . $route['pattern'] . '$#', $path, $matches)) {
                $params = array_filter($matches, fn($key) => is_string($key), ARRAY_FILTER_USE_KEY);
                return ($route['handler'])($params);
            }
        }

        throw new ApiException(404, 'NOT_FOUND', "No route for {$method} {$path}");
    }
}
