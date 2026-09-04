<?php

declare(strict_types=1);

namespace RoverTelemetry\Tests\Support;

abstract class HttpTestCase extends DatabaseTestCase
{
    /** @var resource|null */
    private static $serverProcess = null;
    protected static string $baseUrl = 'http://127.0.0.1:8089';

    public static function setUpBeforeClass(): void
    {
        $publicDir = __DIR__ . '/../../public';
        $descriptors = [1 => ['pipe', 'w'], 2 => ['pipe', 'w']];

        // env is left null (inherit the current process's environment) rather than passed
        // as an explicit array: on Windows, replacing the full environment drops SystemRoot
        // and other variables winsock needs, which makes the child fail to bind/listen.
        // tests/bootstrap.php already putenv()'s the DB_*/MEDIA_STORAGE_PATH values this
        // child needs, and putenv() affects the process environment block that a child
        // inherits automatically.
        self::$serverProcess = proc_open(
            ['C:/xampp/php/php.exe', '-S', '127.0.0.1:8089', '-t', $publicDir],
            $descriptors,
            $pipes
        );

        $deadline = microtime(true) + 10;
        while (microtime(true) < $deadline) {
            $conn = @fsockopen('127.0.0.1', 8089);
            if ($conn !== false) {
                fclose($conn);
                return;
            }
            usleep(100_000);
        }
        throw new \RuntimeException('PHP built-in server did not start in time');
    }

    public static function tearDownAfterClass(): void
    {
        if (self::$serverProcess !== null) {
            proc_terminate(self::$serverProcess);
            proc_close(self::$serverProcess);
            self::$serverProcess = null;
        }
    }

    protected function request(string $method, string $path, ?array $jsonBody = null): array
    {
        $ch = curl_init(self::$baseUrl . $path);
        $options = [
            CURLOPT_CUSTOMREQUEST => $method,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_HEADER => true,
        ];
        if ($jsonBody !== null) {
            $options[CURLOPT_POSTFIELDS] = json_encode($jsonBody);
            $options[CURLOPT_HTTPHEADER] = ['Content-Type: application/json'];
        }
        curl_setopt_array($ch, $options);
        $raw = curl_exec($ch);
        $status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $headerSize = curl_getinfo($ch, CURLINFO_HEADER_SIZE);
        curl_close($ch);

        return [
            'status' => $status,
            'headers' => substr($raw, 0, $headerSize),
            'body' => substr($raw, $headerSize),
        ];
    }
}
