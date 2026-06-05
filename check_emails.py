import sys
sys.path.insert(0, '.')
from app.core.database import SessionLocal
from app.models.payroll import PayrollRecord
from app.models.employee import Employee

db = SessionLocal()

payroll_names = set()
for p in db.query(PayrollRecord).order_by(PayrollRecord.employee_name).all():
    payroll_names.add(p.employee_name)

emp_names = set()
for e in db.query(Employee).all():
    emp_names.add(e.name)

unmatched = payroll_names - emp_names
matched = payroll_names & emp_names
print('Total payroll names:', len(payroll_names))
print('Total employee names:', len(emp_names))
print('Matched:', len(matched))
print('Unmatched:', len(unmatched))
if unmatched:
    print('Unmatched names:')
    for n in sorted(unmatched)[:30]:
        print('  "' + n + '"')
db.close()
