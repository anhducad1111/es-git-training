CREATE TABLE IF NOT EXISTS rovers (
  id               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  device_uid       VARCHAR(64)  NOT NULL,
  name             VARCHAR(100) NULL,
  firmware_version VARCHAR(30)  NULL,
  enabled_sensors  SET('temperature_c','humidity_pct','gas_ppm','distance_cm')
                   NOT NULL DEFAULT 'temperature_c,humidity_pct,gas_ppm,distance_cm',
  last_seen_at     DATETIME(3)  NULL,
  created_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_rover_device_uid (device_uid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS telemetry_readings (
  device_id     BIGINT UNSIGNED NOT NULL,
  recorded_at   DATETIME(3)     NOT NULL,
  temperature_c FLOAT           NULL,
  humidity_pct  FLOAT           NULL,
  gas_ppm       FLOAT           NULL,
  distance_cm   FLOAT           NULL,
  auto_brake    TINYINT(1)      NOT NULL DEFAULT 0,
  PRIMARY KEY (device_id, recorded_at),
  KEY ix_reading_brake (device_id, auto_brake, recorded_at),
  CONSTRAINT fk_reading_rover FOREIGN KEY (device_id) REFERENCES rovers(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS telemetry_summaries (
  device_id       BIGINT UNSIGNED   NOT NULL,
  granularity     ENUM('minute','hour','day') NOT NULL,
  bucket_start    DATETIME          NOT NULL,
  sample_count    INT UNSIGNED      NOT NULL,
  temp_min FLOAT NULL, temp_avg FLOAT NULL, temp_max FLOAT NULL,
  hum_min  FLOAT NULL, hum_avg  FLOAT NULL, hum_max  FLOAT NULL,
  gas_min  FLOAT NULL, gas_avg  FLOAT NULL, gas_max  FLOAT NULL,
  dist_min FLOAT NULL, dist_avg FLOAT NULL, dist_max FLOAT NULL,
  obstacle_events INT UNSIGNED      NOT NULL DEFAULT 0,
  computed_at     DATETIME          NOT NULL,
  PRIMARY KEY (device_id, granularity, bucket_start),
  CONSTRAINT fk_summary_rover FOREIGN KEY (device_id) REFERENCES rovers(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS gateway_metrics (
  sampled_at          DATETIME     NOT NULL,
  cpu_load_percent    FLOAT        NOT NULL,
  cpu_temperature_c   FLOAT        NOT NULL,
  memory_used_percent FLOAT        NOT NULL,
  disk_used_percent   FLOAT        NOT NULL,
  ingest_rate_per_min INT UNSIGNED NOT NULL,
  database_size_mb    FLOAT        NOT NULL,
  PRIMARY KEY (sampled_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS validation_errors (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  device_uid  VARCHAR(64)  NULL,
  received_at DATETIME(3)  NOT NULL,
  error_code  VARCHAR(40)  NOT NULL,
  detail      VARCHAR(255) NOT NULL,
  raw_payload TEXT         NULL,
  PRIMARY KEY (id),
  KEY ix_validation_time (received_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS media_files (
  id                BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  device_id         BIGINT UNSIGNED NOT NULL,
  media_type        ENUM('photo','video') NOT NULL,
  file_path         VARCHAR(255) NOT NULL,
  captured_at       DATETIME(3)  NOT NULL,
  file_size_bytes   INT UNSIGNED NOT NULL DEFAULT 0,
  mime_type         VARCHAR(50)  NOT NULL DEFAULT 'image/jpeg',
  original_filename VARCHAR(200) NULL,
  file_hash         CHAR(64)     NULL,
  PRIMARY KEY (id),
  KEY ix_media_device_time (device_id, captured_at),
  CONSTRAINT fk_media_rover FOREIGN KEY (device_id) REFERENCES rovers(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS sensor_limits (
  field       VARCHAR(30) NOT NULL,
  min_value   FLOAT       NOT NULL,
  max_value   FLOAT       NOT NULL,
  updated_at  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (field)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO sensor_limits (field, min_value, max_value) VALUES
  ('temperature_c', -40,  85),
  ('humidity_pct',    0, 100),
  ('gas_ppm',         0, 10000),
  ('distance_cm',     2, 400)
ON DUPLICATE KEY UPDATE min_value = VALUES(min_value), max_value = VALUES(max_value);
