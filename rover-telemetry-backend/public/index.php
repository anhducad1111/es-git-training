<?php

declare(strict_types=1);

require __DIR__ . '/../src/autoload.php';

use RoverTelemetry\Config;
use RoverTelemetry\Database;
use RoverTelemetry\Router;
use RoverTelemetry\Support\ApiException;
use RoverTelemetry\Controllers\TelemetryController;
use RoverTelemetry\Controllers\RoverController;

header('Content-Type: application/json; charset=UTF-8');

$config = Config::fromEnv();
$requestId = bin2hex(random_bytes(16));

try {
    $pdo = Database::connection($config);
} catch (\PDOException $e) {
    http_response_code(503);
    echo json_encode(['error' => ['code' => 'SERVICE_UNAVAILABLE', 'message' => 'Database unreachable', 'request_id' => $requestId]]);
    exit;
}

$router = new Router();
$telemetryController = new TelemetryController($pdo);
$roverController = new RoverController($pdo, $config);

$router->add('POST', '/api/v1/telemetry', function () use ($telemetryController) {
    $raw = file_get_contents('php://input');
    $body = json_decode($raw, true);
    if (!is_array($body)) {
        throw new ApiException(400, 'MALFORMED_PAYLOAD', 'Request body must be valid JSON');
    }
    return $telemetryController->ingest($body);
});

$router->add('GET', '/api/v1/rovers', function () use ($roverController) {
    return $roverController->list();
});

$router->add('GET', '/api/v1/rovers/(?P<device_uid>[A-Za-z0-9_-]+)/latest', function (array $params) use ($roverController) {
    return $roverController->latest($params);
});

$router->add('GET', '/api/v1/rovers/(?P<device_uid>[A-Za-z0-9_-]+)/readings', function (array $params) use ($roverController) {
    return $roverController->readings($params, $_GET);
});

$uri = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?? '/';
$apiPos = strpos($uri, '/api/v1');
$path = $apiPos !== false ? substr($uri, $apiPos) : $uri;

try {
    $result = $router->dispatch($_SERVER['REQUEST_METHOD'] ?? 'GET', $path);

    if ($result === null) {
        exit;
    }

    http_response_code($result['status']);
    echo json_encode($result['body']);
} catch (ApiException $e) {
    http_response_code($e->httpStatus);
    echo json_encode($e->toArray($requestId));
} catch (\Throwable $e) {
    http_response_code(500);
    echo json_encode(['error' => ['code' => 'INTERNAL_ERROR', 'message' => 'Unexpected server error', 'request_id' => $requestId]]);
}
