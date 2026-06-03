from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.excel_service import process_payroll_excel
from app.services.payroll_service import create_payroll_record
from app.models.employee import Employee
import tempfile
import os

router = APIRouter()

@router.post("/upload")
def upload_payroll(file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not file.filename.endswith(('.xlsx', '.csv')):
        raise HTTPException(status_code=400, detail="Only .xlsx and .csv files allowed")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name
    
    try:
        records = process_payroll_excel(tmp_path)
        processed = 0
        errors = []
        
        for record in records:
            try:
                # Check if employee exists, else create
                employee = db.query(Employee).filter(
                    (Employee.email == record['email']) | 
                    (Employee.employee_number == record['employee_number'])
                ).first()
                
                if not employee:
                    employee = Employee(
                        employee_number=record['employee_number'],
                        name=record['employee_name'],
                        email=record['email'],
                        function=record.get('function', ''),
                        designation=record.get('designation', ''),
                        location=record.get('location', '')
                    )
                    db.add(employee)
                    db.commit()
                    db.refresh(employee)
                
                create_payroll_record(db, employee, record)
                processed += 1
            except Exception as e:
                errors.append(f"Error processing {record.get('employee_name', 'Unknown')}: {str(e)}")
        
        return {"message": f"Processed {processed} records", "processed": processed, "errors": errors}
    finally:
        os.unlink(tmp_path)