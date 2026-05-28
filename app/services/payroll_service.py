from app.models.payroll import PayrollRecord
from app.models.employee import Employee
from sqlalchemy.orm import Session
from datetime import datetime
import os


def calculate_payroll_totals(earnings_dict, deductions_dict):
    """Calculate totals for earnings and deductions"""
    total_earnings = sum([
        earnings_dict.get('basic_salary', 0),
        earnings_dict.get('meals_monthly', 0),
        earnings_dict.get('responsibility_allowance', 0),
        earnings_dict.get('cola', 0),
        earnings_dict.get('leave_allowance', 0),
        earnings_dict.get('other_earnings', 0)
    ])

    total_deductions = sum([
        deductions_dict.get('paye', 0),
        deductions_dict.get('tithe', 0),
        deductions_dict.get('future_savings', 0),
        deductions_dict.get('other_deductions', 0)
    ])

    net_salary = total_earnings - total_deductions

    return total_earnings, total_deductions, net_salary


def create_payroll_record(db: Session, employee_id: int, payroll_data: dict):
    """Create a comprehensive payroll record"""
    # Look up employee name for the payroll record
    employee_name = ""
    if employee_id:
        emp = db.query(Employee).filter(Employee.id == employee_id).first()
        if emp and emp.name:
            employee_name = emp.name
    # Fall back to the name from payroll_data if available
    if not employee_name:
        employee_name = payroll_data.get('employee_name', '')

    earnings = {
        'basic_salary': payroll_data.get('basic_salary', 0),
        'meals_monthly': payroll_data.get('meals_monthly', 0),
        'responsibility_allowance': payroll_data.get('responsibility_allowance', 0),
        'cola': payroll_data.get('cola', 0),
        'leave_allowance': payroll_data.get('leave_allowance', 0),
        'other_earnings': payroll_data.get('other_earnings', 0),
    }

    deductions = {
        'paye': payroll_data.get('paye', 0),
        'tithe': payroll_data.get('tithe', 0),
        'future_savings': payroll_data.get('future_savings', 0),
        'other_deductions': payroll_data.get('other_deductions', 0),
    }

    total_earnings, total_deductions, net_salary = calculate_payroll_totals(earnings, deductions)

    record = PayrollRecord(
        employee_name=employee_name,
        month=payroll_data.get('month', datetime.now().strftime("%B %Y")),
        basic_salary=earnings['basic_salary'],
        meals_monthly=earnings['meals_monthly'],
        responsibility_allowance=earnings['responsibility_allowance'],
        cola=earnings['cola'],
        leave_allowance=earnings['leave_allowance'],
        other_earnings=earnings['other_earnings'],
        total_earnings=total_earnings,
        paye=deductions['paye'],
        tithe=deductions['tithe'],
        future_savings=deductions['future_savings'],
        other_deductions=deductions['other_deductions'],
        total_deductions=total_deductions,
        net_salary=net_salary,
        employer_contribution=payroll_data.get('employer_contribution', 0)
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def number_to_words(n):
    """Convert whole number to words with hyphenated compound numbers (21-99)."""
    if n is None:
        return "Zero"

    ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine']
    tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']
    teens = ['Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen',
             'Seventeen', 'Eighteen', 'Nineteen']

    def convert_below_thousand(num):
        if num == 0:
            return ''
        elif num < 10:
            return ones[num]
        elif num < 20:
            return teens[num - 10]
        elif num < 100:
            hyphen = '-' if num % 10 != 0 else ''
            return tens[num // 10] + hyphen + (ones[num % 10] if num % 10 != 0 else '')
        else:
            remainder = num % 100
            return (ones[num // 100] + ' Hundred' +
                    (' and ' + convert_below_thousand(remainder) if remainder != 0 else ''))

    if n == 0:
        return 'Zero'

    billions = n // 1000000000
    millions = (n % 1000000000) // 1000000
    thousands = (n % 1000000) // 1000
    remainder = n % 1000

    result = ''
    if billions > 0:
        result += convert_below_thousand(billions) + ' Billion '
    if millions > 0:
        result += convert_below_thousand(millions) + ' Million '
    if thousands > 0:
        result += convert_below_thousand(thousands) + ' Thousand '
    if remainder > 0:
        result += convert_below_thousand(remainder)

    return result.strip()


def convert_cents_to_words(cents):
    """Convert cents/pesewas (0-99) to hyphenated words."""
    if cents is None or cents < 1:
        return ""
    ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine']
    tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']
    teens = ['Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen',
             'Seventeen', 'Eighteen', 'Nineteen']

    if cents < 10:
        return ones[cents]
    elif cents < 20:
        return teens[cents - 10]
    else:
        hyphen = '-' if cents % 10 != 0 else ''
        return tens[cents // 10] + hyphen + (ones[cents % 10] if cents % 10 != 0 else '')


def amount_to_words(amount):
    """
    Convert monetary amount to full words string.

    Format: "<Cedis words> Ghana Cedis and <Pesewas words> Pesewas Only"
    Example: 7489.80 -> "Seven Thousand Four Hundred and Eighty-Nine Ghana Cedis and Eighty Pesewas Only"
    Example: 1000.00 -> "One Thousand Ghana Cedis Only"
    """
    if amount is None:
        amount = 0.0
    ghs = int(amount)
    pesewas = int(round((amount - ghs) * 100))

    ghs_words = number_to_words(ghs)

    if ghs_words == "Zero" and pesewas == 0:
        return "Zero Ghana Cedis Only"

    result = ghs_words + " Ghana Cedis"
    if pesewas > 0:
        pesewas_word = convert_cents_to_words(pesewas)
        result += " and " + pesewas_word + " Pesewas"
    result += " Only"
    return result
