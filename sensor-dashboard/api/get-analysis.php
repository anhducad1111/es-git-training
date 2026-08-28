<?php
date_default_timezone_set('Asia/Ho_Chi_Minh');
header("Content-Type: application/json; charset=UTF-8");
$host = "localhost";
$dbname = "sensor_dashboard_db";
$username = "root";
$password = "";
try {
  $pdo = new PDO("mysql:host=$host;dbname=$dbname;charset=utf8mb4", $username, $password, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC]);
} catch (PDOException $e) {
  http_response_code(500);
  echo json_encode(["success" => false, "message" => "Database connection failed"]);
  exit;
}
if ($_SERVER["REQUEST_METHOD"] !== "GET") {
  http_response_code(405);
  echo json_encode(["success" => false, "message" => "Only GET is allowed"]);
  exit;
}

try {
  $cutoff = date("Y-m-d H:i:s", time() - 30 * 60);
  $stmt = $pdo->prepare("SELECT id, content, created_at FROM analysis_logs WHERE created_at >= :cutoff ORDER BY created_at DESC, id DESC LIMIT 1");
  $stmt->execute([":cutoff" => $cutoff]);
  echo json_encode(["success" => true, "server_time" => date("Y-m-d H:i:s"), "logs" => $stmt->fetchAll()], JSON_UNESCAPED_UNICODE);
} catch (PDOException $e) {
  http_response_code(500);
  echo json_encode(["success" => false, "message" => "Failed to fetch analysis logs"]);
}
