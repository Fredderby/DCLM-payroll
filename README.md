# DCLM Payroll Management System

A FastAPI-based payroll processing system for DCLM (Deeper Christian Life Ministry). Handles Excel payroll uploads, PDF payslip generation, and email distribution.
## Features

- **JWT Authentication** — Secure login with role-based access
- **Excel Upload & Processing** — Upload monthly payroll data via Excel files
- **Staff Management** — CRUD operations for employee records
- **Payslip Generation** — Automatic PDF payslip generation per employee
- **Email Distribution** — Send payslips via email with SMTP integration
- **Loan Management** — Track and manage employee loans
- **Dashboard & Reports** — Analytics dashboard with payroll summaries
- **Background Tasks** — Celery workers for async email/PDF processing

## Technology Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy, Jinja2
- **Frontend:** Bootstrap 5, React (navigation component), Font Awesome
- **Database:** MySQL (via pymysql)
- **Queue:** Redis + Celery for background tasks
- **Container:** Docker, Docker Compose

## Quick Start (Development)
