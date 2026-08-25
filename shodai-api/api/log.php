<?php
date_default_timezone_set('Asia/Ho_Chi_Minh');
header("Content-Type: application/json; charset=UTF-8");
$host = "localhost";
$dbname = "mini_db";
$username = "root";
$password = "";
try {
  $pdo = new PDO("mysql:host=$host;dbname=$dbname;charset=utf8mb4", $username, $password, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC]);
} catch (PDOException $e) {
  http_response_code(500);
  echo json_encode(["success" => false, "message" => "Database connection failed"]);
  exit;
}
$method = $_SERVER["REQUEST_METHOD"];
if ($method === "GET") {
  try {
    $stmt = $pdo->query("SELECT id, device_name, temperature, humidity, created_at FROM sensor_logs ORDER BY created_at DESC, id DESC LIMIT 10");
    echo json_encode(["success" => true, "data" => $stmt->fetchAll(), "server_time" => date("Y-m-d H:i:s")], JSON_UNESCAPED_UNICODE);
  } catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(["success" => false, "message" => "Failed to fetch sensor data"]);
  }
  exit;
}
if ($method === "POST") {
  $data = json_decode(file_get_contents("php://input"), true);
  if (!is_array($data)) {
    http_response_code(400);
    echo json_encode(["success" => false, "message" => "Invalid JSON"]);
    exit;
  }
  $device = $data["device"] ?? null;
  $temp = $data["temp"] ?? null;
  $humidity = $data["humidity"] ?? null;
  if ($device === null || $temp === null || $humidity === null) {
    http_response_code(400);
    echo json_encode(["success" => false, "message" => "device, temp and humidity are required"]);
    exit;
  }
  try {
    $stmt = $pdo->prepare("INSERT INTO sensor_logs (device_name, temperature, humidity, created_at) VALUES (:device,:temperature,:humidity,:created_at)");
    $received_time = date("Y-m-d H:i:s");
    $stmt->execute([":device" => $device, ":temperature" => $temp, ":humidity" => $humidity, ":created_at" => $received_time]);
    echo json_encode(["success" => true, "message" => "Sensor data saved successfully", "data" => ["id" => $pdo->lastInsertId(), "device" => $device, "temperature" => $temp, "humidity" => $humidity, "created_at" => $received_time]], JSON_UNESCAPED_UNICODE);
  } catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(["success" => false, "message" => "Failed to save sensor data"]);
  }
  exit;
}
http_response_code(405);
echo json_encode(["success" => false, "message" => "Only GET and POST methods are allowed"]);
