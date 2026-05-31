from fastapi import FastAPI, Request, Depends, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.api import auth, payroll
from app.core.config import settings
from app.services.cache_service import get_cache, set_cache
from app.core.database import get_db
from app.core.security import get_current_user, get_current_user_web
from app.models.user import User
import os
import urllib.parse

app = FastAPI(title="Payroll Processing System", version="1.0.0")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")
templates.env.cache = None

import json

def tojson_filter(value):
    try:
        if hasattr(value, '__table__'):
            return json.dumps({c.name: getattr(value, c.name, None) for c in value.__table__.columns}, default=str)
        return json.dumps(value, default=str)
    except:
        return json.dumps(str(value))

# Custom Jinja filters
def format_month(value):
    """Convert '2024-01' or '2024-01-31' to readable month name"""
    if not value:
        return value
    import datetime
    try:
        parts = str(value).split('-')
        year = parts[0]
        month_num = parts[1].zfill(2)
        month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December']
        month_name = month_names[int(month_num)] if 1 <= int(month_num) <= 12 else month_num
        return f"{month_name} {year}"
    except:
        return value

templates.env.filters['format_month'] = format_month
templates.env.filters['tojson'] = tojson_filter

# API routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(payroll.router, prefix="/payroll", tags=["Payroll"])

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return RedirectResponse(url="/login")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    template = templates.get_template("login.html")
    rendered = template.render({"active_tab": "login"})
    return HTMLResponse(content=rendered, media_type="text/html")

@app.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    from app.core.security import verify_password, create_access_token
    user = db.query(User).filter(User.email == email).first()
    if user and verify_password(password, user.hashed_password):
        # Create JWT token and set in cookie
        access_token = create_access_token(data={"sub": user.email})
        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
        return response
    template = templates.get_template("login.html")
    rendered = template.render({"error": "Invalid credentials", "active_tab": "login"})
    return HTMLResponse(content=rendered, media_type="text/html")

@app.post("/register")
async def register(request: Request, email: str = Form(...), password: str = Form(...), confirm_password: str = Form(...), role: str = Form(...), first_name: str = Form(...), last_name: str = Form(...), terms: bool = Form(...), db: Session = Depends(get_db)):
    # Validate input
    if password != confirm_password:
        template = templates.get_template("login.html")
        rendered = template.render({"register_error": "Passwords do not match", "active_tab": "register"})
        return HTMLResponse(content=rendered, media_type="text/html")
    
    if len(password) < 8:
        template = templates.get_template("login.html")
        rendered = template.render({"register_error": "Password must be at least 8 characters long", "active_tab": "register"})
        return HTMLResponse(content=rendered, media_type="text/html")
    
    if not terms:
        template = templates.get_template("login.html")
        rendered = template.render({"register_error": "You must agree to the terms and conditions", "active_tab": "register"})
        return HTMLResponse(content=rendered, media_type="text/html")
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        template = templates.get_template("login.html")
        rendered = template.render({"register_error": "Email already registered", "active_tab": "register"})
        return HTMLResponse(content=rendered, media_type="text/html")
    
    # Create user
    from app.core.security import get_password_hash
    hashed_password = get_password_hash(password)
    new_user = User(email=email, hashed_password=hashed_password, role=role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Success message
    template = templates.get_template("login.html")
    rendered = template.render({"register_success": "Account created successfully! Please login.", "active_tab": "login"})
    return HTMLResponse(content=rendered, media_type="text/html")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    try:
        current_user = get_current_user_web(request, db)
        from app.models.employee import Employee
        from app.models.payroll import PayrollRecord
        from datetime import datetime
        from app.services.cache_service import get_cache, set_cache

        cache_key = "dash"
        cached = get_cache(cache_key)
        if cached:
            stats, recent_payslips = cached
        else:
            # Build stats for the dashboard
            employee_count = db.query(Employee).count()
            payslip_count = db.query(PayrollRecord).count()
            total_payroll = db.query(PayrollRecord).with_entities(PayrollRecord.net_salary).all()
            total_payroll_sum = sum(p[0] or 0 for p in total_payroll)
            avg_net_salary = (total_payroll_sum / payslip_count) if payslip_count > 0 else 0

            # Distinct months
            months = db.query(PayrollRecord.month).distinct().all()
            months_active = len([m[0] for m in months if m[0]])

            stats = {
                "employee_count": employee_count,
                "payslip_count": payslip_count,
                "total_payroll": total_payroll_sum,
                "months_active": months_active,
                "upload_count": months_active,
                "avg_net_salary": avg_net_salary,
                "email_sent": 0
            }

            # Recent payslips (last 5)
            recent_payslips = db.query(PayrollRecord).order_by(PayrollRecord.id.desc()).limit(5).all()
            set_cache(cache_key, (stats, recent_payslips), ttl_seconds=120)

        template = templates.get_template("dashboard.html")
        rendered = template.render({
            "user": current_user,
            "stats": stats,
            "recent_payslips": recent_payslips,
            "activities": [],
            "now": datetime.now
        })
        return HTMLResponse(content=rendered, media_type="text/html")
    except HTTPException:
        template = templates.get_template("login.html")
        rendered = template.render({})
        return HTMLResponse(content=rendered, media_type="text/html")

@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request, db: Session = Depends(get_db)):
    try:
        current_user = get_current_user_web(request, db)
        template = templates.get_template("upload.html")
        rendered = template.render({"user": current_user})
        return HTMLResponse(content=rendered, media_type="text/html")
    except HTTPException:
        template = templates.get_template("login.html")
        rendered = template.render({})
        return HTMLResponse(content=rendered, media_type="text/html")

