from celery import Celery
from app.core.config import settings
from app.services.email_service import send_email
from app.utils.pdf_generator import generate_payslip
import os

celery_app = Celery("payroll", broker=settings.redis_url)

@celery_app.task
def send_payslip_email(employee_email: str, employee_name: str, net_salary: float):
    # Generate PDF
    pdf_path = f"/tmp/{employee_name}_payslip.pdf"
    generate_payslip(employee_name, net_salary, pdf_path)
    # Send email (simplified, attach PDF)
    # For now, just send text
    import asyncio
    asyncio.run(send_email(employee_email, "Your Payslip", f"Net Salary: {net_salary}"))