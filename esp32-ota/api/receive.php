<?php
declare(strict_types=1);
require_once dirname(__DIR__) . '/config.php';

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    send_json(['success' => false, 'message' => 'Use POST with file, ver, and optional version_information fields.'], 405);
}

require_key(OTA_ADMIN_KEY);

if (!isset($_FILES['file']) || !is_array($_FILES['file']) || $_FILES['file']['error'] !== UPLOAD_ERR_OK) {
    send_json(['success' => false, 'message' => 'No valid file was uploaded.'], 400);
}

$version = trim((string) ($_POST['ver'] ?? ''));
$versionInformation = trim((string) ($_POST['version_information'] ?? ''));
if ($version === '' || mb_strlen($version) > 64 || mb_strlen($versionInformation) > 255) {
    send_json(['success' => false, 'message' => 'ver is required (up to 64 characters); version_information is limited to 255 characters.'], 400);
}

$upload = $_FILES['file'];
if ($upload['size'] < 1 || $upload['size'] > 10 * 1024 * 1024) {
    send_json(['success' => false, 'message' => 'File size must be between 1 byte and 10 MB.'], 400);
}

$binary = file_get_contents($upload['tmp_name']);
if ($binary === false || strlen($binary) !== (int) $upload['size']) {
    send_json(['success' => false, 'message' => 'Could not read the uploaded file.'], 500);
}

try {
    $pdo = new PDO(
        'mysql:host=localhost;dbname=mini_db;charset=utf8mb4',
        'root',
        '',
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
    );
    $pdo->beginTransaction();

    $insert = $pdo->prepare('INSERT INTO storage (ver, `file`, version_information) VALUES (:ver, :file, :version_information)');
    $insert->bindValue(':ver', $version, PDO::PARAM_STR);
    $insert->bindValue(':file', $binary, PDO::PARAM_LOB);
    $insert->bindValue(':version_information', $versionInformation === '' ? null : $versionInformation, $versionInformation === '' ? PDO::PARAM_NULL : PDO::PARAM_STR);
    $insert->execute();
    $newId = (int) $pdo->lastInsertId();

    $keepIds = $pdo->query('SELECT id FROM storage ORDER BY `timestamp` DESC, id DESC LIMIT 5')->fetchAll(PDO::FETCH_COLUMN);
    $placeholders = implode(',', array_fill(0, count($keepIds), '?'));
    $delete = $pdo->prepare("DELETE FROM storage WHERE id NOT IN ($placeholders)");
    $delete->execute($keepIds);
    $deletedCount = $delete->rowCount();

    $pdo->commit();
    send_json([
        'success' => true,
        'message' => 'File stored in the database.',
        'id' => $newId,
        'version' => $version,
        'size' => (int) $upload['size'],
        'removed_old_records' => $deletedCount,
    ], 201);
} catch (Throwable $error) {
    if (isset($pdo) && $pdo->inTransaction()) {
        $pdo->rollBack();
    }
    send_json(['success' => false, 'message' => 'Database storage failed.'], 500);
}
