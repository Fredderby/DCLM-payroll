import pandas as pd
from datetime import datetime
import re


def normalize_col(name: str) -> str:
    """Normalize column name: strip, lowercase, remove punctuation, collapse spaces"""
    if not isinstance(name, str):
        name = str(name)
    name = name.strip().lower()
    # Remove punctuation (keep underscores, letters, digits)
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', '_', name)
    return name.strip('_')


def process_payroll_excel(file_path: str, month: str = None, filename: str = "", staff_category: str = None):
    """
    Process payroll Excel/CSV file with flexible column mapping.
    Supports various column names and extracts payroll data.
    Auto-detects month from filename if not provided.
    
    Returns a list of record dictionaries.
    Raises ValueError with a descriptive message on failure.
    """
    import os as _os
    
    # Validate file exists
    if not _os.path.exists(file_path):
        raise ValueError("File not found at the specified path.")
    
    # Validate file extension
    ext = _os.path.splitext(file_path)[1].lower()
    if ext not in ('.xlsx', '.xls', '.csv'):
        raise ValueError(f"Unsupported file type: '{ext}'. Only .xlsx and .csv files are supported.")
    
    # Auto-detect month from filename
    if month is None and filename:
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

    # Read file into DataFrame
    try:
        if ext == '.csv':
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
    except Exception as e:
        raise ValueError(f"Could not read the file. Please ensure it is a valid {ext.upper()} file. Error: {str(e)[:100]}")
    
    # Validate DataFrame is not empty
    if df is None or df.empty:
        raise ValueError("The uploaded file is empty. Please upload a file with data.")
    
    # Validate at least one row of data (excluding header)
    if len(df) == 0:
        raise ValueError("The uploaded file contains a header but no data rows.")
    
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
        'date_joined': ['date_joined', 'joining_date', 'employment_date', 'date joined', 'date_of_joining', 'start_date', 'doj', 'joined_date'],
        'ssnit_number': ['ssnit_number', 'ssnit', 'ssn', 'national_id'],
        # Pastoral earnings
        'basic_salary': ['basic_salary', 'basic_pay', 'base_salary', 'salary', 'basic'],
        'meals_monthly': ['meals_monthly', 'meals_allowance', 'meal_allowance'],
        'responsibility_allowance': ['responsibility_allowance', 'resp_allowance', 'responsibility'],
        'cola': ['cola', 'cost_of_living', 'cola_allowance'],
        'leave_allowance': ['leave_allowance', 'leave_pay', 'annual_leave'],
        'other_earnings': ['other_earnings', 'other_allowances', 'miscellaneous', 'bonuses'],
        # Non-Pastoral earnings
        'monthly_basic_salary': ['monthly_basic_salary', 'monthly_basic_pay', 'monthly_basic'],
        'rent_monthly': ['rent_monthly', 'rent_allowance', 'housing_allowance', 'rent'],
        'utility_monthly': ['utility_monthly', 'utility_allowance', 'utilities', 'utility'],
        'transport_monthly': ['transport_monthly', 'transport_allowance', 'transport', 'travel_allowance'],
        # Deductions
        'paye': ['paye', 'tax', 'income_tax', 'tax_paid'],
        'tithe': ['tithe', '10_tithe', 'tithe_10', '10%_tithe'],
        'future_savings': ['future_savings', 'savings', 'pension_contribution'],
        'other_deductions': ['other_deductions', 'miscellaneous_deductions'],
        # PF 8% deduction (for both Pastoral & Non-Pastoral) - Active field
        'pf_eight_percent': ['pf_eight_percent', 'pf_8', 'pf_8%', 'pf_8_percent', 'pension_fund_8%', 'pension_fund_8', 'pension_fund_8_percent', 'employee_pf', 'pension_fund', 'employee_pension_fund', 'employee_pf_8'],
        'ssnit_deduction': ['ssnit_deduction', 'ssnit', 'ssnit_55', 'ssnit_5_5', 'ssnit_5.5', 'ssnit_5.5%', 'ssnit%'],
    }

    # Build column mapping: for each standard column name, find the actual column in df
    mapped_columns = {}
    for standard_col, possible_cols in column_mappings.items():
        for possible_col in possible_cols:
            if possible_col in df.columns:
                mapped_columns[standard_col] = possible_col
                break

    # Validate that a required column (employee_name) exists
    if 'employee_name' not in mapped_columns:
        raise ValueError(
            "Invalid template structure: Could not find an 'Employee Name' column. "
            "Please use the correct payroll template for the staff category."
        )

    # Use explicitly provided staff_category, default to pastoral
    staff_category = staff_category or "pastoral"

    records = []
    for _, row in df.iterrows():
        try:
            # Non-Pastoral: use monthly_basic_salary -> basic_salary
            np_basic = float(row.get(mapped_columns.get('monthly_basic_salary'), 0)) if mapped_columns.get('monthly_basic_salary') else None
            record = {
                'employee_number': str(row.get(mapped_columns.get('employee_number'), '') or ''),
                'employee_name': str(row.get(mapped_columns.get('employee_name'), '') or ''),
                'email': str(row.get(mapped_columns.get('email'), '') or ''),
                'function': str(row.get(mapped_columns.get('function'), '') or ''),
                'designation': str(row.get(mapped_columns.get('designation'), '') or ''),
                'location': str(row.get(mapped_columns.get('location'), '') or ''),
                'bank_account': str(row.get(mapped_columns.get('bank_account'), '') or ''),
                'date_joined': row.get(mapped_columns.get('date_joined'), None),
                'ssnit_number': str(row.get(mapped_columns.get('ssnit_number'), '') or ''),
                'month': month,
                'staff_category': staff_category,
                # Earnings
                'basic_salary': float(row.get(mapped_columns.get('basic_salary'), np_basic or 0)) if (mapped_columns.get('basic_salary') or np_basic is not None) else 0,
                'meals_monthly': float(row.get(mapped_columns.get('meals_monthly'), 0)) if mapped_columns.get('meals_monthly') else 0,
                'responsibility_allowance': float(row.get(mapped_columns.get('responsibility_allowance'), 0)) if mapped_columns.get('responsibility_allowance') else 0,
                'cola': float(row.get(mapped_columns.get('cola'), 0)) if mapped_columns.get('cola') else 0,
                'leave_allowance': float(row.get(mapped_columns.get('leave_allowance'), 0)) if mapped_columns.get('leave_allowance') else 0,
                'other_earnings': float(row.get(mapped_columns.get('other_earnings'), 0)) if mapped_columns.get('other_earnings') else 0,
                # Non-Pastoral specific earnings
                'rent_monthly': float(row.get(mapped_columns.get('rent_monthly'), 0)) if mapped_columns.get('rent_monthly') else 0,
                'utility_monthly': float(row.get(mapped_columns.get('utility_monthly'), 0)) if mapped_columns.get('utility_monthly') else 0,
                'transport_monthly': float(row.get(mapped_columns.get('transport_monthly'), 0)) if mapped_columns.get('transport_monthly') else 0,
                # Deductions
                'paye': float(row.get(mapped_columns.get('paye'), 0)) if mapped_columns.get('paye') else 0,
                'tithe': float(row.get(mapped_columns.get('tithe'), 0)) if mapped_columns.get('tithe') else 0,
                'future_savings': float(row.get(mapped_columns.get('future_savings'), 0)) if mapped_columns.get('future_savings') else 0,
                'other_deductions': float(row.get(mapped_columns.get('other_deductions'), 0)) if mapped_columns.get('other_deductions') else 0,
                # PF 8% deduction (for both Pastoral & Non-Pastoral) - Active field
                'pf_eight_percent': float(row.get(mapped_columns.get('pf_eight_percent'), 0)) if mapped_columns.get('pf_eight_percent') else 0,
                'ssnit_deduction': float(row.get(mapped_columns.get('ssnit_deduction'), 0)) if mapped_columns.get('ssnit_deduction') else 0,
            }
            records.append(record)
        except Exception as e:
            print(f"Error processing row: {e}")
            continue

    if not records:
        raise ValueError("No valid records could be extracted from the file. Check that the file contains data and uses the correct template format.")

    return records