from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def generate_payslip(employee_name: str, net_salary: float, file_path: str):
    c = canvas.Canvas(file_path, pagesize=letter)
    c.drawString(100, 750, f"Payslip for {employee_name}")
    c.drawString(100, 730, f"Net Salary: ${net_salary}")
    c.save()