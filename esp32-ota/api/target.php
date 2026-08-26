<?php
declare(strict_types=1);
require_once dirname(__DIR__) . '/config.php';

require_key(OTA_ADMIN_KEY);

$method = $_SERVER['REQUEST_METHOD'];

if ($method === 'GET') {
    $pinnedId = ota_read_target_id();
    $entry = ota_resolve_target_entry();
    send_json([
        'success' => true,
        'pinned' => $pinnedId !== null,
        'id' => $entry['id'] ?? null,
        'version' => $entry['version'] ?? null,
        'client' => $entry['client'] ?? null,
    ]);
}

if ($method === 'POST') {
    $action = (string) ($_POST['action'] ?? 'set');

    if ($action === 'clear') {
        ota_write_target_id(null);
        $entry = ota_resolve_target_entry();
        send_json([
            'success' => true,
            'message' => 'Target cleared; devices will follow the latest build automatically.',
            'pinned' => false,
            'id' => $entry['id'] ?? null,
            'version' => $entry['version'] ?? null,
        ]);
    }

    $id = (int) ($_POST['id'] ?? 0);
    if ($id < 1) {
        send_json(['success' => false, 'message' => 'A valid id is required.'], 400);
    }

    $entry = ota_find_entry($id);
    if ($entry === null) {
        send_json(['success' => false, 'message' => 'Firmware not found.'], 404);
    }

    ota_write_target_id($id);
    send_json([
        'success' => true,
        'message' => 'Target pinned.',
        'pinned' => true,
        'id' => $entry['id'],
        'version' => $entry['version'],
    ]);
}

send_json(['success' => false, 'message' => 'Only GET and POST methods are allowed'], 405);
