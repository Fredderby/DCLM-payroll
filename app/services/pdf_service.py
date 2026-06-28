from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from sqlalchemy.orm import Session
from app.models.payroll import PayrollRecord
from app.models.employee import Employee
from app.models.loan import Loan
from app.services.payroll_service import number_to_words, amount_to_words
import os
import tempfile
import shutil
import time
import threading
from datetime import datetime, timedelta

# ── Temporary PDF Storage Configuration ──
# PDF files are stored in a temp directory and auto-purged after this many hours
PDF_TEMP_LIFETIME_HOURS = 24

_pdf_temp_dir = None
_cleanup_timer = None
_cleanup_lock = threading.Lock()


def get_pdf_temp_dir() -> str:
    """Get or create the temporary directory for PDF storage."""
    global _pdf_temp_dir
    if _pdf_temp_dir is None:
        _pdf_temp_dir = tempfile.mkdtemp(prefix="payslips_")
        # Schedule cleanup
        schedule_cleanup()
    return _pdf_temp_dir


def schedule_cleanup():
    """Schedule cleanup of old PDF files."""
    global _cleanup_timer
    with _cleanup_lock:
        if _cleanup_timer is None:
            _cleanup_timer = threading.Timer(PDF_TEMP_LIFETIME_HOURS * 3600, cleanup_old_pdfs)
            _cleanup_timer.daemon = True
            _cleanup_timer.start()


def cleanup_old_pdfs():
    """Remove PDF files older than the configured lifetime."""
    global _cleanup_timer, _pdf_temp_dir
    try:
        if _pdf_temp_dir and os.path.exists(_pdf_temp_dir):
            now = time.time()
            cutoff = now - (PDF_TEMP_LIFETIME_HOURS * 3600)
            for fname in os.listdir(_pdf_temp_dir):
                fpath = os.path.join(_pdf_temp_dir, fname)
                if fname.endswith('.pdf') and os.path.isfile(fpath):
                    file_time = os.path.getmtime(fpath)
                    if file_time < cutoff:
                        try:
                            os.remove(fpath)
                        except OSError:
                            pass
    except Exception:
        pass
    finally:
        # Reschedule
        with _cleanup_lock:
            _cleanup_timer = None
        schedule_cleanup()


def get_pdf_output_dir(use_temp: bool = True) -> str:
    """Get the output directory for generated PDFs.
    
    When use_temp is True (default), files are stored in a temporary directory
    and automatically cleaned up after PDF_TEMP_LIFETIME_HOURS.
    """
    if use_temp:
        return get_pdf_temp_dir()
    return "payslips"


def parse_bank_account(val: str):
    """Parse '601120033368, GCB, KUMASI MAIN' into (account_number, bank_name, bank_branch)"""
    parts = [p.strip() for p in (val or "").split(",")]
    return (parts[0] if len(parts) > 0 else "",
            parts[1] if len(parts) > 1 else "",
            parts[2] if len(parts) > 2 else "")


MONTH_NAMES = {
    "01": "January", "02": "February", "03": "March", "04": "April",
    "05": "May", "06": "June", "07": "July", "08": "August",
    "09": "September", "10": "October", "11": "November", "12": "December"
}


def _format_month(raw: str | None) -> str:
    """Convert YYYY-MM or any format to 'October-2025' style"""
    if not raw:
        return "N/A"
    raw = raw.strip()
    if len(raw) == 7 and raw[4] == '-':
        parts = raw.split('-')
        month_name = MONTH_NAMES.get(parts[1], parts[1])
        return f"{month_name}-{parts[0]}"
    if raw.startswith("20") and len(raw) >= 7:
        for sep in ['-', '/', ' ']:
            if sep in raw:
                p = raw.split(sep)
                if len(p) >= 2:
                    m = p[1].zfill(2) if len(p[1]) <= 2 else p[1]
                    mn = MONTH_NAMES.get(m, m)
                    y = p[0] if len(p[0]) == 4 else (p[2] if len(p) > 2 else "20??")
                    return f"{mn}-{y}"
    for sep in [' ', '-', '/']:
        if sep in raw:
            p = raw.rsplit(sep, 1)
            if len(p) == 2 and p[1].isdigit() and len(p[1]) == 4:
                return f"{p[0].capitalize()}-{p[1]}"
    return raw


