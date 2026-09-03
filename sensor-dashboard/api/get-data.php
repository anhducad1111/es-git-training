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

function parseDateTimeParam($value) {
  $dt = DateTime::createFromFormat("Y-m-d H:i:s", $value);
  $errors = DateTime::getLastErrors();
  if (!$dt || ($errors !== false && ($errors["warning_count"] > 0 || $errors["error_count"] > 0))) {
    return null;
  }
  return $dt->format("Y-m-d H:i:s");
}

$from = null;
$to = null;
if (isset($_GET["from"]) && $_GET["from"] !== "") {
  $from = parseDateTimeParam($_GET["from"]);
  if ($from === null) {
    http_response_code(400);
    echo json_encode(["success" => false, "message" => "Invalid 'from' format, expected Y-m-d H:i:s"]);
    exit;
  }
}
if (isset($_GET["to"]) && $_GET["to"] !== "") {
  $to = parseDateTimeParam($_GET["to"]);
  if ($to === null) {
    http_response_code(400);
    echo json_encode(["success" => false, "message" => "Invalid 'to' format, expected Y-m-d H:i:s"]);
    exit;
  }
}

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
    if ($from === null && $to === null) {
      $historyStmt = $pdo->prepare("SELECT reading_time, data FROM (SELECT reading_time, data FROM sensor_readings WHERE label = :label ORDER BY reading_time DESC LIMIT 100) t ORDER BY reading_time ASC");
      $historyStmt->execute([":label" => $label]);
    } else {
      $conditions = ["label = :label"];
      $params = [":label" => $label];
      if ($from !== null) {
        $conditions[] = "reading_time >= :from";
        $params[":from"] = $from;
      }
      if ($to !== null) {
        $conditions[] = "reading_time <= :to";
        $params[":to"] = $to;
      }
      $historyStmt = $pdo->prepare("SELECT reading_time, data FROM sensor_readings WHERE " . implode(" AND ", $conditions) . " ORDER BY reading_time ASC");
      $historyStmt->execute($params);
    }
    $history[$label] = array_map(fn($r) => ["reading_time" => $r["reading_time"], "data" => (float)$r["data"]], $historyStmt->fetchAll());
  }
  echo json_encode(["success" => true, "server_time" => date("Y-m-d H:i:s"), "latest" => (object)$latest, "history" => (object)$history], JSON_UNESCAPED_UNICODE);
} catch (PDOException $e) {
  http_response_code(500);
  echo json_encode(["success" => false, "message" => "Failed to fetch sensor readings"]);
}