@app.post("/upload")
async def upload_payroll(request: Request, file: UploadFile = File(...), month: str = Form(...), db: Session = Depends(get_db)):
    try:
        current_user = get_current_user_web(request, db)
    except HTTPException:
        return RedirectResponse(url="/login", status_code=303)
    
    from app.services.excel_service import process_payroll_excel
    from app.services.payroll_service import create_payroll_record
    from app.models.employee import Employee
    from app.models.payroll import PayrollRecord
    from datetime import datetime, date
    import tempfile
    import os
    import time

    if not file.filename.endswith(('.xlsx', '.csv')):
        template = templates.get_template("upload.html")
        rendered = template.render({"user": current_user, "error": "Only .xlsx and .csv files allowed"})
        return HTMLResponse(content=rendered, media_type="text/html")

    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            db.close()
            from app.core.database import SessionLocal
            db = SessionLocal()
            
            records = process_payroll_excel(tmp_path, month)
            processed = 0
            errors = []
            unmatched_records = []  # Names that didn't match any registered employee
            
            # Track IDs of employees that appear in the file
            matched_emp_ids = set()
            
            for record in records:
                try:
                    emp_no = str(record.get('employee_number', '') or '').strip()
                    emp_email = str(record.get('email', '') or '').strip()
                    emp_name = str(record.get('employee_name', '') or '').strip()
                    # Normalize: collapse multiple spaces, remove leading/trailing spaces
                    emp_name_norm = ' '.join(emp_name.split()).upper()
                    
                    employee = None
                    # PRIMARY: Match by employee name (case-insensitive, normalized)
                    if emp_name_norm:
                        # First try exact match (normalized - both upper)
                        all_emps = db.query(Employee).all()
                        for e in all_emps:
                            db_name_norm = ' '.join((e.name or '').split()).upper()
                            if db_name_norm == emp_name_norm:
                                employee = e
                                break
                    if not employee and emp_name_norm:
                        # Try partial match
                        employee = db.query(Employee).filter(
                            Employee.name.ilike(f'%{emp_name}%')
                        ).first()
                    if not employee and emp_name_norm:
                        # Try matching by individual name parts
                        name_parts = emp_name_norm.split()
                        for part in name_parts:
                            if len(part) > 2:
                                all_emps = db.query(Employee).all()
                                for e in all_emps:
                                    db_name_norm = ' '.join((e.name or '').split()).upper()
                                    if part in db_name_norm:
                                        employee = e
                                        break
                                if employee:
                                    break
                    # FALLBACK: Match by employee number if name didn't match
                    if not employee and emp_no:
                        employee = db.query(Employee).filter(Employee.employee_number == emp_no).first()
                    # FALLBACK: Match by email if still no match
                    if not employee and emp_email:
                        employee = db.query(Employee).filter(Employee.email == emp_email).first()
                    
                    if not employee:
                        # No match found - skip and list for correction
                        unmatched_records.append({
                            'name': emp_name or emp_no or emp_email or 'Unknown',
                            'number': emp_no,
                            'email': emp_email
                        })
                        print(f"MATCH FAILED: emp_name={repr(emp_name)} normalized={repr(emp_name_norm)} emp_no={repr(emp_no)}")
                        continue
                    
                    print(f"MATCH OK: emp_name={repr(emp_name)} -> {employee.name} (ID={employee.id})")
                    
                    # Existing employee matched - update details from file if provided
                    if record.get('employee_name'): 
                        employee.name = str(record['employee_name']).strip()
                    if record.get('function'): 
                        employee.function = str(record['function']).strip()
                    if record.get('designation'): 
                        employee.designation = str(record['designation']).strip()
                    if record.get('location'): 
                        employee.location = str(record['location']).strip()
                    if record.get('bank_account'):
                        from app.services.pdf_service import parse_bank_account
                        bn, bk, bb = parse_bank_account(record.get('bank_account', ''))
                        if bn: employee.bank_number = bn
                        if bk: employee.bank_name = bk
                        if bb: employee.bank_branch = bb
                    db.commit()
                    
                    matched_emp_ids.add(employee.id)
                    
                    # Check if payroll record already exists for this employee + month
                    existing_payroll = db.query(PayrollRecord).filter(
                        PayrollRecord.employee_id == employee.id,
                        PayrollRecord.month == month
                    ).first()
                    
                    if existing_payroll:
                        # Update existing record instead of creating duplicate
                        existing_payroll.basic_salary = record.get('basic_salary', existing_payroll.basic_salary)
                        existing_payroll.meals_monthly = record.get('meals_monthly', existing_payroll.meals_monthly)
                        existing_payroll.responsibility_allowance = record.get('responsibility_allowance', existing_payroll.responsibility_allowance)
                        existing_payroll.cola = record.get('cola', existing_payroll.cola)
                        existing_payroll.leave_allowance = record.get('leave_allowance', existing_payroll.leave_allowance)
                        existing_payroll.other_earnings = record.get('other_earnings', existing_payroll.other_earnings)
                        existing_payroll.paye = record.get('paye', existing_payroll.paye)
                        existing_payroll.tithe = record.get('tithe', existing_payroll.tithe)
                        existing_payroll.future_savings = record.get('future_savings', existing_payroll.future_savings)
                        existing_payroll.other_deductions = record.get('other_deductions', existing_payroll.other_deductions)
                        existing_payroll.employer_contribution = record.get('employer_contribution', existing_payroll.employer_contribution)
                        from app.services.payroll_service import calculate_payroll_totals
                        earnings = {
                            'basic_salary': existing_payroll.basic_salary,
                            'meals_monthly': existing_payroll.meals_monthly,
                            'responsibility_allowance': existing_payroll.responsibility_allowance,
                            'cola': existing_payroll.cola,
                            'leave_allowance': existing_payroll.leave_allowance,
                            'other_earnings': existing_payroll.other_earnings,
                        }
                        deductions = {
                            'paye': existing_payroll.paye,
                            'tithe': existing_payroll.tithe,
                            'future_savings': existing_payroll.future_savings,
                            'other_deductions': existing_payroll.other_deductions,
                        }
                        total_earnings, total_deductions, net_salary = calculate_payroll_totals(earnings, deductions)
                        existing_payroll.total_earnings = total_earnings
                        existing_payroll.total_deductions = total_deductions
                        existing_payroll.net_salary = net_salary
                        # Clear old PDF so it gets regenerated on demand
                        if existing_payroll.pdf_generated:
                            try:
                                if os.path.exists(existing_payroll.pdf_generated):
                                    os.remove(existing_payroll.pdf_generated)
                            except:
                                pass
                            existing_payroll.pdf_generated = None
                        db.commit()
                    else:
                        # Create payroll record (no PDF generation during upload)
                        payroll_record = create_payroll_record(db, employee.id, record)
                        db.commit()
                    
                    processed += 1
                except Exception as e:
                    db.rollback()
                    errors.append(f"Error processing {record.get('employee_name', 'Unknown')}: {str(e)[:80]}")
            
            # Identify registered employees NOT in this upload (possibly terminated)
            all_emp_ids = {r.id for r in db.query(Employee.id).all()}
            missing_emp_ids = all_emp_ids - matched_emp_ids
            missing_employees = []
            if missing_emp_ids:
                missing_emps = db.query(Employee).filter(Employee.id.in_(missing_emp_ids)).order_by(Employee.name).all()
                missing_employees = [e for e in missing_emps if e.name]
            
            # Build summary
            summary_parts = []
            if processed:
                summary_parts.append(f"Successfully uploaded {processed} payroll record(s) for {month}")
            if unmatched_records:
                summary_parts.append(f"{len(unmatched_records)} name(s) did not match any registered employee (skipped)")
            if missing_employees:
                summary_parts.append(f"{len(missing_employees)} registered employee(s) not in this file (may be terminated)")
            
            msg = ". ".join(summary_parts) + "." if summary_parts else "No data processed."

            template = templates.get_template("upload.html")
            rendered = template.render({
                "user": current_user,
                "message": msg,
                "errors": errors[:5],
                "unmatched_records": unmatched_records,
                "missing_employees": missing_employees,
                "processed_count": processed
            })
            return HTMLResponse(content=rendered, media_type="text/html")
            
        except Exception as e:
            db.rollback()
            template = templates.get_template("upload.html")
            rendered = template.render({"user": current_user, "error": f"Upload failed: {str(e)[:200]}"})
            return HTMLResponse(content=rendered, media_type="text/html")
        finally:
            try:
                os.unlink(tmp_path)
            except:
                pass
    
    template = templates.get_template("upload.html")
    rendered = template.render({"user": current_user, "error": "Upload failed after multiple retry attempts"})
    return HTMLResponse(content=rendered, media_type="text/html")

