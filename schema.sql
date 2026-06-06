CREATE DATABASE IF NOT EXISTS airhub_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE airhub_db;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_no VARCHAR(64) NOT NULL,
    lastname VARCHAR(100) NOT NULL,
    firstname VARCHAR(100) NOT NULL,
    middlename VARCHAR(100) NOT NULL DEFAULT '',
    fullname VARCHAR(255) NOT NULL,
    course VARCHAR(100) NOT NULL,
    project_type VARCHAR(100) NOT NULL,
    room VARCHAR(100) NOT NULL,
    nfc_code VARCHAR(128) NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_users_student_no (student_no),
    INDEX idx_users_nfc_code (nfc_code)
);

CREATE TABLE IF NOT EXISTS user_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nfc_code VARCHAR(128) NOT NULL,
    date_logged TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_logs_nfc_code (nfc_code),
    INDEX idx_user_logs_date_logged (date_logged),
    INDEX idx_user_logs_card_day (nfc_code, date_logged)
);

CREATE TABLE IF NOT EXISTS firebase_sync_queue (
    id INT AUTO_INCREMENT PRIMARY KEY,
    record_type ENUM('user','log') NOT NULL,
    record_id INT NOT NULL,
    attempts INT NOT NULL DEFAULT 0,
    last_error TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    synced_at TIMESTAMP NULL DEFAULT NULL,
    UNIQUE KEY uniq_firebase_sync_record (record_type, record_id),
    INDEX idx_firebase_sync_pending (synced_at, updated_at)
);

CREATE OR REPLACE VIEW user_logs_info AS
SELECT
    l.id,
    l.nfc_code,
    DATE_FORMAT(l.date_logged, '%Y-%m-%d %H:%i:%s') AS date_logged,
    COALESCE(u.student_no, '') AS student_no,
    COALESCE(u.lastname, 'GUEST') AS lastname,
    COALESCE(u.firstname, '') AS firstname,
    COALESCE(u.fullname, 'Guest') AS fullname,
    CASE
        WHEN u.id IS NULL THEN 'GUEST_PENDING'
        WHEN (
            SELECT COUNT(*)
            FROM user_logs day_logs
            WHERE day_logs.nfc_code = l.nfc_code
              AND day_logs.date_logged >= DATE(l.date_logged)
              AND day_logs.date_logged < DATE(l.date_logged) + INTERVAL 1 DAY
              AND (
                day_logs.date_logged < l.date_logged
                OR (day_logs.date_logged = l.date_logged AND day_logs.id <= l.id)
              )
        ) % 2 = 1 THEN 'TAP_IN'
        ELSE 'TAP_OUT'
    END AS status,
    CASE
        WHEN (
            SELECT COUNT(*)
            FROM user_logs day_logs
            WHERE day_logs.nfc_code = l.nfc_code
              AND day_logs.date_logged >= DATE(l.date_logged)
              AND day_logs.date_logged < DATE(l.date_logged) + INTERVAL 1 DAY
              AND (
                day_logs.date_logged < l.date_logged
                OR (day_logs.date_logged = l.date_logged AND day_logs.id <= l.id)
              )
        ) % 2 = 1 THEN 'LOGIN'
        ELSE 'LOGOUT'
    END AS event_type,
    CASE
        WHEN (
            SELECT COUNT(*)
            FROM user_logs day_logs
            WHERE day_logs.nfc_code = l.nfc_code
              AND day_logs.date_logged >= DATE(l.date_logged)
              AND day_logs.date_logged < DATE(l.date_logged) + INTERVAL 1 DAY
              AND (
                day_logs.date_logged < l.date_logged
                OR (day_logs.date_logged = l.date_logged AND day_logs.id <= l.id)
              )
        ) % 2 = 1 THEN DATE_FORMAT(l.date_logged, '%Y-%m-%d %H:%i:%s')
        ELSE DATE_FORMAT((
            SELECT previous_log.date_logged
            FROM user_logs previous_log
            WHERE previous_log.nfc_code = l.nfc_code
              AND previous_log.date_logged >= DATE(l.date_logged)
              AND previous_log.date_logged < DATE(l.date_logged) + INTERVAL 1 DAY
              AND (
                previous_log.date_logged < l.date_logged
                OR (previous_log.date_logged = l.date_logged AND previous_log.id < l.id)
              )
            ORDER BY previous_log.date_logged DESC, previous_log.id DESC
            LIMIT 1
        ), '%Y-%m-%d %H:%i:%s')
    END AS time_entered,
    CASE
        WHEN (
            SELECT COUNT(*)
            FROM user_logs day_logs
            WHERE day_logs.nfc_code = l.nfc_code
              AND day_logs.date_logged >= DATE(l.date_logged)
              AND day_logs.date_logged < DATE(l.date_logged) + INTERVAL 1 DAY
              AND (
                day_logs.date_logged < l.date_logged
                OR (day_logs.date_logged = l.date_logged AND day_logs.id <= l.id)
              )
        ) % 2 = 0 THEN DATE_FORMAT(l.date_logged, '%Y-%m-%d %H:%i:%s')
        ELSE NULL
    END AS time_left,
    CASE
        WHEN (
            SELECT COUNT(*)
            FROM user_logs day_logs
            WHERE day_logs.nfc_code = l.nfc_code
              AND day_logs.date_logged >= DATE(l.date_logged)
              AND day_logs.date_logged < DATE(l.date_logged) + INTERVAL 1 DAY
              AND (
                day_logs.date_logged < l.date_logged
                OR (day_logs.date_logged = l.date_logged AND day_logs.id <= l.id)
              )
        ) % 2 = 0 THEN TIMESTAMPDIFF(SECOND, (
            SELECT previous_log.date_logged
            FROM user_logs previous_log
            WHERE previous_log.nfc_code = l.nfc_code
              AND previous_log.date_logged >= DATE(l.date_logged)
              AND previous_log.date_logged < DATE(l.date_logged) + INTERVAL 1 DAY
              AND (
                previous_log.date_logged < l.date_logged
                OR (previous_log.date_logged = l.date_logged AND previous_log.id < l.id)
              )
            ORDER BY previous_log.date_logged DESC, previous_log.id DESC
            LIMIT 1
        ), l.date_logged)
        ELSE NULL
    END AS duration_seconds,
    CASE
        WHEN (
            SELECT COUNT(*)
            FROM user_logs day_logs
            WHERE day_logs.nfc_code = l.nfc_code
              AND day_logs.date_logged >= DATE(l.date_logged)
              AND day_logs.date_logged < DATE(l.date_logged) + INTERVAL 1 DAY
              AND (
                day_logs.date_logged < l.date_logged
                OR (day_logs.date_logged = l.date_logged AND day_logs.id <= l.id)
              )
        ) % 2 = 0 THEN TIME_FORMAT(SEC_TO_TIME(TIMESTAMPDIFF(SECOND, (
            SELECT previous_log.date_logged
            FROM user_logs previous_log
            WHERE previous_log.nfc_code = l.nfc_code
              AND previous_log.date_logged >= DATE(l.date_logged)
              AND previous_log.date_logged < DATE(l.date_logged) + INTERVAL 1 DAY
              AND (
                previous_log.date_logged < l.date_logged
                OR (previous_log.date_logged = l.date_logged AND previous_log.id < l.id)
              )
            ORDER BY previous_log.date_logged DESC, previous_log.id DESC
            LIMIT 1
        ), l.date_logged)), '%H:%i:%s')
        ELSE NULL
    END AS duration_label
FROM user_logs l
LEFT JOIN users u ON u.nfc_code = l.nfc_code;
