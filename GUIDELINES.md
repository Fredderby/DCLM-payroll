# GUIDELINES.md

## 📌 Project Overview

This project is a **Payroll Processing System** that:

* Accepts payroll data via **Excel upload**
* Validates and processes employee salary records
* Generates **payslips (PDF)**
* Sends payslips via **email**

The system must be **secure, robust, scalable, and fault-tolerant**.

---

## 🧱 Core Architecture

### Backend Framework

* Use **FastAPI**
* Follow modular structure:

```
app/
  ├── api/
  ├── core/
  ├── models/
  ├── schemas/
  ├── services/
  ├── utils/
  ├── workers/
```

---

## 🔐 Authentication & Authorization

### Authentication Method

* Use **JWT (JSON Web Tokens)**

### Flow

1. User logs in with email + password
2. Server returns:

   * `access_token` (short-lived)
   * `refresh_token` (long-lived)

---

### User Roles

#### Admin

* Full system access
* Manage users
* Upload payroll
* Send emails

#### HR

* Upload Excel
* Generate payslips
* Send emails

#### Employee (Future Scope)

* View/download own payslip only (sample can be found under payslips folder "Frederick_Osei-Kuffour_2025-10.pdf)

---

### Auth Endpoints

```
POST   /auth/register
POST   /auth/login
POST   /auth/refresh
POST   /auth/logout
GET    /auth/me
```

---

### Security Rules

* Hash passwords using **bcrypt**
* Access token expiry: **15–30 minutes**
* Refresh token expiry: **7–30 days**
* Store secrets in `.env`
* Protect all sensitive routes with authentication

---

### Route Protection Example

```python
@router.post("/upload")
def upload_file(current_user: User = Depends(get_current_active_user)):
    ...
```

---

## 📊 Excel Processing

### Input Requirements

* Only `.xlsx` files allowed
* Required columns:

  * Employee Name
  * Email
  * Basic Salary
  * Allowances
  * Deductions

---

### Validation

* Reject:

  * Missing columns
  * Invalid data types
  * Duplicate entries
* Use **Pydantic schemas**

---

### Processing

* Use **pandas**
* Normalize column names
* Handle large files efficiently (chunking if needed)

---

## 💰 Payroll Engine

### Calculations

* Gross Salary = Basic + Allowances
* Net Salary = Gross − Deductions

### Design

* Keep logic in:

```
services/payroll_service.py
```

### Extensibility

* Tax rules
* Custom deductions
* Bonuses

---

## 🧾 Payslip Generation

### Format

* PDF (primary)
* Image (optional)

### Content

* Company logo/name
* Employee details
* Salary breakdown
* Payment date

### Tools

* PDF: `reportlab` or `weasyprint`
* Image: `Pillow`

---

## 📧 Email Service

### Features

* Bulk sending
* Retry failed emails
* Delivery tracking

### Implementation

* SMTP or Email APIs

### Rules

* NEVER send emails synchronously
* Always queue email jobs

---

## ⚙️ Background Processing

### Required Tools

* **Celery + Redis** (recommended)
* OR FastAPI BackgroundTasks (small scale only)
* React, Tailwind CSS

### Tasks

* Excel processing
* Payslip generation
* Email sending

---

## 🗄️ Database Design

### Recommended

* MySQL

---

### Tables

#### Users

* id
* email
* hashed_password
* role
* is_active
* created_at

#### Employees

* id
* name
* email

#### Payroll Records

* id
* employee_name
* basic_salary
* allowances
* deductions
* net_salary
* created_at

#### Upload History

* id
* file_name
* uploaded_by
* status
* timestamp

#### Email Logs

* id
* employee_name
* status
* sent_at

---

## 🛡️ Security

* Validate all uploads
* Limit file size
* Sanitize Excel input
* Enforce role-based access
* Do NOT log sensitive salary data

---

## 🚀 Performance

* Use async endpoints
* Avoid blocking operations
* Batch processing
* Queue heavy tasks

---

## 🧪 Testing

### Unit Tests

* Payroll calculations
* Excel validation

### Integration Tests

* Upload → Process → Email flow

---

## 📁 File Storage

* Temporary upload storage
* Payslips:

  * MySQL (Read from .env)
  * Cloud storage (production)

---

## 📈 Logging & Monitoring

* Log:

  * Upload activity
  * Processing errors
  * Email delivery status
* Use structured logging (JSON)

---

## ❗ Error Handling

* Fail per-record, not entire batch
* Provide clear error messages
* Retry failed jobs

---

## 🧠 Development Principles

* Separation of concerns
* Dependency injection
* Reusable services
* No business logic in routes

---

## 🔄 Future Enhancements

* Employee self-service portal
* Multi-company support
* Scheduled payroll runs
* Audit logs

---

## 🚫 Anti-Patterns

* Blocking FastAPI routes
* Hardcoding logic
* Skipping validation
* Sending emails synchronously

---

## ✅ Definition of Done

A feature is complete only if:

* Input validation implemented
* Auth + authorization enforced
* Errors handled properly
* Logging added
* Tests written
* No sensitive data exposure

---