@app.get("/staff", response_class=HTMLResponse)
async def staff_page(request: Request, db: Session = Depends(get_db)):
    try:
        current_user = get_current_user_web(request, db)
        from app.models.employee import Employee
        
        # Get all staff members
        staff_list = db.query(Employee).all()
        
        template = templates.get_template("staff.html")
        rendered = template.render({"user": current_user, "staff_list": staff_list})
        return HTMLResponse(content=rendered, media_type="text/html")
    except HTTPException:
        return RedirectResponse(url="/login", status_code=303)

@app.post("/staff/add")
async def add_staff(request: Request, employee_number: str = Form(...), name: str = Form(...), 
                   email: str = Form(...), function: str = Form(default=""),
                   designation: str = Form(default=""), location: str = Form(default=""),
                   ssnit_number: str = Form(default=""), tax_relief: str = Form(default=""),
                   employer_contribution: float = Form(default=0), bank_number: str = Form(default=""),
                   bank_name: str = Form(default=""), bank_branch: str = Form(default=""),
                   date_joined: str = Form(default=None), db: Session = Depends(get_db)):
    try:
        current_user = get_current_user_web(request, db)
    except HTTPException:
        return RedirectResponse(url="/login", status_code=303)
    
    from app.models.employee import Employee
    from datetime import datetime
    
    # Check if employee exists
    existing = db.query(Employee).filter(
        (Employee.email == email) | (Employee.employee_number == employee_number)
    ).first()
    
    if existing:
        staff_list = db.query(Employee).all()
        template = templates.get_template("staff.html")
        rendered = template.render({"user": current_user, "staff_list": staff_list, "error": "Employee already exists"})
        return HTMLResponse(content=rendered, media_type="text/html")
    
    try:
        date_obj = None
        if date_joined:
            date_obj = datetime.strptime(date_joined, "%Y-%m-%d").date()
        
        employee = Employee(
            employee_number=employee_number,
            name=name,
            email=email,
            function=function,
            designation=designation,
            location=location,
            ssnit_number=ssnit_number,
            tax_relief=tax_relief,
            employer_contribution=employer_contribution or 0,
            bank_number=bank_number,
            bank_name=bank_name,
            bank_branch=bank_branch,
            date_joined=date_obj
        )
        db.add(employee)
        db.commit()
        
        staff_list = db.query(Employee).all()
        template = templates.get_template("staff.html")
        rendered = template.render({"user": current_user, "staff_list": staff_list, "success": f"Staff member {name} added successfully"})
        return HTMLResponse(content=rendered, media_type="text/html")
    except Exception as e:
        db.rollback()
        staff_list = db.query(Employee).all()
        template = templates.get_template("staff.html")
        rendered = template.render({"user": current_user, "staff_list": staff_list, "error": f"Failed to add staff: {str(e)}"})
        return HTMLResponse(content=rendered, media_type="text/html")

@app.get("/staff/edit/{staff_id}", response_class=HTMLResponse)
async def edit_staff_page(request: Request, staff_id: int, db: Session = Depends(get_db)):
    try:
        current_user = get_current_user_web(request, db)
        from app.models.employee import Employee
        
        staff = db.query(Employee).filter(Employee.id == staff_id).first()
        if not staff:
            raise HTTPException(status_code=404, detail="Staff member not found")
        
        staff_list = db.query(Employee).all()
        template = templates.get_template("staff.html")
        rendered = template.render({"user": current_user, "staff": staff, "staff_list": staff_list})
        return HTMLResponse(content=rendered, media_type="text/html")
    except HTTPException:
        return RedirectResponse(url="/login", status_code=303)

