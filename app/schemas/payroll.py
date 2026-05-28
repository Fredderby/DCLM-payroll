from pydantic import BaseModel
from typing import List

class PayrollRecordBase(BaseModel):
    employee_name: str
    email: str
    basic_salary: float
    allowances: float
    deductions: float

class PayrollRecordCreate(PayrollRecordBase):
    pass

class PayrollRecord(PayrollRecordBase):
    id: int
    net_salary: float

    class Config:
        from_attributes = True

class PayrollUploadResponse(BaseModel):
    message: str
    processed: int
    errors: List[str]