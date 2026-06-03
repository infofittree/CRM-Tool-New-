-- Phase 2 CRM dashboard expansion.
-- For existing Phase 1 MySQL databases, run these ALTER statements once.

ALTER TABLE leads ADD COLUMN website VARCHAR(255) NULL;
ALTER TABLE leads ADD COLUMN industry VARCHAR(120) NULL;
ALTER TABLE leads ADD COLUMN city VARCHAR(120) NULL;
ALTER TABLE leads ADD COLUMN designation VARCHAR(120) NULL;
ALTER TABLE leads ADD COLUMN whatsapp_number VARCHAR(50) NULL;
ALTER TABLE leads ADD COLUMN product_interest VARCHAR(255) NULL;
ALTER TABLE leads ADD COLUMN moq_requirement VARCHAR(100) NULL;
ALTER TABLE leads ADD COLUMN expected_quantity VARCHAR(100) NULL;
ALTER TABLE leads ADD COLUMN budget_range VARCHAR(100) NULL;
ALTER TABLE leads ADD COLUMN priority_level VARCHAR(20) NOT NULL DEFAULT 'MEDIUM';
ALTER TABLE leads ADD COLUMN remarks TEXT NULL;
ALTER TABLE leads ADD COLUMN internal_notes TEXT NULL;
ALTER TABLE leads ADD INDEX ix_leads_priority (priority_level);

CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    role VARCHAR(30) NOT NULL DEFAULT 'Salesperson',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,
    UNIQUE KEY uq_users_username (username),
    KEY ix_users_role (role),
    KEY ix_users_deleted_at (deleted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS app_settings (
    setting_key VARCHAR(100) PRIMARY KEY,
    setting_value TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS lead_sequences (
    year INT PRIMARY KEY,
    last_number INT NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