@app.post("/staff/update/{staff_id}")
async def update_staff(request: Request, staff_id: int, employee_number: str = Form(...), name: str = Form(...), 
                       email: str = Form(...), function: str = Form(default=""),
                       designation: str = Form(default=""), location: str = Form(default=""),
                       ssnit_number: str = Form(default=""), tax_relief: str = Form(default=""),
                       employer_contribution: float = Form(default=0), bank_number: str = Form(default=""),
                       bank_name: str = Form(default=""), bank_branch: str = Form(default=""),
                       date_joined: str = Form(default=None), db: Session = Depends(get_db)):
    try:
        current_user = get_current_user_web(request, db)
    except HTTPException:
        return RedirectResponse(url="/login", status_code=303)
    
    from app.models.employee import Employee
    from datetime import datetime
    
    try:
        staff = db.query(Employee).filter(Employee.id == staff_id).first()
        if not staff:
            raise HTTPException(status_code=404, detail="Staff member not found")
        
        # Check if new email/employee_number already exists for another employee
        existing = db.query(Employee).filter(
            (Employee.id != staff_id) &
            ((Employee.email == email) | (Employee.employee_number == employee_number))
        ).first()
        
        if existing:
            staff_list = db.query(Employee).all()
            template = templates.get_template("staff.html")
            rendered = template.render({"user": current_user, "staff": staff, "staff_list": staff_list, 
                                      "error": "Email or employee number already exists"})
            return HTMLResponse(content=rendered, media_type="text/html")
        
        # Update employee
        staff.employee_number = employee_number
        staff.name = name
        staff.email = email
        staff.function = function
        staff.designation = designation
        staff.location = location
        staff.ssnit_number = ssnit_number
        staff.tax_relief = tax_relief
        staff.employer_contribution = employer_contribution or 0
        staff.bank_number = bank_number
        staff.bank_name = bank_name
        staff.bank_branch = bank_branch
        
        if date_joined:
            staff.date_joined = datetime.strptime(date_joined, "%Y-%m-%d").date()
        
        db.commit()
        
        staff_list = db.query(Employee).all()
        template = templates.get_template("staff.html")
        rendered = template.render({"user": current_user, "staff_list": staff_list, "success": f"Staff member {name} updated successfully"})
        return HTMLResponse(content=rendered, media_type="text/html")
    except Exception as e:
        db.rollback()
        staff_list = db.query(Employee).all()
        staff = db.query(Employee).filter(Employee.id == staff_id).first()
        template = templates.get_template("staff.html")
        rendered = template.render({"user": current_user, "staff": staff, "staff_list": staff_list, "error": f"Failed to update staff: {str(e)}"})
        return HTMLResponse(content=rendered, media_type="text/html")

@app.post("/staff/delete/{staff_id}")
async def delete_staff(request: Request, staff_id: int, db: Session = Depends(get_db)):
    try:
        current_user = get_current_user_web(request, db)
    except HTTPException:
        return RedirectResponse(url="/login", status_code=303)
    
    from app.models.employee import Employee
    
    try:
        staff = db.query(Employee).filter(Employee.id == staff_id).first()
        if not staff:
            staff_list = db.query(Employee).all()
            template = templates.get_template("staff.html")
            rendered = template.render({"user": current_user, "staff_list": staff_list, "error": "Staff member not found"})
            return HTMLResponse(content=rendered, media_type="text/html")
        
        staff_name = staff.name
        db.delete(staff)
        db.commit()
        
        staff_list = db.query(Employee).all()
        template = templates.get_template("staff.html")
        rendered = template.render({"user": current_user, "staff_list": staff_list, "success": f"Staff member {staff_name} deleted successfully"})
        return HTMLResponse(content=rendered, media_type="text/html")
    except Exception as e:
        db.rollback()
        staff_list = db.query(Employee).all()
        template = templates.get_template("staff.html")
        rendered = template.render({"user": current_user, "staff_list": staff_list, "error": f"Failed to delete staff: {str(e)}"})
        return HTMLResponse(content=rendered, media_type="text/html")

@app.get("/payslips", response_class=HTMLResponse)
async def payslips_page(request: Request, db: Session = Depends(get_db)):
    try:
        current_user = get_current_user_web(request, db)
        from app.models.payroll import PayrollRecord
        from app.models.employee import Employee
        from app.services.cache_service import get_cache, set_cache
        
        cache_key = "payslips_data"
        cached = get_cache(cache_key)
        if cached:
            payslips = cached
            # Re-attach employee info (cache breaks object references)
            for p in payslips:
                if hasattr(p, 'employee_id') and p.employee_id:
                    emp = db.query(Employee).filter(Employee.id == p.employee_id).first()
                    p.employee = emp
                else:
                    emp = db.query(Employee).filter(Employee.name == p.employee_name).first()
                    p.employee = emp
        else:
            # Query payslips
            payslips = db.query(PayrollRecord).all()
            # Attach employee names for template
            for p in payslips:
                if hasattr(p, 'employee_id') and p.employee_id:
                    emp = db.query(Employee).filter(Employee.id == p.employee_id).first()
                    p.employee = emp
                else:
                    emp = db.query(Employee).filter(Employee.name == p.employee_name).first()
                    p.employee = emp
            set_cache(cache_key, payslips, ttl_seconds=120)
        
        # Get distinct months for filter
        payroll_months = db.query(PayrollRecord.month).distinct().order_by(PayrollRecord.month.desc()).all()
        months = [m[0] for m in payroll_months if m[0]]
        
        selected_month = request.query_params.get("month", "")
        
        # Generate month-to-date stats
        total_payslips = len(payslips)
        total_net_salary = sum(p.net_salary or 0 for p in payslips)
        total_earnings = sum(p.total_earnings or 0 for p in payslips)
        total_deductions = sum(p.total_deductions or 0 for p in payslips)
        
        template = templates.get_template("payslips.html")
        rendered = template.render({
            "user": current_user, 
            "payslips": payslips,
            "months": months,
            "selected_month": selected_month,
            "total_payslips": total_payslips,
            "total_net_salary": total_net_salary,
            "total_earnings": total_earnings,
            "total_deductions": total_deductions,
            "success": request.query_params.get("success"),
            "error": request.query_params.get("error")
        })
        return HTMLResponse(content=rendered, media_type="text/html")
    except HTTPException:
        return RedirectResponse(url="/login", status_code=303)
    except Exception as e:
        template = templates.get_template("payslips.html")
        rendered = template.render({"error": f"Error loading payslips: {str(e)}", "payslips": [], "months": [], "selected_month": ""})
        return HTMLResponse(content=rendered, media_type="text/html")

