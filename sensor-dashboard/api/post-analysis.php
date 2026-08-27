<?php
date_default_timezone_set('Asia/Ho_Chi_Minh');
header("Content-Type: application/json; charset=UTF-8");
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

$body = json_decode(file_get_contents("php://input"), true);
$content = is_array($body) ? ($body["content"] ?? null) : null;
if (!is_string($content) || trim($content) === "") {
  http_response_code(400);
  echo json_encode(["success" => false, "message" => "content is required and must be a non-empty string"]);
  exit;
}

try {
  $createdAt = date("Y-m-d H:i:s");
  $stmt = $pdo->prepare("INSERT INTO analysis_logs (content, created_at) VALUES (:content, :created_at)");
  $stmt->execute([":content" => $content, ":created_at" => $createdAt]);
  echo json_encode(["success" => true, "id" => (int)$pdo->lastInsertId(), "created_at" => $createdAt], JSON_UNESCAPED_UNICODE);
} catch (PDOException $e) {
  http_response_code(500);
  echo json_encode(["success" => false, "message" => "Failed to save analysis"]);
}
