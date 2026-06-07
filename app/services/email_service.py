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

            # Format payroll month to "Month YYYY" if needed
            display_month = month
            month_names = ["", "January", "February", "March", "April", "May", "June",
                          "July", "August", "September", "October", "November", "December"]
            if month and "-" in month:
                parts = month.split("-")
                if len(parts) == 2:
                    p0, p1 = parts[0].strip(), parts[1].strip()
                    if p0.isdigit() and len(p0) == 4:
                        mn = int(p1.zfill(2))
                        display_month = f"{month_names[mn] if 1 <= mn <= 12 else p1} {p0}"
                    else:
                        mn = int(p0.zfill(2))
                        display_month = f"{month_names[mn] if 1 <= mn <= 12 else p0} {p1}"

            body = f"""Dear {employee_name},

Your payslip for {display_month} is attached. Please review the details carefully.

Net Salary: GHS {net_salary:,.2f}

If you have any questions, please contact the Head of Finance.

Best regards,
Head of Finance"""

            message.attach(MIMEText(body, "plain"))

            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, "rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(pdf_path)}")
                message.attach(part)

            # IMPORTANT: aiosmtplib.SMTP() auto-connects and handles STARTTLS automatically.
            # Do NOT call starttls() manually - it causes "Connection already using TLS" error.
            if port == 465:
                # SSL/TLS implicit mode
                async with aiosmtplib.SMTP(hostname=server, port=port, use_tls=True, timeout=30) as smtp:
                    await smtp.login(username, password)
                    await smtp.send_message(message)
            else:
                # STARTTLS mode (port 587): aiosmtplib auto-handles TLS
                async with aiosmtplib.SMTP(hostname=server, port=port, timeout=30) as smtp:
                    await smtp.login(username, password)
                    await smtp.send_message(message)

            return True, "Email sent successfully"
        except Exception as e:
            import traceback
            error_msg = f"{type(e).__name__}: {e}"
            logger.error(f"SMTP send failed: {error_msg}", exc_info=True)
            traceback.print_exc()
            return False, error_msg

    @staticmethod
    async def send_bulk_payslips(payroll_records, db_session):
        """Send payslips to all employees for a specific month"""
        from app.models.email_log import EmailLog
        from app.models.employee import Employee
        from app.models.employee_alias import EmployeeAlias
        from datetime import datetime

        results = {"successful": 0, "failed": 0, "errors": []}

        for payroll in payroll_records:
            emp = db_session.query(Employee).filter(Employee.name == payroll.employee_name).first()
            if not emp:
                # Try alias lookup
                rec_name = (payroll.employee_name or '').strip()
                rec_name_norm = ' '.join(rec_name.split()).upper()
                alias = db_session.query(EmployeeAlias).filter(EmployeeAlias.alias_name == rec_name).first()
                if not alias:
                    all_aliases = db_session.query(EmployeeAlias).all()
                    for a in all_aliases:
                        alias_norm = ' '.join((a.alias_name or '').split()).upper()
                        if alias_norm == rec_name_norm:
                            alias = a
                            break
                if alias:
                    emp = db_session.query(Employee).filter(Employee.id == alias.employee_id).first()
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
            import traceback
            logger.error(f"SMTP send failed: {e}", exc_info=True)
            traceback.print_exc()
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
            import traceback
            logger.error(f"SMTP send failed: {e}", exc_info=True)
            traceback.print_exc()
            return False, str(e)

    @staticmethod
    async def send_email(to_email: str, subject: str, body: str):
        """Legacy function for backwards compatibility"""
        return await EmailService.send_notification(to_email, subject, body)

async def send_single_and_log(employee_id: int, employee_name: str, employee_number: str,
                               recipient_email: str, payroll_id: int, month: str,
                               net_salary: float, pdf_path: str, db_session):
    """Send a single payslip email and log the result to EmailLog table."""
    from app.models.email_log import EmailLog
    try:
        success, message = await EmailService.send_payslip(
            recipient_email=recipient_email,
            employee_name=employee_name,
            month=month or "",
            pdf_path=pdf_path,
            net_salary=net_salary
        )
        
        log = EmailLog(
            employee_id=employee_id,
            employee_name=employee_name,
            employee_number=employee_number or "",
            payroll_id=payroll_id,
            recipient_email=recipient_email,
            status="sent" if success else "failed",
            month=month,
            net_salary=net_salary,
            error_message=None if success else message,
            sent_at=datetime.utcnow()
        )
        db_session.add(log)
        db_session.commit()
        return success, message
    except Exception as e:
        print(f"send_single_and_log error: {e}")
        import traceback
        traceback.print_exc()
        return False, str(e)




async def send_email(to_email: str, subject: str, body: str):
    """Legacy function for backwards compatibility"""
    return await EmailService.send_notification(to_email, subject, body)


async def send_payslip_email(recipient_email: str, employee_name: str, pdf_path: str, month: str, net_salary: float = None):
    """Send a single payslip via email. Returns (success: bool, error_msg: str) tuple."""
    try:
        import traceback as _tb
        if net_salary is None:
            # Try to get net_salary from payroll records
            try:
                from app.models.payroll import PayrollRecord
                from app.core.database import SessionLocal
                db = SessionLocal()
                try:
                    payroll_entry = db.query(PayrollRecord).filter(
                        PayrollRecord.employee_name == employee_name,
                        PayrollRecord.month == month
                    ).order_by(PayrollRecord.id.desc()).first()
                    if payroll_entry:
                        net_salary = payroll_entry.net_salary
                    else:
                        net_salary = 0
                finally:
                    db.close()
            except Exception as e:
                print(f"Could not look up net_salary for {employee_name}: {e}")
                net_salary = 0
        if pdf_path and os.path.exists(pdf_path):
            success, smtp_msg = await EmailService.send_payslip(
                recipient_email=recipient_email,
                employee_name=employee_name,
                month=month or "",
                pdf_path=pdf_path,
                net_salary=net_salary
            )
            if not success:
                log_msg = f"EMAIL FAILED for {recipient_email}: {smtp_msg}"
                print(log_msg)
            return success, smtp_msg
        else:
            error_msg = f"PDF not found: {pdf_path}"
            print(f"EMAIL FAILED for {recipient_email}: {error_msg}")
            return False, error_msg
    except Exception as e:
        error_msg = f"Exception: {type(e).__name__}: {e}"
        print(f"EMAIL EXCEPTION for {recipient_email}: {error_msg}")
        _tb.print_exc()
        return False, error_msg