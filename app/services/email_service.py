"""
Email Service for sending payslips and notifications
Uses environment variables:
  SMTP_SERVER=smtp.gmail.com
  SMTP_PORT=587
  SMTP_USERNAME=dclmghpayslip@gmail.com
  SMTP_PASSWORD=rzdevbvlnejadkbl
"""
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
from app.core.config import settings

# Default SMTP fallback values (Settings from .env takes priority)
DEFAULT_SMTP_SERVER = "smtp.gmail.com"
DEFAULT_SMTP_PORT = 587
FROM_NAME = "DCLM Payroll System"


class EmailService:
    """Service to handle email sending for payslips and notifications"""

    @staticmethod
    def _get_smtp_settings():
        """Get SMTP settings from Settings object (reads .env), with env var fallback."""
        # Priority: Settings object (from .env) > environment variable > hardcoded default
        server = getattr(settings, "smtp_server", None) or os.getenv("SMTP_SERVER") or DEFAULT_SMTP_SERVER
        port = int(getattr(settings, "smtp_port", None) or os.getenv("SMTP_PORT") or DEFAULT_SMTP_PORT)
        username = getattr(settings, "smtp_username", None) or os.getenv("SMTP_USERNAME") or ""
        password = getattr(settings, "smtp_password", None) or os.getenv("SMTP_PASSWORD") or ""
        return server, port, username, password

    @staticmethod
    async def send_payslip(recipient_email: str, employee_name: str, month: str, pdf_path: str, net_salary: float):
        """Send payslip via email to employee"""
        try:
            server, port, username, password = EmailService._get_smtp_settings()
            if not username or not password:
                return False, "SMTP not configured. Set SMTP_USERNAME and SMTP_PASSWORD env vars."

            message = MIMEMultipart()
            message["From"] = f"{FROM_NAME} <{username}>"
            message["To"] = recipient_email
            message["Subject"] = f"Payslip - {month}"

            body = f"""Dear {employee_name},

Your payslip for {month} is attached. Please review the details carefully.

Net Salary: GHS {net_salary:,.2f}

If you have any questions, please contact the Human Resources department.

Best regards,
DCLM Payroll Management System"""

            message.attach(MIMEText(body, "plain"))

            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, "rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(pdf_path)}")
                message.attach(part)

            if port == 465:
                async with aiosmtplib.SMTP(hostname=server, port=port, use_tls=True) as smtp:
                    await smtp.login(username, password)
                    await smtp.send_message(message)
            else:
                async with aiosmtplib.SMTP(hostname=server, port=port) as smtp:
                    await smtp.starttls()
                    await smtp.login(username, password)
                    await smtp.send_message(message)

            return True, "Email sent successfully"
        except Exception as e:
            return False, str(e)

    @staticmethod
    async def send_bulk_payslips(payroll_records, db_session):
        """Send payslips to all employees for a specific month"""
        from app.models.email_log import EmailLog
        from app.models.employee import Employee
        from datetime import datetime

        results = {"successful": 0, "failed": 0, "errors": []}

        for payroll in payroll_records:
            emp = db_session.query(Employee).filter(Employee.name == payroll.employee_name).first()
            employee_name = emp.name if emp and emp.name else (payroll.employee_name or "Unknown")
            if not emp or not emp.email:
                results["failed"] += 1
                results["errors"].append(f"Payroll {payroll.id} ({employee_name}): No employee email found")
                continue

            # Ensure PDF exists
            if not payroll.pdf_generated or not os.path.exists(payroll.pdf_generated):
                from app.services.pdf_service import generate_payslip_pdf
                pdf_path = generate_payslip_pdf(db_session, payroll.id)
                if pdf_path:
                    payroll.pdf_generated = pdf_path
                    db_session.commit()

            success, message = await EmailService.send_payslip(
                recipient_email=emp.email,
                employee_name=employee_name,
                month=payroll.month or "N/A",
                pdf_path=payroll.pdf_generated,
                net_salary=payroll.net_salary or 0
            )

            # Log the email attempt
            try:
                log = EmailLog(
                    employee_id=emp.id,
                    employee_name=employee_name,
                    payroll_id=payroll.id,
                    recipient_email=emp.email,
                    status="sent" if success else "failed",
                    month=payroll.month
                )
                db_session.add(log)
                db_session.commit()
            except Exception:
                db_session.rollback()

            if success:
                results["successful"] += 1
            else:
                results["failed"] += 1
                results["errors"].append(f"{employee_name}: {message}")

        return results

    @staticmethod
    async def send_test_email(recipient_email: str = None):
        """Send a test email to verify SMTP configuration"""
        try:
            server, port, username, password = EmailService._get_smtp_settings()
            if not username or not password:
                return False, "SMTP not configured. Set SMTP_USERNAME and SMTP_PASSWORD env vars."

            test_to = recipient_email or username
            message = MIMEText("This is a test email from DCLM Payroll System.\n\nIf you receive this, your SMTP configuration is working correctly!")
            message["From"] = f"{FROM_NAME} <{username}>"
            message["To"] = test_to
            message["Subject"] = "Test - DCLM Payroll SMTP Configuration"

            if port == 465:
                async with aiosmtplib.SMTP(hostname=server, port=port, use_tls=True) as smtp:
                    await smtp.login(username, password)
                    await smtp.send_message(message)
            else:
                async with aiosmtplib.SMTP(hostname=server, port=port) as smtp:
                    await smtp.starttls()
                    await smtp.login(username, password)
                    await smtp.send_message(message)

            return True, "Test email sent successfully!"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def is_configured():
        """Check if SMTP is configured"""
        _, _, username, password = EmailService._get_smtp_settings()
        return bool(username and password)

    @staticmethod
    async def send_notification(recipient_email: str, subject: str, body: str):
        try:
            server, port, username, password = EmailService._get_smtp_settings()
            message = MIMEText(body)
            message["From"] = f"{FROM_NAME} <{username}>"
            message["To"] = recipient_email
            message["Subject"] = subject

            if port == 465:
                async with aiosmtplib.SMTP(hostname=server, port=port, use_tls=True) as smtp:
                    await smtp.login(username, password)
                    await smtp.send_message(message)
            else:
                async with aiosmtplib.SMTP(hostname=server, port=port) as smtp:
                    await smtp.starttls()
                    await smtp.login(username, password)
                    await smtp.send_message(message)

            return True, "Notification sent"
        except Exception as e:
            return False, str(e)

    @staticmethod
    async def send_email(to_email: str, subject: str, body: str):
        """Legacy function for backwards compatibility"""
        return await EmailService.send_notification(to_email, subject, body)


async def send_email(to_email: str, subject: str, body: str):
    """Legacy function for backwards compatibility"""
    return await EmailService.send_notification(to_email, subject, body)


async def send_payslip_email(recipient_email: str, employee_name: str, pdf_path: str, month: str):
    """Send a single payslip via email. Top-level function for route handlers to import."""
    try:
        from app.models.payroll import PayrollRecord
        net_salary = 0
        if pdf_path and os.path.exists(pdf_path):
            success, message = await EmailService.send_payslip(
                recipient_email=recipient_email,
                employee_name=employee_name,
                month=month or "",
                pdf_path=pdf_path,
                net_salary=net_salary
            )
        else:
            print(f"PDF not found for {recipient_email}: {pdf_path}")
            return False
        return success
    except Exception as e:
        print(f"send_payslip_email error for {recipient_email}: {e}")
        return False