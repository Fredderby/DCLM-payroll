import pandas as pd
from datetime import datetime
import re


def normalize_col(name: str) -> str:
    """Normalize column name: strip, lowercase, remove punctuation, collapse spaces"""
    name = name.strip().lower()
    # Remove punctuation (keep underscores, letters, digits)
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', '_', name)
    return name.strip('_')


def process_payroll_excel(file_path: str, month: str = None, filename: str = ""):
    """
    Process payroll Excel file with flexible column mapping.
    Supports various column names and extracts payroll data.
    Auto-detects month from filename if not provided.
    """
    if month is None and filename:
        # Auto-detect month from filename
        import re as _re
        month_patterns = [
            (r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})', lambda m: f"{m.group(1)} {m.group(2)}"),
            (r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*\.?\s*(\d{4})', 
             lambda m: {'Jan':'January','Feb':'February','Mar':'March','Apr':'April','May':'May','Jun':'June',
                        'Jul':'July','Aug':'August','Sep':'September','Oct':'October','Nov':'November','Dec':'December'}.get(m.group(1).capitalize(), m.group(1)) + f" {m.group(2)}"),
            (r'(\d{4})[-/_](\d{2})', lambda m: datetime(int(m.group(1)), int(m.group(2)), 1).strftime("%B %Y")),
        ]
        for pattern, formatter in month_patterns:
            match = _re.search(pattern, filename, _re.IGNORECASE)
            if match:
                month = formatter(match)
                break
    
    if month is None:
        month = datetime.now().strftime("%B %Y")

    # Normalize column names - strip punctuation like dots, dashes, etc.
    df.columns = [normalize_col(c) for c in df.columns]

    # Column mappings - support various column names
    # Each value is a list of possible normalized column names to try
    column_mappings = {
        'employee_number': ['employee_number', 'emp_no', 'employee_no', 'staff_id', 'id_number', 'employee_num'],
        'employee_name': ['employee_name', 'name', 'full_name', 'staff_name'],
        'email': ['email', 'email_address', 'employee_email'],
        'function': ['function', 'job_title', 'position', 'designation'],
        'designation': ['designation', 'grade', 'level'],
        'location': ['location', 'department', 'office_location', 'branch'],
        'bank_account': ['bank_account', 'bank_details', 'account_number', 'bank_info'],
        'date_joined': ['date_joined', 'joining_date', 'employment_date'],
        'ssnit_number': ['ssnit_number', 'ssnit', 'ssn', 'national_id'],
        'basic_salary': ['basic_salary', 'basic_pay', 'base_salary', 'salary', 'basic'],
        'meals_monthly': ['meals_monthly', 'meals_allowance', 'meal_allowance'],
        'responsibility_allowance': ['responsibility_allowance', 'resp_allowance', 'responsibility'],
        'cola': ['cola', 'cost_of_living', 'cola_allowance'],
        'leave_allowance': ['leave_allowance', 'leave_pay', 'annual_leave'],
        'other_earnings': ['other_earnings', 'other_allowances', 'miscellaneous', 'bonuses'],
        'paye': ['paye', 'tax', 'income_tax', 'tax_paid'],
        'tithe': ['tithe', '10_tithe', 'tithe_10', '10%_tithe'],
        'future_savings': ['future_savings', 'savings', 'pension_contribution'],
        'other_deductions': ['other_deductions', 'miscellaneous_deductions'],
        'employer_contribution': ['employer_contribution', 'employer_paid', 'company_paid']
    }

    # Map actual columns
    mapped_columns = {}
    for standard_col, possible_cols in column_mappings.items():
        for possible_col in possible_cols:
            if possible_col in df.columns:
                mapped_columns[standard_col] = possible_col
                break

    records = []
    for _, row in df.iterrows():
        try:
            record = {
                'employee_number': row.get(mapped_columns.get('employee_number'), ''),
                'employee_name': row.get(mapped_columns.get('employee_name'), ''),
                'email': row.get(mapped_columns.get('email'), ''),
                'function': row.get(mapped_columns.get('function'), ''),
                'designation': row.get(mapped_columns.get('designation'), ''),
                'location': row.get(mapped_columns.get('location'), ''),
                'bank_account': row.get(mapped_columns.get('bank_account'), ''),
                'date_joined': row.get(mapped_columns.get('date_joined'), None),
                'ssnit_number': row.get(mapped_columns.get('ssnit_number'), ''),
                'month': month,
                # Earnings
                'basic_salary': float(row.get(mapped_columns.get('basic_salary'), 0)) if mapped_columns.get('basic_salary') else 0,
                'meals_monthly': float(row.get(mapped_columns.get('meals_monthly'), 0)) if mapped_columns.get('meals_monthly') else 0,
                'responsibility_allowance': float(row.get(mapped_columns.get('responsibility_allowance'), 0)) if mapped_columns.get('responsibility_allowance') else 0,
                'cola': float(row.get(mapped_columns.get('cola'), 0)) if mapped_columns.get('cola') else 0,
                'leave_allowance': float(row.get(mapped_columns.get('leave_allowance'), 0)) if mapped_columns.get('leave_allowance') else 0,
                'other_earnings': float(row.get(mapped_columns.get('other_earnings'), 0)) if mapped_columns.get('other_earnings') else 0,
                # Deductions
                'paye': float(row.get(mapped_columns.get('paye'), 0)) if mapped_columns.get('paye') else 0,
                'tithe': float(row.get(mapped_columns.get('tithe'), 0)) if mapped_columns.get('tithe') else 0,
                'future_savings': float(row.get(mapped_columns.get('future_savings'), 0)) if mapped_columns.get('future_savings') else 0,
                'other_deductions': float(row.get(mapped_columns.get('other_deductions'), 0)) if mapped_columns.get('other_deductions') else 0,
                'employer_contribution': float(row.get(mapped_columns.get('employer_contribution'), 0)) if mapped_columns.get('employer_contribution') else 0,
            }
            records.append(record)
        except Exception as e:
            print(f"Error processing row: {e}")
            continue

    return records