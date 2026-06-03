CREATE DATABASE IF NOT EXISTS sales_lead_crm
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE sales_lead_crm;

CREATE TABLE IF NOT EXISTS leads (
    lead_id VARCHAR(32) PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    website VARCHAR(255),
    industry VARCHAR(120),
    city VARCHAR(120),
    contact_person VARCHAR(255),
    designation VARCHAR(120),
    phone VARCHAR(50),
    whatsapp_number VARCHAR(50),
    email VARCHAR(255),
    country VARCHAR(100),
    status VARCHAR(50) NOT NULL DEFAULT 'NEW',
    assigned_to VARCHAR(100),
    lead_source VARCHAR(100),
    product_interest VARCHAR(255),
    moq_requirement VARCHAR(100),
    expected_quantity VARCHAR(100),
    budget_range VARCHAR(100),
    priority_level VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
    remarks TEXT,
    internal_notes TEXT,
    created_date DATE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,
    lead_score FLOAT NOT NULL DEFAULT 0,
    last_contact_date DATE,
    UNIQUE KEY uq_leads_email (email),
    KEY ix_leads_company_name (company_name),
    KEY ix_leads_status_assigned (status, assigned_to),
    KEY ix_leads_priority (priority_level),
    KEY ix_leads_email (email),
    KEY ix_leads_phone (phone),
    KEY ix_leads_deleted_at (deleted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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

CREATE TABLE IF NOT EXISTS followups (
    followup_id INT AUTO_INCREMENT PRIMARY KEY,
    lead_id VARCHAR(32) NOT NULL,
    followup_date DATE,
    discussion TEXT,
    next_action VARCHAR(255),
    next_followup DATE,
    updated_by VARCHAR(100),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY ix_followups_lead_date (lead_id, followup_date),
    KEY ix_followups_next_followup (next_followup),
    CONSTRAINT fk_followups_lead FOREIGN KEY (lead_id) REFERENCES leads (lead_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS activity_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    action VARCHAR(100) NOT NULL,
    user_name VARCHAR(100),
    lead_id VARCHAR(32),
    remarks TEXT,
    KEY ix_activity_logs_lead_timestamp (lead_id, timestamp),
    CONSTRAINT fk_activity_logs_lead FOREIGN KEY (lead_id) REFERENCES leads (lead_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS duplicate_reports (
    duplicate_id INT AUTO_INCREMENT PRIMARY KEY,
    lead_1 VARCHAR(32) NOT NULL,
    lead_2 VARCHAR(32) NOT NULL,
    similarity_score FLOAT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_duplicate_pair (lead_1, lead_2),
    KEY ix_duplicate_reports_status (status),
    CONSTRAINT fk_duplicate_reports_lead_1 FOREIGN KEY (lead_1) REFERENCES leads (lead_id),
    CONSTRAINT fk_duplicate_reports_lead_2 FOREIGN KEY (lead_2) REFERENCES leads (lead_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