@app.get("/payslips/{payroll_id}/data")
async def payslip_data(payroll_id: int, request: Request, db: Session = Depends(get_db)):
    """Return payslip data as JSON for preview modal"""
    try:
        current_user = get_current_user_web(request, db)
    except Exception:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})
    
    from app.models.payroll import PayrollRecord
    from app.models.employee import Employee
    from app.services.pdf_service import generate_payslip_pdf
    
    payroll = db.query(PayrollRecord).filter(PayrollRecord.id == payroll_id).first()
    if not payroll:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"error": "Payslip not found"})
    
    # Generate PDF on demand if not already generated (for preview button to work)
    if not payroll.pdf_generated or not isinstance(payroll.pdf_generated, str) or not os.path.exists(str(payroll.pdf_generated or "")):
        try:
            pdf_path = generate_payslip_pdf(db, payroll.id)
            if pdf_path:
                payroll.pdf_generated = pdf_path
                db.commit()
        except Exception as e:
            pass  # PDF generation failed, preview still works
    
    employee = db.query(Employee).filter(Employee.name == payroll.employee_name).first()
    
    emp_data = {
        "name": employee.name if employee else payroll.employee_name or "Unknown",
        "employee_number": employee.employee_number if employee else "N/A",
        "designation": employee.designation if employee else "",
        "function": employee.function if employee else "",
        "location": employee.location if employee else "",
        "bank_name": employee.bank_name if employee else "N/A",
        "bank_branch": employee.bank_branch if employee else "",
        "bank_number": employee.bank_number if employee else "N/A",
        "email": employee.email if employee else "",
        "date_joined": str(employee.date_joined) if employee and employee.date_joined else "",
        "ssnit_number": employee.ssnit_number if employee else "",
        }

    return {
        "id": payroll.id,
        "month": payroll.month,
        "employee_name": payroll.employee_name or "N/A",
        "employee_number": emp_data.get("employee_number", "N/A"),
        "email": emp_data.get("email", ""),
        "designation": emp_data.get("designation", ""),
        "function": emp_data.get("function", ""),
        "location": emp_data.get("location", ""),
        "bank_name": emp_data.get("bank_name", "N/A"),
        "bank_branch": emp_data.get("bank_branch", ""),
        "bank_number": emp_data.get("bank_number", "N/A"),
        "date_joined": emp_data.get("date_joined", ""),
        "ssnit_number": emp_data.get("ssnit_number", ""),
        "basic_salary": float(payroll.basic_salary or 0),
        "meals_monthly": float(payroll.meals_monthly or 0),
        "responsibility_allowance": float(payroll.responsibility_allowance or 0),
        "cola": float(payroll.cola or 0),
        "leave_allowance": float(payroll.leave_allowance or 0),
        "other_earnings": float(payroll.other_earnings or 0),
        "total_earnings": float(payroll.total_earnings or 0),
        "paye": float(payroll.paye or 0),
        "tithe": float(payroll.tithe or 0),
        "future_savings": float(payroll.future_savings or 0),
        "other_deductions": float(payroll.other_deductions or 0),
        "total_deductions": float(payroll.total_deductions or 0),
        "net_salary": float(payroll.net_salary or 0),
        "employer_contribution": float(payroll.employer_contribution or 0),
        "pdf_generated": bool(payroll.pdf_generated) if hasattr(payroll, 'pdf_generated') else False
    }

@app.get("/payslips/{payroll_id}/download")
async def download_payslip(payroll_id: int, request: Request, db: Session = Depends(get_db)):
    from app.models.payroll import PayrollRecord
    from app.services.pdf_service import generate_payslip_pdf, get_pdf_temp_dir
    from fastapi.responses import FileResponse
    
    # Authenticate user
    try:
        current_user = get_current_user_web(request, db)
    except Exception:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    payroll = db.query(PayrollRecord).filter(PayrollRecord.id == payroll_id).first()
    if not payroll:
        raise HTTPException(status_code=404, detail="Payslip not found")
    
    # Generate PDF on demand if not already generated (or regenerated from temp)
    if not payroll.pdf_generated or not isinstance(payroll.pdf_generated, str) or not os.path.exists(payroll.pdf_generated):
        pdf_path = generate_payslip_pdf(db, payroll.id)
        if not pdf_path:
            raise HTTPException(status_code=500, detail="Failed to generate payslip PDF")
        payroll.pdf_generated = pdf_path
        db.commit()
    else:
        # If the file still exists and was generated in temp dir, serve it
        # Otherwise regenerate
        if not os.path.exists(payroll.pdf_generated):
            pdf_path = generate_payslip_pdf(db, payroll.id)
            if not pdf_path:
                raise HTTPException(status_code=500, detail="Failed to generate payslip PDF")
            payroll.pdf_generated = pdf_path
            db.commit()
    
    if not isinstance(payroll.pdf_generated, str) or not os.path.exists(payroll.pdf_generated):
        raise HTTPException(status_code=404, detail="PDF file not found")
    
    return FileResponse(payroll.pdf_generated, media_type="application/pdf", filename=os.path.basename(payroll.pdf_generated))

@app.post("/payslips/{payroll_id}/send-email")
async def send_payslip_email(payroll_id: int, request: Request, db: Session = Depends(get_db)):
    """Send payslip to employee via email"""
    try:
        current_user = get_current_user_web(request, db)
    except:
        # Return a simple HTML response for failed auth
        return await send_payslip_redirect(request, "Not authenticated. Please login again.", "error")
    
    from app.models.payroll import PayrollRecord
    from app.models.employee import Employee
    from app.services.email_service import EmailService
    from app.services.pdf_service import generate_payslip_pdf
    
    try:
        payroll = db.query(PayrollRecord).filter(PayrollRecord.id == payroll_id).first()
        if not payroll:
            return await send_payslip_redirect(request, "Payslip not found.", "error")
        
        employee = db.query(Employee).filter(Employee.name == payroll.employee_name).first()
        if not employee or not employee.email:
            return await send_payslip_redirect(request, "Employee email not configured.", "error")
        
        # Ensure PDF exists before sending
        if not payroll.pdf_generated or not isinstance(payroll.pdf_generated, str) or not os.path.exists(str(payroll.pdf_generated or '')):
            pdf_path = generate_payslip_pdf(db, payroll.id)
            if pdf_path:
                payroll.pdf_generated = pdf_path
                db.commit()
        
        if not payroll.pdf_generated or not isinstance(payroll.pdf_generated, str) or not os.path.exists(str(payroll.pdf_generated or '')):
            return await send_payslip_redirect(request, "Failed to generate PDF payslip.", "error")
        
        success, message = await EmailService.send_payslip(
            recipient_email=employee.email,
            employee_name=employee.name,
            month=payroll.month,
            pdf_path=payroll.pdf_generated,
            net_salary=payroll.net_salary
        )
        
        if success:
            return await send_payslip_redirect(request, f"Payslip sent to {employee.email}", "success")
        else:
            return await send_payslip_redirect(request, f"Failed to send email: {message}", "error")
    
    except Exception as e:
        return await send_payslip_redirect(request, f"Error sending payslip: {str(e)}", "error")


