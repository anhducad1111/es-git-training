CREATE DATABASE IF NOT EXISTS sensor_dashboard_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE sensor_dashboard_db;

CREATE TABLE IF NOT EXISTS sensor_readings (
  id INT AUTO_INCREMENT PRIMARY KEY,
  label VARCHAR(32) NOT NULL,
  data DOUBLE NOT NULL,
  data_type VARCHAR(16) NOT NULL,
  reading_time DATETIME NOT NULL,
  INDEX idx_label_time (label, reading_time)
);
