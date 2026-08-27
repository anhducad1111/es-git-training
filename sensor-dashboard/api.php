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

if ($method === "GET") {
  try {
    $latest = [];
    $latestStmt = $pdo->query("SELECT r.label, r.data, r.reading_time FROM sensor_readings r INNER JOIN (SELECT label, MAX(reading_time) AS max_time FROM sensor_readings GROUP BY label) m ON r.label = m.label AND r.reading_time = m.max_time");
    foreach ($latestStmt->fetchAll() as $row) {
      $latest[$row["label"]] = ["data" => (float)$row["data"], "reading_time" => $row["reading_time"]];
    }
    $history = [];
    $labelsStmt = $pdo->query("SELECT DISTINCT label FROM sensor_readings");
    foreach ($labelsStmt->fetchAll() as $labelRow) {
      $label = $labelRow["label"];
      $historyStmt = $pdo->prepare("SELECT reading_time, data FROM (SELECT reading_time, data FROM sensor_readings WHERE label = :label ORDER BY reading_time DESC LIMIT 100) t ORDER BY reading_time ASC");
      $historyStmt->execute([":label" => $label]);
      $history[$label] = array_map(fn($r) => ["reading_time" => $r["reading_time"], "data" => (float)$r["data"]], $historyStmt->fetchAll());
    }
    echo json_encode(["success" => true, "server_time" => date("Y-m-d H:i:s"), "latest" => (object)$latest, "history" => (object)$history], JSON_UNESCAPED_UNICODE);
  } catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(["success" => false, "message" => "Failed to fetch sensor readings"]);
  }
  exit;
}

if ($method === "POST") {
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
  exit;
}

http_response_code(405);
echo json_encode(["success" => false, "message" => "Only GET and POST methods are allowed"]);