async def send_payslip_redirect(request: Request, msg: str, msg_type: str = "error"):
    """Redirect back to the send payslips page with a message"""
    referer = request.headers.get("referer", "/payslips/send")
    separator = "&" if "?" in referer else "?"
    return RedirectResponse(url=f"{referer}{separator}email_status={msg_type}&email_message={urllib.parse.quote(msg)}", status_code=303)

@app.get("/payslips/send", response_class=HTMLResponse)
@app.get("/payslips/send-all", response_class=HTMLResponse)
async def send_all_payslips_page(request: Request, db: Session = Depends(get_db), month: str = None, filter_by: str = "all"):
    """Page to send all payslips for a specific month"""
    try:
        current_user = get_current_user_web(request, db)
        from app.core.config import settings
        from app.models.payroll import PayrollRecord
        from app.models.employee import Employee
        from app.models.email_log import EmailLog
        
        # Get list of months with payslips
        payroll_months = db.query(PayrollRecord.month).distinct().all()
        months = [m[0] for m in payroll_months if m[0]]
        
        payslips = []
        if month:
            payslips = db.query(PayrollRecord).filter(PayrollRecord.month == month).all()
            
            # Attach employee info to each payslip
            for p in payslips:
                emp = db.query(Employee).filter(Employee.name == p.employee_name).first()
                p.employee_obj = emp
            
            # Apply filter
            if filter_by == "with_email":
                payslips = [p for p in payslips if p.employee_obj and p.employee_obj.email]
            elif filter_by == "no_email":
                payslips = [p for p in payslips if not p.employee_obj or not p.employee_obj.email]
        
                # Get recent email logs
        email_logs = []
        try:
            email_logs = db.query(EmailLog).order_by(EmailLog.sent_at.desc()).limit(50).all()
        except Exception:
            email_logs = []
        
        template = templates.get_template("send_payslips.html")
        rendered = template.render({
            "user": current_user,
            "request": request,
            "months": months,
            "selected_month": month,
            "filter_by": filter_by,
            "payslips": payslips,
            "email_logs": email_logs,
            "smtp_configured": bool(settings.smtp_server and settings.smtp_username),
            "smtp_server": settings.smtp_server or "",
            "smtp_port": settings.smtp_port or "",
            "smtp_username": settings.smtp_username or "",
            "smtp_password": settings.smtp_password or ""
        })
        return HTMLResponse(content=rendered, media_type="text/html")
    except HTTPException:
        return RedirectResponse(url="/login", status_code=303)

@app.post("/payslips/send-all")
async def send_all_payslips(request: Request, month: str = Form(...), db: Session = Depends(get_db)):
    """Send all payslips for a specific month"""
    try:
        current_user = get_current_user_web(request, db)
    except HTTPException:
        return RedirectResponse(url="/login", status_code=303)
    
    from app.models.payroll import PayrollRecord
    from app.services.email_service import EmailService
    from app.services.pdf_service import generate_payslip_pdf
    
    try:
        # Get all payslips for the month
        payslips = db.query(PayrollRecord).filter(PayrollRecord.month == month).all()
        
        if not payslips:
            template = templates.get_template("send_payslips.html")
            rendered = template.render({"user": current_user, "error": f"No payslips found for {month}"})
            return HTMLResponse(content=rendered, media_type="text/html")
        
        # First generate PDFs for any records that don't have them
        for p in payslips:
            if not p.pdf_generated or not os.path.exists(p.pdf_generated):
                pdf_path = generate_payslip_pdf(db, p.id)
                if pdf_path:
                    p.pdf_generated = pdf_path
        db.commit()
        
        # Send all payslips
        results = await EmailService.send_bulk_payslips(payslips, db)
        
        template = templates.get_template("send_payslips.html")
        rendered = template.render({
            "user": current_user, 
            "success": f"Sent {results['successful']} payslips. Failed: {results['failed']}",
            "results": results
        })
        return HTMLResponse(content=rendered, media_type="text/html")
    
    except Exception as e:
        template = templates.get_template("send_payslips.html")
        rendered = template.render({"user": current_user, "error": f"Error sending payslips: {str(e)}"})
        return HTMLResponse(content=rendered, media_type="text/html")

@app.post("/payslips/generate-all", response_class=JSONResponse)
async def generate_all_payslips(request: Request, month: str = Form(""), db: Session = Depends(get_db)):
    """Regenerate PDFs for all payslips in a given month (or all months if empty)"""
    from app.models.payroll import PayrollRecord
    from app.services.pdf_service import generate_payslip_pdf
    import os
    
    if month and month != "__ALL__":
        records = db.query(PayrollRecord).filter(PayrollRecord.month == month).all()
    else:
        records = db.query(PayrollRecord).all()
        month = "All Months"
    if not records:
        return {"success": False, "message": f"No payslips found for {month}"}
    
    generated = 0
    failed = 0
    for r in records:
        try:
            pdf_path = generate_payslip_pdf(db, r.id)
            if pdf_path:
                r.pdf_generated = pdf_path
                generated += 1
            else:
                failed += 1
        except:
            failed += 1
    db.commit()
    
    return {"success": True, "message": f"Generated {generated} PDF(s) for {month}. Failed: {failed}"}


@app.post("/payslips/{payroll_id}/generate-pdf", response_class=JSONResponse)
@app.post("/payslips/generate-single/{payroll_id}", response_class=JSONResponse)
async def generate_single_payslip(payroll_id: int, db: Session = Depends(get_db)):
    """Regenerate PDF for a single payslip"""
    from app.models.payroll import PayrollRecord
    from app.services.pdf_service import generate_payslip_pdf
    import os
    
    r = db.query(PayrollRecord).filter(PayrollRecord.id == payroll_id).first()
    if not r:
        return {"success": False, "message": "Payslip not found"}
    
    try:
        pdf_path = generate_payslip_pdf(db, r.id)
        if pdf_path:
            r.pdf_generated = pdf_path
            db.commit()
            return {"success": True, "message": "PDF generated successfully"}
        else:
            return {"success": False, "message": "PDF generation failed"}
    except Exception as e:
        return {"success": False, "message": str(e)}




