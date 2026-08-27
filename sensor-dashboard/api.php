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
$method = $_SERVER["REQUEST_METHOD"];

http_response_code(405);
echo json_encode(["success" => false, "message" => "Only GET and POST methods are allowed"]);
