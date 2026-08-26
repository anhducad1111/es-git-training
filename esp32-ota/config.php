<?php
declare(strict_types=1);

// Change all values below before using this outside a trusted local network.
const OTA_PUBLIC_BASE_URL = 'http://192.168.1.116/esp32-ota';
const OTA_ADMIN_KEY = 'shodai-haru-2026-8-25';
const OTA_DEVICE_KEY = 'ota-device-2026-8-25';
const OTA_MAX_FIRMWARE_BYTES = 2_000_000;
const OTA_FIRMWARE_DIRECTORY = __DIR__ . DIRECTORY_SEPARATOR . 'firmware';
const OTA_TARGET_FILE = __DIR__ . DIRECTORY_SEPARATOR . 'target.json';
const OTA_KEEP_LATEST = 5;

date_default_timezone_set('Asia/Ho_Chi_Minh');

/** Stored firmware filenames look like: {id}-{filename}-{version}-{info}-{client}-{timestamp}.{ext} */
function ota_firmware_files(): array {
    if (!is_dir(OTA_FIRMWARE_DIRECTORY)) {
        return [];
    }
    $paths = glob(OTA_FIRMWARE_DIRECTORY . DIRECTORY_SEPARATOR . '*') ?: [];
    return array_filter($paths, 'is_file');
}

function ota_parse_stored_file(string $path): ?array {
    $base = pathinfo($path, PATHINFO_FILENAME);
    $parts = explode('-', $base);
    if (count($parts) !== 6 || !ctype_digit($parts[0])) {
        return null;
    }
    [$id, $filename, $version, $info, $client, $timestamp] = $parts;
    return [
        'id' => (int) $id,
        'filename' => $filename,
        'version' => $version,
        'info' => $info,
        'client' => $client,
        'timestamp' => $timestamp,
        'path' => $path,
        'size' => filesize($path),
    ];
}

/** All parsed, valid firmware entries, newest (highest id) first. */
function ota_list_entries(): array {
    $entries = array_values(array_filter(array_map('ota_parse_stored_file', ota_firmware_files())));
    usort($entries, fn(array $a, array $b) => $b['id'] <=> $a['id']);
    return $entries;
}

function ota_next_id(): int {
    $maxId = 0;
    foreach (ota_list_entries() as $entry) {
        $maxId = max($maxId, $entry['id']);
    }
    return $maxId + 1;
}

function ota_timestamp(): string {
    return date('YmdHis');
}

function ota_latest_entry(): ?array {
    $entries = ota_list_entries();
    return $entries[0] ?? null;
}

function ota_find_entry(int $id): ?array {
    foreach (ota_list_entries() as $entry) {
        if ($entry['id'] === $id) {
            return $entry;
        }
    }
    return null;
}

/** Deletes everything but the newest OTA_KEEP_LATEST files; returns removed filenames. */
function ota_prune_old_files(int $keep = OTA_KEEP_LATEST): array {
    $removed = [];
    foreach (array_slice(ota_list_entries(), $keep) as $entry) {
        if (@unlink($entry['path'])) {
            $removed[] = basename($entry['path']);
        }
    }
    return $removed;
}

/** Version strings look like "1_0_3"; returns [1,0,3] or null if any segment isn't numeric. */
function ota_parse_version_parts(string $version): ?array {
    $parts = explode('_', $version);
    $numeric = [];
    foreach ($parts as $part) {
        if ($part === '' || !ctype_digit($part)) {
            return null;
        }
        $numeric[] = (int) $part;
    }
    return $numeric;
}

/** Compares two "1_0_3"-style versions numerically; returns null if either can't be parsed. */
function ota_compare_versions(string $a, string $b): ?int {
    $partsA = ota_parse_version_parts($a);
    $partsB = ota_parse_version_parts($b);
    if ($partsA === null || $partsB === null) {
        return null;
    }
    $length = max(count($partsA), count($partsB));
    for ($i = 0; $i < $length; $i++) {
        $x = $partsA[$i] ?? 0;
        $y = $partsB[$i] ?? 0;
        if ($x !== $y) {
            return $x <=> $y;
        }
    }
    return 0;
}

/** Reads the pinned firmware id, or null when following the latest build automatically. */
function ota_read_target_id(): ?int {
    if (!is_file(OTA_TARGET_FILE)) {
        return null;
    }
    $data = json_decode((string) file_get_contents(OTA_TARGET_FILE), true);
    if (!is_array($data) || !isset($data['id']) || !is_int($data['id']) || $data['id'] < 1) {
        return null;
    }
    return $data['id'];
}

/** Pins a specific firmware id, or pass null to resume auto-following the latest build. */
function ota_write_target_id(?int $id): void {
    file_put_contents(OTA_TARGET_FILE, json_encode(['id' => $id]), LOCK_EX);
}

/** The entry devices should be served: the pinned one if it still exists, else the latest. */
function ota_resolve_target_entry(): ?array {
    $pinnedId = ota_read_target_id();
    if ($pinnedId !== null) {
        $entry = ota_find_entry($pinnedId);
        if ($entry !== null) {
            return $entry;
        }
    }
    return ota_latest_entry();
}

function send_json(array $data, int $status = 200): never {
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    echo json_encode($data, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    exit;
}

function supplied_key(): string {
    return (string) ($_SERVER['HTTP_X_OTA_KEY'] ?? $_POST['ota_key'] ?? '');
}

function require_key(string $expected): void {
    if ($expected === '' || str_starts_with($expected, 'replace-with-') || !hash_equals($expected, supplied_key())) {
        send_json(['success' => false, 'message' => 'Unauthorized'], 401);
    }
}