# === LOAN MANAGEMENT ===
@app.get("/loans", response_class=HTMLResponse)
async def loans_page(request: Request, db: Session = Depends(get_db)):
    try:
        current_user = get_current_user_web(request, db)
    except HTTPException:
        return RedirectResponse(url="/login", status_code=303)
    
    from app.models.loan import Loan
    from app.models.employee import Employee
    from app.services.cache_service import get_cache, set_cache
    import json
    
    cache_key = "loans_data"
    cached = get_cache(cache_key)
    if cached:
        loans, employees_list, active_count, total_outstanding_sum, total_loaned_sum, completed_count = cached
        employees_json = json.dumps(employees_list)
    else:
        loans = db.query(Loan).order_by(Loan.created_at.desc()).all()
        employees = db.query(Employee).all()
        
        # Prepare employees JSON for autocomplete
        employees_list = [{"name": e.name, "employee_number": e.employee_number or ""} for e in employees if e.name]
        employees_json = json.dumps(employees_list)
        
        # Stats
        active_count = db.query(Loan).filter(Loan.status == "Active").count()
        total_outstanding = db.query(Loan).filter(Loan.status == "Active").with_entities(Loan.balance).all()
        total_outstanding_sum = sum(b[0] or 0 for b in total_outstanding)
        total_loaned = db.query(Loan).with_entities(Loan.loan_amount).all()
        total_loaned_sum = sum(l[0] or 0 for l in total_loaned)
        completed_count = db.query(Loan).filter(Loan.status == "Completed").count()
        set_cache(cache_key, (loans, employees_list, active_count, total_outstanding_sum, total_loaned_sum, completed_count), ttl_seconds=120)
    
    stats = {
        "active_count": active_count,
        "total_outstanding": total_outstanding_sum,
        "total_loaned": total_loaned_sum,
        "completed_count": completed_count
    }
    
    import json as _json_mod
    loans_json = _json_mod.dumps([{
        "id": l.id,
        "employee_name": l.employee_name,
        "bank_name": l.bank_name,
        "loan_amount": l.loan_amount,
        "interest_amount": l.interest_amount,
        "total_receivable": l.total_receivable,
        "monthly_deduction": l.monthly_deduction,
        "amount_paid": l.amount_paid,
        "months_to_pay": l.months_to_pay,
        "months_paid": l.months_paid,
        "balance": l.balance,
        "status": l.status,
        "notes": l.notes
    } for l in loans])
    
    template = templates.get_template("loans.html")
    rendered = template.render({
        "user": current_user,
        "loans": loans,
        "stats": stats,
        "employees_json": employees_json,
        "loans_json": loans_json,
        "success": request.query_params.get("success"),
        "error": request.query_params.get("error")
    })
    return HTMLResponse(content=rendered, media_type="text/html")

@app.post("/loans/add")
async def add_loan(request: Request, employee_name: str = Form(...), bank_name: str = Form(default=""),
                   loan_amount: float = Form(default=0), interest_amount: float = Form(default=0),
                   months_to_pay: int = Form(default=1), notes: str = Form(default=""),
                   db: Session = Depends(get_db)):
    try:
        current_user = get_current_user_web(request, db)
    except HTTPException:
        return RedirectResponse(url="/login", status_code=303)
    
    from app.models.loan import Loan
    
    try:
        total_receivable = loan_amount + interest_amount
        monthly_deduction = total_receivable / months_to_pay if months_to_pay > 0 else total_receivable
        
        loan = Loan(
            employee_name=employee_name,
            bank_name=bank_name,
            loan_amount=loan_amount,
            interest_amount=interest_amount,
            months_to_pay=months_to_pay,
            total_receivable=total_receivable,
            monthly_deduction=monthly_deduction,
            amount_paid=0,
            months_paid=0,
            balance=total_receivable,
            status="Active",
            notes=notes
        )
        db.add(loan)
        db.commit()
        
        return RedirectResponse(url="/loans?success=Loan+recorded+successfully", status_code=303)
    except Exception as e:
        db.rollback()
        return RedirectResponse(url=f"/loans?error={str(e)}", status_code=303)

@app.post("/loans/{loan_id}/pay")
async def pay_loan(request: Request, loan_id: int, payment_amount: float = Form(...), 
                   db: Session = Depends(get_db)):
    try:
        current_user = get_current_user_web(request, db)
    except HTTPException:
        return RedirectResponse(url="/login", status_code=303)
    
    from app.models.loan import Loan
    
    loan = db.query(Loan).filter(Loan.id == loan_id).first()
    if not loan:
        return RedirectResponse(url="/loans?error=Loan+not+found", status_code=303)
    
    try:
        loan.amount_paid = (loan.amount_paid or 0) + payment_amount
        loan.months_paid = (loan.months_paid or 0) + 1
        loan.balance = max(0, (loan.total_receivable or 0) - (loan.amount_paid or 0))
        
        if loan.balance <= 0:
            loan.status = "Completed"
        
        db.commit()
        return RedirectResponse(url=f"/loans?success=Payment+recorded+for+{loan.employee_name}", status_code=303)
    except Exception as e:
        db.rollback()
        return RedirectResponse(url=f"/loans?error={str(e)}", status_code=303)

@app.post("/loans/{loan_id}/default")
async def default_loan(loan_id: int, db: Session = Depends(get_db)):
    from app.models.loan import Loan
    
    loan = db.query(Loan).filter(Loan.id == loan_id).first()
    if not loan:
        return {"success": False, "message": "Loan not found"}
    
    loan.status = "Defaulted"
    db.commit()
    return {"success": True, "message": "Loan marked as defaulted"}

@app.post("/loans/delete/{loan_id}")
async def delete_loan(request: Request, loan_id: int, db: Session = Depends(get_db)):
    try:
        current_user = get_current_user_web(request, db)
    except HTTPException:
        return RedirectResponse(url="/login", status_code=303)
    
    from app.models.loan import Loan
    
    loan = db.query(Loan).filter(Loan.id == loan_id).first()
    if loan:
        db.delete(loan)
        db.commit()
        return RedirectResponse(url="/loans?success=Loan+deleted", status_code=303)
    return RedirectResponse(url="/loans?error=Loan+not+found", status_code=303)