class WatermarkedDocTemplate(SimpleDocTemplate):
    """Custom doc template that draws the DCLM logo as translucent watermark"""

    def __init__(self, *args, **kwargs):
        self.logo_path = kwargs.pop('logo_path', None)
        super().__init__(*args, **kwargs)

    def afterPage(self):
        """Draw watermark on every page"""
        if self.logo_path and os.path.exists(self.logo_path):
            try:
                c = self.canv
                pw, ph = self.pagesize
                c.saveState()
                c.setFillAlpha(0.08)
                c.drawImage(self.logo_path,
                            pw * 0.15, ph * 0.15,
                            width=pw * 0.7, height=ph * 0.7,
                            mask='auto', preserveAspectRatio=True)
                c.restoreState()
            except Exception:
                pass


def generate_payslip_pdf(db: Session, payroll_id: int,
                         output_dir: str = None):
    """Generate payslip PDF that matches the HTML preview exactly.
    
    If output_dir is None, a temporary directory is used and files are 
    automatically cleaned up after PDF_TEMP_LIFETIME_HOURS.
    """
    if output_dir is None:
        output_dir = get_pdf_output_dir(use_temp=True)
    
    os.makedirs(output_dir, exist_ok=True)

    payroll = db.query(PayrollRecord).filter(PayrollRecord.id == payroll_id).first()
    if not payroll:
        return None

    employee = db.query(Employee).filter(Employee.name == payroll.employee_name).first()
    if not employee:
        # Try alias lookup
        rec_name = (payroll.employee_name or '').strip()
        rec_name_norm = ' '.join(rec_name.split()).upper()
        from app.models.employee_alias import EmployeeAlias
        alias = db.query(EmployeeAlias).filter(EmployeeAlias.alias_name == rec_name).first()
        if not alias:
            all_aliases = db.query(EmployeeAlias).all()
            for a in all_aliases:
                alias_norm = ' '.join((a.alias_name or '').split()).upper()
                if alias_norm == rec_name_norm:
                    alias = a
                    break
        if alias:
            employee = db.query(Employee).filter(Employee.id == alias.employee_id).first()
    if not employee:
        # Fuzzy fallback for name variations
        from app.main import fuzzy_score
        all_emps = db.query(Employee).all()
        best_emp, best_score = None, 0
        for e in all_emps:
            s = fuzzy_score(rec_name, e.name or '')
            if s > best_score:
                best_score = s
                best_emp = e
        if best_emp and best_score >= 50:
            employee = best_emp
    if not employee:
        class PlaceholderEmployee:
            def __init__(self, name):
                self.name = name
                self.employee_number = ""
                self.function = ""
                self.designation = ""
                self.location = ""
                self.date_joined = None
                self.ssnit_number = ""
                self.bank_number = ""
                self.bank_name = ""
                self.bank_branch = ""
                self.email = ""
        employee = PlaceholderEmployee(payroll.employee_name)

    # Recalculate totals from individual fields so PF 8% is always included
    from app.services.payroll_service import calculate_payroll_totals
    pdf_earnings_dict = {
        'basic_salary': payroll.basic_salary,
        'meals_monthly': payroll.meals_monthly,
        'responsibility_allowance': payroll.responsibility_allowance,
        'cola': payroll.cola,
        'leave_allowance': payroll.leave_allowance,
        'other_earnings': payroll.other_earnings,
        'rent_monthly': payroll.rent_monthly,
        'utility_monthly': payroll.utility_monthly,
        'transport_monthly': payroll.transport_monthly,
    }
    pdf_deductions_dict = {
        'paye': payroll.paye,
        'tithe': payroll.tithe,
        'future_savings': payroll.future_savings,
        'other_deductions': payroll.other_deductions,
        'ssnit_deduction': payroll.ssnit_deduction,
        'pf_eight_percent': payroll.pf_eight_percent,
    }
    pdf_computed_earnings, pdf_computed_deductions, pdf_computed_net = calculate_payroll_totals(pdf_earnings_dict, pdf_deductions_dict)

    month_display = _format_month(payroll.month)
    logo_path = os.path.join("static", "img", "logo.jpg") if os.path.exists(os.path.join("static", "img", "logo.jpg")) else os.path.join("static", "logo.jpg")

    safe_emp_name = (payroll.employee_name or "EMP").replace('/', '_').replace('\\', '_').replace(' ', '_')
    safe_month = (payroll.month or '').replace(' ', '_').replace('/', '_').replace('\\', '_')
    filename = f"{output_dir}/{safe_emp_name}_{safe_month}.pdf"
    
    # Remove existing file if present (fixes Permission denied on subsequent generates)
    if os.path.exists(filename):
        try:
            os.chmod(filename, 0o666)
            os.remove(filename)
        except (PermissionError, OSError):
            pass
    
    doc = WatermarkedDocTemplate(
        filename, pagesize=A4, logo_path=logo_path,
        topMargin=0.35*inch, bottomMargin=0.35*inch,
        leftMargin=0.5*inch, rightMargin=0.5*inch
    )

    elements = []
    styles = getSampleStyleSheet()

    # ── Colors (matching HTML preview) ──
    NAVY = colors.HexColor("#1a1a2e")
    DEEP_BLUE = colors.HexColor("#0f3460")
    LIGHT_BG = colors.HexColor("#f8fafc")
    BORDER = colors.HexColor("#e5e7eb")
    GREEN = colors.HexColor("#059669")
    GREEN_BG = colors.HexColor("#ecfdf5")
    GREEN_BORDER = colors.HexColor("#bbf7d0")
    GRAY_ALT = colors.HexColor("#f9fafb")
    TOTAL_BG = colors.HexColor("#f3f4f6")
    WHITE = colors.white
    DARK = colors.HexColor("#111827")
    GRAY_TXT = colors.HexColor("#6b7280")

    PW = 7.0 * inch

    # ═══════════ HEADER ═══════════
    nm = employee.name or "N/A"
    bank_info_hdr = "N/A"
    if employee.bank_name or employee.bank_number:
        bank_info_hdr = f"Bank: {employee.bank_name or ''} {employee.bank_branch or ''} | Acc: {employee.bank_number or 'N/A'}"

    org_s = ParagraphStyle('O', fontSize=11, fontName='Helvetica-Bold',
                           textColor=NAVY, alignment=TA_CENTER, leading=14)
    addr_s = ParagraphStyle('A', fontSize=7.5, fontName='Helvetica',
                            textColor=GRAY_TXT, alignment=TA_CENTER, leading=10)
    enh_s = ParagraphStyle('E', fontSize=10, fontName='Helvetica-Bold',
                           textColor=NAVY, alignment=TA_CENTER)
    bh_s = ParagraphStyle('B', fontSize=7, fontName='Helvetica',
                          textColor=GRAY_TXT, alignment=TA_CENTER, leading=10)
    pay_s = ParagraphStyle('P', fontSize=11, fontName='Helvetica-Bold',
                           textColor=DEEP_BLUE, alignment=TA_CENTER)
    mon_s = ParagraphStyle('M', fontSize=8.5, fontName='Helvetica-Bold',
                           textColor=DARK, alignment=TA_CENTER)

    hdr = Table([
        [Paragraph("DEEPER CHRISTIAN LIFE MINISTRY", org_s)],
        [Paragraph("P.O. BOX AN 16866, ACCRA-GHANA", addr_s)],
        [Paragraph(" ", ParagraphStyle('s1', fontSize=3))],
        [Paragraph(f"{nm}", enh_s)],
        [Paragraph(f"{bank_info_hdr}", bh_s)],
        [Paragraph(" ", ParagraphStyle('s2', fontSize=2))],
        [Paragraph("PAY SLIP", pay_s)],
        [Paragraph(f"for {month_display}", mon_s)],
    ], colWidths=[PW])
    hdr.setStyle(TableStyle([
        ('TOPPADDING', (0,0), (-1,-1), 1), ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ('LINEBELOW', (0,-1), (-1,-1), 2, DEEP_BLUE),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    elements.append(hdr)
    elements.append(Spacer(1, 0.08*inch))

    # ═══════════ EMPLOYEE INFO CARD (2-col grid with border) ═══════════
    info_s = ParagraphStyle('I', fontSize=7.5, fontName='Helvetica', textColor=DARK)
    pairs = [
        ("Bank Name:", employee.bank_name or "N/A"),
        ("Employee No.:", employee.employee_number or "N/A"),
        ("Function:", employee.function or "N/A"),
        ("Designation:", employee.designation or "N/A"),
        ("Location:", employee.location or "N/A"),
        ("Date Joined:", str(employee.date_joined or "N/A")),
        ("SSNIT No.:", employee.ssnit_number or "N/A"),
        ("Account No.:", employee.bank_number or "N/A"),
    ]
    info_rows = []
    for i in range(0, len(pairs), 2):
        l = pairs[i]
        r = pairs[i+1] if i+1 < len(pairs) else ("", "")
        info_rows.append([
            Paragraph(f"<b>{l[0]}</b>  {l[1]}", info_s),
            Paragraph(f"<b>{r[0]}</b>  {r[1]}", info_s),
        ])
    inner = Table(info_rows, colWidths=[PW*0.50, PW*0.50])
    inner.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'), ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 2), ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 4), ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    card = Table([[inner]], colWidths=[PW])
    card.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), LIGHT_BG),
        ('BOX', (0,0), (-1,-1), 0.5, BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 6), ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8), ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(card)
    elements.append(Spacer(1, 0.12*inch))

    # ═══════════ EARNINGS & DEDUCTIONS TABLE ═══════════
    tl = ParagraphStyle('tl', fontSize=7.5, fontName='Helvetica', textColor=DARK, alignment=TA_LEFT)
    tr = ParagraphStyle('tr', fontSize=7.5, fontName='Helvetica', textColor=DARK, alignment=TA_RIGHT)
    td = ParagraphStyle('td', fontSize=7.5, fontName='Helvetica', textColor=GRAY_TXT, alignment=TA_RIGHT)
    tbl = ParagraphStyle('tbl', fontSize=7.5, fontName='Helvetica-Bold', textColor=DARK, alignment=TA_LEFT)
    tbr = ParagraphStyle('tbr', fontSize=7.5, fontName='Helvetica-Bold', textColor=DARK, alignment=TA_RIGHT)
    th = ParagraphStyle('th', fontSize=7.5, fontName='Helvetica-Bold', textColor=WHITE, alignment=TA_LEFT)
    thr = ParagraphStyle('thr', fontSize=7.5, fontName='Helvetica-Bold', textColor=WHITE, alignment=TA_RIGHT)

    def v(val):
        if val is None: return Paragraph("—", td)
        return Paragraph(f"{float(val):,.2f}", tr)
    def vb(val):
        if val is None: return Paragraph("—", td)
        return Paragraph(f"{float(val):,.2f}", tbr)

    # Build payroll rows based on staff category
    staff_category = getattr(payroll, 'staff_category', 'pastoral') or 'pastoral'
    rows = [
        [Paragraph("Description", th), Paragraph("Amount (GHS)", thr), Paragraph("Deductions (GHS)", thr)],
    ]

    if staff_category.lower() == 'pastoral':
        # Pastoral earnings (all shown unconditionally to match preview)
        rows.append([Paragraph("Basic Salary", tl), v(payroll.basic_salary), v(None)])
        rows.append([Paragraph("Meals", tl), v(payroll.meals_monthly), v(None)])
        rows.append([Paragraph("Responsibility Allowance", tl), v(payroll.responsibility_allowance), v(None)])
        rows.append([Paragraph("COLA", tl), v(payroll.cola), v(None)])
        rows.append([Paragraph("Leave Allowance", tl), v(payroll.leave_allowance), v(None)])
        # Pastoral deductions (all shown unconditionally to match preview)
        rows.append([Paragraph("PAYE", tl), v(None), v(payroll.paye)])
        rows.append([Paragraph("10% Tithe", tl), v(None), v(payroll.tithe)])
        rows.append([Paragraph("Future Savings", tl), v(None), v(payroll.future_savings)])
        rows.append([Paragraph("PF 8%", tl), v(None), v(payroll.pf_eight_percent)])
        rows.append([Paragraph("SSNIT 5.5%", tl), v(None), v(payroll.ssnit_deduction)])
    else:
        # Non-Pastoral earnings (all shown unconditionally to match preview)
        rows.append([Paragraph("Monthly Basic Salary", tl), v(payroll.basic_salary), v(None)])
        rows.append([Paragraph("Meals Monthly", tl), v(payroll.meals_monthly), v(None)])
        if float(payroll.rent_monthly or 0) > 0:
            rows.append([Paragraph("Rent Monthly", tl), v(payroll.rent_monthly), v(None)])
        if float(payroll.utility_monthly or 0) > 0:
            rows.append([Paragraph("Utility Monthly", tl), v(payroll.utility_monthly), v(None)])
        if float(payroll.transport_monthly or 0) > 0:
            rows.append([Paragraph("Transport Monthly", tl), v(payroll.transport_monthly), v(None)])
        rows.append([Paragraph("COLA", tl), v(payroll.cola), v(None)])
        rows.append([Paragraph("Leave Allowance", tl), v(payroll.leave_allowance), v(None)])
        if float(payroll.other_earnings or 0) > 0:
            rows.append([Paragraph("Other Earnings", tl), v(payroll.other_earnings), v(None)])
        # Non-Pastoral deductions (all shown unconditionally to match preview)
        rows.append([Paragraph("PAYE", tl), v(None), v(payroll.paye)])
        rows.append([Paragraph("10% Tithe", tl), v(None), v(payroll.tithe)])
        rows.append([Paragraph("Future Savings", tl), v(None), v(payroll.future_savings)])
        rows.append([Paragraph("PF 8%", tl), v(None), v(payroll.pf_eight_percent)])
        rows.append([Paragraph("SSNIT 5.5%", tl), v(None), v(payroll.ssnit_deduction)])
        if float(payroll.other_deductions or 0) > 0:
            rows.append([Paragraph("Other Deductions", tl), v(None), v(payroll.other_deductions)])

    rows.append([Paragraph("TOTAL", tbl), vb(pdf_computed_earnings), vb(pdf_computed_deductions)])

    cw = [PW*0.40, PW*0.30, PW*0.30]
    mt = Table(rows, colWidths=cw)
    mt.setStyle(TableStyle([
        ('FONTSIZE', (0,0), (-1,-1), 7.5),
        ('BACKGROUND', (0,0), (-1,0), DEEP_BLUE), ('TEXTCOLOR', (0,0), (-1,0), WHITE),
        ('LINEBELOW', (0,1), (-1,-2), 0.4, BORDER),
        ('BACKGROUND', (0,-1), (-1,-1), TOTAL_BG),
        ('LINEABOVE', (0,-1), (-1,-1), 1.5, DEEP_BLUE),
        ('LINEBELOW', (0,-1), (-1,-1), 1.5, DEEP_BLUE),
        ('TOPPADDING', (0,0), (-1,-1), 4), ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6), ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'), ('ALIGN', (2,0), (2,-1), 'RIGHT'),
        ('LINEAFTER', (1,0), (1,-1), 0.4, BORDER),
    ]))
    wrap = Table([[mt]], colWidths=[PW])
    wrap.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    elements.append(wrap)
    elements.append(Spacer(1, 0.12*inch))

    # ═══════════ NET SALARY BOX ═══════════
    words_str = amount_to_words(pdf_computed_net)

    nsl = ParagraphStyle('nsl', fontSize=9, fontName='Helvetica-Bold',
                          textColor=colors.HexColor("#065f46"), alignment=TA_LEFT)
    nsv = ParagraphStyle('nsv', fontSize=14, fontName='Helvetica-Bold',
                          textColor=GREEN, alignment=TA_RIGHT)
    nsw = ParagraphStyle('nsw', fontSize=7, fontName='Helvetica-Oblique',
                          textColor=colors.HexColor("#166534"), alignment=TA_LEFT)

    net = Table([
        [Paragraph("<b>NET SALARY</b>", nsl), Paragraph(f"GHS {pdf_computed_net:,.2f}", nsv)],
        [Paragraph(words_str, nsw), Paragraph("", tl)],
    ], colWidths=[PW*0.50, PW*0.50])
    net.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,0), (-1,-1), GREEN_BG),
        ('TOPPADDING', (0,0), (-1,-1), 6), ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 10), ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('LINEABOVE', (0,1), (-1,1), 0.5, GREEN_BORDER),
    ]))
    elements.append(net)
    elements.append(Spacer(1, 0.12*inch))

    # ═══════════ LOAN TABLE ═══════════
    loans = db.query(Loan).filter(Loan.employee_name == employee.name, Loan.status != "Completed").all()
    if loans:
        loan_title = ParagraphStyle('lt', fontSize=8, fontName='Helvetica-Bold',
                                     textColor=DEEP_BLUE, alignment=TA_LEFT)
        loan_hdr = ParagraphStyle('lh', fontSize=6.5, fontName='Helvetica-Bold',
                                   textColor=WHITE, alignment=TA_LEFT)
        loan_hdr_r = ParagraphStyle('lhr', fontSize=6.5, fontName='Helvetica-Bold',
                                     textColor=WHITE, alignment=TA_RIGHT)
        loan_cell = ParagraphStyle('lc', fontSize=6.5, fontName='Helvetica',
                                    textColor=DARK, alignment=TA_LEFT)
        loan_cell_r = ParagraphStyle('lcr', fontSize=6.5, fontName='Helvetica',
                                      textColor=DARK, alignment=TA_RIGHT)
        
        loan_rows = [[
            Paragraph("Bank Name", loan_hdr),
            Paragraph("Loan Amount Requested", loan_hdr_r),
            Paragraph("Amount Paid", loan_hdr_r),
            Paragraph("Months Remaining", loan_hdr_r),
        ]]
        for l in loans:
            months_remaining = max(0, (l.months_to_pay or 0) - (l.months_paid or 0))
            loan_rows.append([
                Paragraph(l.bank_name or "N/A", loan_cell),
                Paragraph(f"GHS {l.loan_amount:,.2f}" if l.loan_amount else "GHS 0.00", loan_cell_r),
                Paragraph(f"GHS {l.amount_paid:,.2f}" if l.amount_paid else "GHS 0.00", loan_cell_r),
                Paragraph(str(months_remaining), loan_cell_r),
            ])
        
        lcw = [PW*0.30, PW*0.28, PW*0.24, PW*0.18]
        loan_table = Table(loan_rows, colWidths=lcw)
        loan_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), DEEP_BLUE),
            ('TEXTCOLOR', (0,0), (-1,0), WHITE),
            ('LINEBELOW', (0,1), (-1,-1), 0.4, BORDER),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE, GRAY_ALT]),
            ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
            ('LINEABOVE', (0,1), (-1,1), 0.4, BORDER),
        ]))
        
        loan_title_table = Table([
            [Paragraph("<i class='fas fa-hand-holding-usd'></i> LOAN REPAYMENT SUMMARY", loan_title)]
        ], colWidths=[PW])
        elements.append(loan_title_table)
        elements.append(Spacer(1, 0.02*inch))
        
        loan_wrap = Table([[loan_table]], colWidths=[PW])
        loan_wrap.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 0.5, BORDER),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ]))
        elements.append(loan_wrap)
        elements.append(Spacer(1, 0.12*inch))

    # ═══════════ FOOTER ═══════════
    ds = ParagraphStyle('ds', fontSize=6.5, fontName='Helvetica',
                        textColor=colors.HexColor("#9ca3af"), alignment=TA_CENTER)
    fs = ParagraphStyle('fs', fontSize=6.5, fontName='Helvetica-Oblique',
                        textColor=colors.HexColor("#9ca3af"), alignment=TA_CENTER)
    bank_info = ""
    if employee.bank_name or employee.bank_number:
        bank_info = f"Bank: {employee.bank_name or ''} {employee.bank_branch or ''} | Acc: {employee.bank_number or 'N/A'}"
    else:
        bank_info = "Payment will be processed by Finance Department"
    elements.append(Paragraph(bank_info, ds))
    elements.append(Spacer(1, 3))
    elements.append(Paragraph("This is a computer-generated document and does not require a signature.", fs))

    doc.build(elements)
    return filename
