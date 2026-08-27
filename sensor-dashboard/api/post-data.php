<?php
date_default_timezone_set('Asia/Ho_Chi_Minh');
header("Content-Type: application/json; charset=UTF-8");
require __DIR__ . "/../config.php";
$host = "localhost";
$dbname = "sensor_dashboard_db";
$username = "esiot";
$password = "1";
try {
  $pdo = new PDO("mysql:host=$host;dbname=$dbname;charset=utf8mb4", $username, $password, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC]);
} catch (PDOException $e) {
  http_response_code(500);
  echo json_encode(["success" => false, "message" => "Database connection failed"]);
  exit;
}
if ($_SERVER["REQUEST_METHOD"] !== "POST") {
  http_response_code(405);
  echo json_encode(["success" => false, "message" => "Only POST is allowed"]);
  exit;
}
$providedKey = $_SERVER["HTTP_X_API_KEY"] ?? $_GET['apiKey'] ?? "";
if (!hash_equals(API_KEY, $providedKey)) {
  http_response_code(401);
  echo json_encode(["success" => false, "message" => "Invalid or missing API key"]);
  exit;
}

$items = json_decode(file_get_contents("php://input"), true);
if (!is_array($items) || !array_is_list($items)) {
  http_response_code(400);
  echo json_encode(["success" => false, "message" => "Request body must be a JSON array"]);
  exit;
}
$valid = [];
foreach ($items as $item) {
  if (!is_array($item)) continue;
  $timestamp = $item["timestamp"] ?? null;
  $data = $item["data"] ?? null;
  $dataType = $item["data_type"] ?? null;
  $label = $item["label"] ?? null;
  if (!is_numeric($timestamp)) continue;
  if (!is_numeric($data)) continue;
  if (!is_string($dataType) || $dataType === "") continue;
  if (!is_string($label) || $label === "") continue;
  $valid[] = [
    "label" => $label,
    "data" => (float)$data,
    "data_type" => $dataType,
    "reading_time" => date("Y-m-d H:i:s", (int)$timestamp),
  ];
}
$skipped = count($items) - count($valid);
try {
  $pdo->beginTransaction();
  $stmt = $pdo->prepare("INSERT INTO sensor_readings (label, data, data_type, reading_time) VALUES (:label, :data, :data_type, :reading_time)");
  foreach ($valid as $row) {
    $stmt->execute($row);
  }
  $pdo->commit();
  echo json_encode(["success" => true, "inserted" => count($valid), "skipped" => $skipped]);
} catch (PDOException $e) {
  $pdo->rollBack();
  http_response_code(500);
  echo json_encode(["success" => false, "message" => "Failed to save sensor readings"]);
}