# === EMAIL SETTINGS ===
@app.get("/settings/email", response_class=HTMLResponse)
async def email_settings_page(request: Request, db: Session = Depends(get_db)):
    try:
        current_user = get_current_user_web(request, db)
    except HTTPException:
        return RedirectResponse(url="/login", status_code=303)
    
    from app.core.config import settings
    
    # Determine security type - default to tls for port 587
    port = settings.smtp_port or 587
    if port == 587:
        smtp_security = "tls"
    elif port == 465:
        smtp_security = "ssl"
    else:
        smtp_security = "none"
    
    template = templates.get_template("email_settings.html")
    rendered = template.render({
        "user": current_user,
        "message": request.query_params.get("success"),
        "error": request.query_params.get("error"),
        "smtp_configured": bool(settings.smtp_server and settings.smtp_username),
        "smtp_server": settings.smtp_server or "",
        "smtp_port": port,
        "smtp_username": settings.smtp_username or "",
        "smtp_password": settings.smtp_password or "",
        "smtp_security": smtp_security
    })
    return HTMLResponse(content=rendered, media_type="text/html")

@app.post("/settings/email")
async def email_settings_save(request: Request, smtp_server: str = Form(...), smtp_port: int = Form(...),
                              smtp_username: str = Form(...), smtp_password: str = Form(...),
                              smtp_security: str = Form(...), db: Session = Depends(get_db)):
    try:
        current_user = get_current_user_web(request, db)
    except HTTPException:
        return RedirectResponse(url="/login", status_code=303)
    
        # Save to .env file
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        updates = {
            'smtp_server': smtp_server,
            'smtp_port': str(smtp_port),
            'smtp_username': smtp_username,
            'smtp_password': smtp_password,
            'smtp_security': smtp_security
        }
        
        updated_keys = set()
        new_lines = []
        for line in lines:
            stripped = line.strip()
            if '=' in stripped:
                key = stripped.split('=')[0].strip().lower()
                if key in updates:
                    new_lines.append(f'{key}={updates[key]}\n')
                    updated_keys.add(key)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        
        # Add any missing keys
        for key, val in updates.items():
            if key not in updated_keys:
                new_lines.append(f'{key}={val}\n')
        
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        
        return RedirectResponse(url="/settings/email?success=Settings+saved+to+.env+file.+Restart+server+to+apply.", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/settings/email?error=Failed+to+save:+{str(e)}", status_code=303)

@app.post("/settings/email/test")
async def test_email_connection(request: Request, db: Session = Depends(get_db)):
    try:
        current_user = get_current_user_web(request, db)
    except:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    from app.core.config import settings
    
    
    if not settings.smtp_server or not settings.smtp_username:
        raise HTTPException(status_code=400, detail="SMTP not configured. Check your .env file.")
    
    return {"status": "ok", "message": f"SMTP configured: {settings.smtp_server}:{settings.smtp_port}"}


# === PAYROLL REPORTS ===
@app.get("/reports", response_class=HTMLResponse)
async def reports_page(request: Request, db: Session = Depends(get_db)):
    try:
        current_user = get_current_user_web(request, db)
    except HTTPException:
        return RedirectResponse(url="/login", status_code=303)
    
    from app.models.payroll import PayrollRecord
    from app.models.employee import Employee
    from app.services.cache_service import get_cache, set_cache
    from sqlalchemy import func
    
    cache_key = "reports_data"
    cached = get_cache(cache_key)
    if cached:
        stats, monthly_data = cached
    else:
        total_records = db.query(PayrollRecord).count()
        total_employees = db.query(Employee).count()
        
        total_payroll_data = db.query(PayrollRecord.net_salary).all()
        total_payroll = sum(p[0] or 0 for p in total_payroll_data)
        avg_net = total_payroll / total_records if total_records > 0 else 0
        
        stats = {
            "total_records": total_records,
            "total_employees": total_employees,
            "total_payroll": total_payroll,
            "avg_net": avg_net
        }
        
        # Monthly breakdown
        months = db.query(PayrollRecord.month).distinct().order_by(PayrollRecord.month.desc()).all()
        monthly_data = []
        for m in months:
            if m[0]:
                records = db.query(PayrollRecord).filter(PayrollRecord.month == m[0]).all()
                monthly_data.append({
                    "month": m[0],
                    "count": len(records),
                    "total": sum(r.net_salary or 0 for r in records)
                })
        set_cache(cache_key, (stats, monthly_data), ttl_seconds=120)
    
    template = templates.get_template("reports.html")
    rendered = template.render({
        "user": current_user,
        "stats": stats,
        "monthly_data": monthly_data,
        "error": None
    })
    return HTMLResponse(content=rendered, media_type="text/html")


# === UPLOAD HISTORY ===
@app.get("/reports/history", response_class=HTMLResponse)
async def upload_history_page(request: Request, db: Session = Depends(get_db)):
    try:
        current_user = get_current_user_web(request, db)
    except HTTPException:
        return RedirectResponse(url="/login", status_code=303)
    
    from app.models.upload_history import UploadHistory
    from app.services.cache_service import get_cache, set_cache
    
    cache_key = "upload_hist"
    cached = get_cache(cache_key)
    if cached:
        uploads = cached
    else:
        try:
            uploads = db.query(UploadHistory).order_by(UploadHistory.timestamp.desc()).all()
        except:
            uploads = db.query(UploadHistory).all()
        
        # If timestamp is missing, use created_at as fallback
        for u in uploads:
            if not u.timestamp and hasattr(u, 'created_at'):
                u.timestamp = u.created_at
        set_cache(cache_key, uploads, ttl_seconds=120)
    
    template = templates.get_template("upload_history.html")
    rendered = template.render({
        "user": current_user,
        "uploads": uploads,
        "error": None
    })
    return HTMLResponse(content=rendered, media_type="text/html")




@app.get("/api/employees/{employee_id}/detail")
async def employee_detail(request: Request, employee_id: int, db: Session = Depends(get_db)):
    try:
        current_user = get_current_user_web(request, db)
    except HTTPException:
        return {"error": "Not authenticated"}
    
    from app.models.employee import Employee
    
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        return {"error": "Employee not found"}
    
    return {
        "id": emp.id,
        "employee_number": emp.employee_number,
        "name": emp.name,
        "email": emp.email,
        "function": emp.function,
        "designation": emp.designation,
        "location": emp.location,
        "date_joined": emp.date_joined.isoformat() if emp.date_joined else None,
        "ssnit_number": emp.ssnit_number,
        "tax_relief": emp.tax_relief,
        "employer_contribution": emp.employer_contribution or 0,
        "bank_name": emp.bank_name,
        "bank_number": emp.bank_number,
        "bank_branch": emp.bank_branch
    }

@app.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="access_token")
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
