-- ============================================================
-- DCLM Payroll - Performance Optimization Indexes
-- Run once after migration to improve query performance
-- ============================================================

-- Payroll Records Indexes
CREATE INDEX IF NOT EXISTS idx_payroll_month ON payroll_records(month);
CREATE INDEX IF NOT EXISTS idx_payroll_employee_name ON payroll_records(employee_name);
CREATE INDEX IF NOT EXISTS idx_payroll_month_employee ON payroll_records(month, employee_name);
CREATE INDEX IF NOT EXISTS idx_payroll_created_at ON payroll_records(created_at);

-- Employees Indexes
CREATE INDEX IF NOT EXISTS idx_employee_name ON employees(name);
CREATE INDEX IF NOT EXISTS idx_employee_email ON employees(email);
CREATE INDEX IF NOT EXISTS idx_employee_number ON employees(employee_number);

-- Loans Indexes
CREATE INDEX IF NOT EXISTS idx_loan_employee_id ON loans(employee_id);
CREATE INDEX IF NOT EXISTS idx_loan_month ON loans(month);
CREATE INDEX IF NOT EXISTS idx_loan_status ON loans(status);

-- Upload History Indexes
CREATE INDEX IF NOT EXISTS idx_upload_month ON upload_history(month);
CREATE INDEX IF NOT EXISTS idx_upload_uploaded_by ON upload_history(uploaded_by);
CREATE INDEX IF NOT EXISTS idx_upload_created_at ON upload_history(created_at);

-- Email Log Indexes
CREATE INDEX IF NOT EXISTS idx_email_sent_at ON email_log(sent_at);
CREATE INDEX IF NOT EXISTS idx_email_employee ON email_log(employee_email);

-- Users Indexes
CREATE INDEX IF NOT EXISTS idx_user_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_user_email ON users(email);

-- ============================================================
-- Schema Migration: Add new columns for staff_category and non-pastoral fields
-- Run after code deployment
-- ============================================================

ALTER TABLE payroll_records
  ADD COLUMN IF NOT EXISTS staff_category VARCHAR(20) DEFAULT 'pastoral';

ALTER TABLE payroll_records
  ADD COLUMN IF NOT EXISTS rent_monthly FLOAT DEFAULT 0;

ALTER TABLE payroll_records
  ADD COLUMN IF NOT EXISTS utility_monthly FLOAT DEFAULT 0;

ALTER TABLE payroll_records
  ADD COLUMN IF NOT EXISTS transport_monthly FLOAT DEFAULT 0;

ALTER TABLE payroll_records
  ADD COLUMN IF NOT EXISTS employee_pf FLOAT DEFAULT 0;

ALTER TABLE payroll_records
  ADD COLUMN IF NOT EXISTS ssnit_deduction FLOAT DEFAULT 0;
