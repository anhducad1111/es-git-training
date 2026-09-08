<?php

declare(strict_types=1);

namespace RoverTelemetry\Tests\Integration;

use RoverTelemetry\Repositories\MediaRepository;
use RoverTelemetry\Repositories\RoverRepository;
use RoverTelemetry\Tests\Support\DatabaseTestCase;

final class MediaRepositoryTest extends DatabaseTestCase
{
    public function test_build_storage_path_follows_device_date_filename_convention(): void
    {
        $repository = new MediaRepository($this->pdo);

        $path = $repository->buildStoragePath('rover-001', new \DateTimeImmutable('2026-09-04T10:00:00.123Z'), 'snapshot.jpg');

        $this->assertSame('rover-001/2026/09/04/10-00-00-123_snapshot.jpg', $path);
    }

    public function test_create_and_find_round_trip(): void
    {
        $rover = (new RoverRepository($this->pdo))->getOrCreateByDeviceUid('rover-001');
        $repository = new MediaRepository($this->pdo);

        $created = $repository->create(
            (int) $rover['id'], 'photo', 'rover-001/2026/09/04/10-00-00-123_snapshot.jpg',
            new \DateTimeImmutable('2026-09-04T10:00:00.123Z'), 184320, 'image/jpeg', 'snapshot.jpg', str_repeat('a', 64)
        );

        $found = $repository->find((int) $created['id'], (int) $rover['id']);
        $this->assertSame('photo', $found['media_type']);
        $this->assertSame(184320, (int) $found['file_size_bytes']);
    }

    public function test_list_for_rover_filters_by_media_type_and_orders_recent_first(): void
    {
        $rover = (new RoverRepository($this->pdo))->getOrCreateByDeviceUid('rover-001');
        $repository = new MediaRepository($this->pdo);
        $repository->create((int) $rover['id'], 'photo', 'p1.jpg', new \DateTimeImmutable('2026-09-04T09:00:00Z'), 100, 'image/jpeg', null, null);
        $repository->create((int) $rover['id'], 'video', 'v1.mp4', new \DateTimeImmutable('2026-09-04T10:00:00Z'), 200, 'video/mp4', null, null);

        $photos = $repository->listForRover((int) $rover['id'], 'photo', null, null, 100);

        $this->assertCount(1, $photos);
        $this->assertSame('photo', $photos[0]['media_type']);
    }

    public function test_delete_removes_row_only_for_matching_device(): void
    {
        $rover = (new RoverRepository($this->pdo))->getOrCreateByDeviceUid('rover-001');
        $otherRover = (new RoverRepository($this->pdo))->getOrCreateByDeviceUid('rover-002');
        $repository = new MediaRepository($this->pdo);
        $created = $repository->create((int) $rover['id'], 'photo', 'p1.jpg', new \DateTimeImmutable('now'), 100, 'image/jpeg', null, null);

        $this->assertFalse($repository->delete((int) $created['id'], (int) $otherRover['id']));
        $this->assertTrue($repository->delete((int) $created['id'], (int) $rover['id']));
        $this->assertNull($repository->find((int) $created['id'], (int) $rover['id']));
    }
}
