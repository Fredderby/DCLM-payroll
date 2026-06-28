from celery import Celery
from app.core.config import settings
from app.services.email_service import send_email
from app.services.pdf_service import generate_payslip_pdf
from app.core.database import SessionLocal
import os

celery_app = Celery("payroll", broker=settings.redis_url)

@celery_app.task
def send_payslip_email_task(employee_email: str, employee_name: str, payroll_id: int, net_salary: float):
    """Background task to generate PDF and send payslip email."""
    db = SessionLocal()
    try:
        from app.models.payroll import PayrollRecord
        payroll = db.query(PayrollRecord).filter(PayrollRecord.id == payroll_id).first()
        if not payroll:
            return {"success": False, "error": "Payroll record not found"}

        pdf_path = payroll.pdf_generated
        if not pdf_path or not os.path.exists(pdf_path):
            pdf_path = generate_payslip_pdf(db, payroll_id)
            if pdf_path:
                payroll.pdf_generated = pdf_path
                db.commit()

        if not pdf_path or not os.path.exists(pdf_path):
            return {"success": False, "error": "Failed to generate PDF"}

        import asyncio
        asyncio.run(send_email(employee_email, "Your Payslip", f"Net Salary: {net_salary}"))
        return {"success": True}
    finally:
        db.close()