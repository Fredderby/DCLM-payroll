/**
 * LoanManagement Component
 * 
 * Replaces the inline script in templates/loans.html with a clean React component.
 * Handles:
 * - Loan calculator (interest, monthly deduction preview)
 * - Employee search autocomplete dropdown
 * - Payment modal (record payment)
 * - Mark loan as defaulted
 * - Progress bar width calculation
 */
(function() {
  'use strict';

  // ===== REACT COMPONENT =====
  const { useState, useEffect, useRef, useCallback, createElement: h } = React;

  /**
   * LoanForm Component - The "Record New Loan" form with autocomplete + calculator
   */
  function LoanForm({ employees }) {
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedEmployee, setSelectedEmployee] = useState('');
    const [showDropdown, setShowDropdown] = useState(false);
    const [bankName, setBankName] = useState('');
    const [loanAmount, setLoanAmount] = useState(0);
    const [interestAmount, setInterestAmount] = useState(0);
    const [monthsToPay, setMonthsToPay] = useState(1);
    const [notes, setNotes] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const searchRef = useRef(null);
    const dropdownRef = useRef(null);

    const matchedEmployees = employees.filter(function(e) {
      var q = searchQuery.toLowerCase().trim();
      if (!q) return false;
      return (e.name && e.name.toLowerCase().includes(q)) ||
             (e.employee_number && e.employee_number.toLowerCase().includes(q));
    });

    var total = loanAmount + interestAmount;
    var monthly = monthsToPay > 0 ? total / monthsToPay : 0;
    var showSummary = loanAmount > 0;

    function selectEmployee(name) {
      setSelectedEmployee(name);
      setSearchQuery(name);
      setShowDropdown(false);
    }

    function handleSubmit(evt) {
      if (!selectedEmployee) {
        evt.preventDefault();
        if (typeof DCLMToast !== 'undefined') {
          DCLMToast.warning('Required', 'Please select an employee first');
        }
        return;
      }
      setSubmitting(true);
    }

    return h('form', { method: 'POST', action: '/loans/add', onSubmit: handleSubmit },
      // Employee & Bank Details header
      h('div', { className: 'text-[0.7rem] uppercase tracking-wider text-blue-800 font-bold pb-2 mb-4 border-b-2 border-blue-100' },
        'Employee & Bank Details'
      ),

      // Employee Search
      h('div', { className: 'mb-4', key: 'employee-field' },
        h('label', { className: 'block text-xs font-medium text-gray-600 mb-1.5' },
          'Employee Name ',
          h('span', { className: 'text-red-400' }, '*')
        ),
        h('div', { className: 'relative' },
          h('input', {
            type: 'text',
            placeholder: 'Type to search...',
            autoComplete: 'off',
            value: searchQuery,
            ref: searchRef,
            onFocus: function() { if (searchQuery.length > 0) setShowDropdown(true); },
            onBlur: function() { setTimeout(function() { setShowDropdown(false); }, 250); },
            onChange: function(e) {
              setSearchQuery(e.target.value);
              setSelectedEmployee('');
              setShowDropdown(e.target.value.length > 0);
            },
            className: 'w-full px-4 py-2.5 rounded-xl border border-gray-300 text-sm focus:ring-2 focus:ring-blue-900/30 focus:border-blue-800 outline-none'
          }),
          h('input', { type: 'hidden', name: 'employee_name', value: selectedEmployee, required: true }),
          showDropdown && matchedEmployees.length > 0 && h('div', {
            ref: dropdownRef,
            className: 'absolute top-full left-0 right-0 mt-1 z-50 bg-white border border-gray-200 rounded-xl shadow-xl max-h-52 overflow-y-auto py-1'
          },
            matchedEmployees.map(function(e, i) {
              return h('div', {
                key: e.name + '-' + i,
                className: 'px-4 py-2.5 cursor-pointer hover:bg-blue-50 border-b border-gray-100 last:border-0 text-sm',
                onMouseDown: function() { selectEmployee(e.name); }
              },
                h('div', { className: 'font-medium text-gray-800' }, e.name),
                h('div', { className: 'text-[0.7rem] text-gray-400' }, '#' + (e.employee_number || ''))
              );
            })
          ),
          showDropdown && matchedEmployees.length === 0 && searchQuery.trim().length > 0 && h('div', {
            className: 'absolute top-full left-0 right-0 mt-1 z-50 bg-white border border-gray-200 rounded-xl shadow-xl py-1'
          },
            h('div', { className: 'px-4 py-3 text-sm text-gray-400 text-center' }, 'No matching employees')
          )
        )
      ),

      // Bank Name
      h('div', { className: 'mb-4' },
        h('label', { className: 'block text-xs font-medium text-gray-600 mb-1.5' }, 'Bank Name'),
        h('input', {
          type: 'text',
          name: 'bank_name',
          value: bankName,
          onChange: function(e) { setBankName(e.target.value); },
          placeholder: 'e.g. GCB Bank',
          className: 'w-full px-4 py-2.5 rounded-xl border border-gray-300 text-sm focus:ring-2 focus:ring-blue-900/30 focus:border-blue-800 outline-none'
        })
      ),

      // Loan Details header
      h('div', { className: 'text-[0.7rem] uppercase tracking-wider text-blue-800 font-bold pb-2 mb-4 mt-6 border-b-2 border-blue-100' },
        'Loan Details'
      ),

      // Loan Amount + Interest grid
      h('div', { className: 'grid grid-cols-2 gap-3 mb-3' },
        h('div', {},
          h('label', { className: 'block text-xs font-medium text-gray-600 mb-1.5' },
            'Loan Amount (GHS) ', h('span', { className: 'text-red-400' }, '*')
          ),
          h('input', {
            type: 'number', step: '0.01', min: '0',
            name: 'loan_amount', required: true,
            value: loanAmount || '',
            onChange: function(e) { setLoanAmount(parseFloat(e.target.value) || 0); },
            placeholder: '0.00',
            className: 'w-full px-4 py-2.5 rounded-xl border border-gray-300 text-sm focus:ring-2 focus:ring-blue-900/30 focus:border-blue-800 outline-none'
          })
        ),
        h('div', {},
          h('label', { className: 'block text-xs font-medium text-gray-600 mb-1.5' }, 'Interest (GHS)'),
          h('input', {
            type: 'number', step: '0.01', min: '0',
            name: 'interest_amount',
            value: interestAmount || '',
            onChange: function(e) { setInterestAmount(parseFloat(e.target.value) || 0); },
            placeholder: '0.00',
            className: 'w-full px-4 py-2.5 rounded-xl border border-gray-300 text-sm focus:ring-2 focus:ring-blue-900/30 focus:border-blue-800 outline-none'
          })
        )
      ),

      // Months + Monthly Deduction grid
      h('div', { className: 'grid grid-cols-2 gap-3 mb-3' },
        h('div', {},
          h('label', { className: 'block text-xs font-medium text-gray-600 mb-1.5' }, 'Months to Pay'),
          h('input', {
            type: 'number', min: '1',
            name: 'months_to_pay', value: monthsToPay,
            onChange: function(e) { setMonthsToPay(parseInt(e.target.value) || 1); },
            className: 'w-full px-4 py-2.5 rounded-xl border border-gray-300 text-sm focus:ring-2 focus:ring-blue-900/30 focus:border-blue-800 outline-none'
          })
        ),
        h('div', {},
          h('label', { className: 'block text-xs font-medium text-gray-600 mb-1.5' }, 'Monthly Deduction'),
          h('input', {
            type: 'text', readOnly: true,
            value: monthly.toFixed(2),
            className: 'w-full px-4 py-2.5 rounded-xl border border-gray-200 bg-gray-50 text-sm font-semibold text-gray-700'
          })
        )
      ),

      // Summary preview
      showSummary && h('div', { className: 'mb-4 p-4 rounded-xl bg-blue-50/80 border border-blue-200' },
        h('div', { className: 'flex justify-between text-sm' },
          h('span', { className: 'text-gray-500' }, 'Total Receivable:'),
          h('span', { className: 'font-bold text-blue-900' }, 'GHS ' + total.toFixed(2))
        ),
        h('div', { className: 'flex justify-between text-sm mt-1' },
          h('span', { className: 'text-gray-500' }, 'Monthly Deduction:'),
          h('span', { className: 'font-bold text-emerald-600' }, 'GHS ' + monthly.toFixed(2))
        )
      ),

      // Notes
      h('div', { className: 'mb-5' },
        h('label', { className: 'block text-xs font-medium text-gray-600 mb-1.5' }, 'Notes (optional)'),
        h('textarea', {
          name: 'notes', rows: '2',
          value: notes,
          onChange: function(e) { setNotes(e.target.value); },
          className: 'w-full px-4 py-2.5 rounded-xl border border-gray-300 text-sm focus:ring-2 focus:ring-blue-900/30 focus:border-blue-800 outline-none resize-none'
        })
      ),

      // Submit button
      h('button', {
        type: 'submit',
        disabled: submitting,
        className: 'w-full py-3 rounded-xl font-semibold text-white shadow-lg shadow-blue-900/20 transition-all hover:shadow-xl hover:brightness-110' + (submitting ? ' opacity-60 cursor-not-allowed' : ''),
        style: { background: 'linear-gradient(135deg, #1a365d, #2a4a7f)' }
      },
        submitting
          ? h('span', {}, h('i', { className: 'fas fa-spinner fa-spin mr-2' }), 'Saving...')
          : h('span', {}, h('i', { className: 'fas fa-save mr-2' }), 'Record Loan')
      )
    );
  }

  /**
   * PaymentModal Component
   */
  function PaymentModal({ isOpen, loanId, employeeName, onClose, onRecorded }) {
    const [amount, setAmount] = useState(0);
    const [submitting, setSubmitting] = useState(false);

    useEffect(function() {
      if (isOpen) setAmount(0);
    }, [isOpen]);

    if (!isOpen) return null;

    function handleSubmit(evt) {
      evt.preventDefault();
      if (amount <= 0) {
        if (typeof DCLMToast !== 'undefined') {
          DCLMToast.warning('Invalid Amount', 'Please enter a payment amount greater than 0');
        }
        return;
      }
      setSubmitting(true);
      var form = evt.target;
      var xhr = new XMLHttpRequest();
      xhr.open('POST', form.action, true);
      xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
      xhr.onload = function() {
        setSubmitting(false);
        if (xhr.status === 303 || xhr.status === 302) {
          window.location.href = '/loans?success=Payment+recorded+successfully';
        } else {
          if (typeof DCLMToast !== 'undefined') {
            DCLMToast.error('Error', 'Failed to record payment');
          } else {
            alert('Failed to record payment');
          }
        }
      };
      xhr.onerror = function() {
        setSubmitting(false);
        if (typeof DCLMToast !== 'undefined') {
          DCLMToast.error('Network Error', 'Failed to connect to server');
        } else {
          alert('Network error');
        }
      };
      xhr.send('payment_amount=' + encodeURIComponent(amount));
    }

    return h('div', {
      className: 'fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm',
      onClick: function(e) { if (e.target === this) onClose(); }
    },
      h('div', { className: 'bg-white rounded-2xl shadow-2xl w-full max-w-sm mx-4 overflow-hidden' },
        h('div', {
          className: 'px-6 py-4 text-white flex items-center justify-between',
          style: { background: 'linear-gradient(135deg, #1a365d, #2a4a7f)' }
        },
          h('h5', { className: 'font-semibold flex items-center gap-2' },
            h('i', { className: 'fas fa-coins' }), ' Record Payment'
          ),
          h('button', { onClick: onClose, className: 'text-white/70 hover:text-white' },
            h('i', { className: 'fas fa-times' })
          )
        ),
        h('form', { method: 'POST', onSubmit: handleSubmit, action: '/loans/' + loanId + '/pay' },
          h('div', { className: 'p-6' },
            h('p', { className: 'text-sm text-gray-500 mb-4' },
              'Recording payment for ',
              h('strong', { className: 'text-gray-800' }, employeeName)
            ),
            h('div', {},
              h('label', { className: 'block text-xs font-medium text-gray-600 mb-1.5' }, 'Payment Amount (GHS)'),
              h('input', {
                type: 'number', step: '0.01', min: '0.01', required: true,
                autoFocus: true,
                value: amount || '',
                onChange: function(e) { setAmount(parseFloat(e.target.value) || 0); },
                placeholder: '0.00',
                className: 'w-full px-4 py-2.5 rounded-xl border border-gray-300 text-sm focus:ring-2 focus:ring-blue-900/30 focus:border-blue-800 outline-none'
              })
            )
          ),
          h('div', { className: 'px-6 py-4 bg-gray-50 flex justify-end gap-3' },
            h('button', {
              type: 'button',
              onClick: onClose,
              className: 'px-5 py-2.5 text-sm font-medium rounded-xl border border-gray-300 text-gray-600 hover:bg-gray-100 transition'
            }, 'Cancel'),
            h('button', {
              type: 'submit',
              disabled: submitting,
              className: 'px-5 py-2.5 text-sm font-medium rounded-xl bg-emerald-600 text-white hover:bg-emerald-700 transition shadow-lg shadow-emerald-600/20' + (submitting ? ' opacity-60 cursor-not-allowed' : '')
            },
              submitting
                ? h('span', {}, h('i', { className: 'fas fa-spinner fa-spin mr-1' }), ' Processing...')
                : h('span', {}, h('i', { className: 'fas fa-check mr-1' }), ' Record Payment')
            )
          )
        )
      )
    );
  }

  /**
   * LoanCard Component - renders a single loan record card with progress bar
   */
  function LoanCard({ loan, onPay, onDefault }) {
    var pct = loan.total_receivable > 0 ? (loan.amount_paid / loan.total_receivable * 100) : 0;
    var barWidth = pct > 100 ? 100 : pct;
    var remainingMonths = (loan.months_to_pay || 0) - (loan.months_paid || 0);
    var isActive = loan.status === 'Active';
    var isCompleted = loan.status === 'Completed';
    var isDefaulted = loan.status === 'Defaulted';

    var ringClass = '';
    if (isCompleted) ringClass = 'ring-1 ring-emerald-300';
    else if (isDefaulted) ringClass = 'ring-1 ring-red-300';

    return h('div', {
      className: 'loan-card rounded-xl bg-white border border-gray-200/60 shadow-sm overflow-hidden ' + ringClass
    },
      // Header
      h('div', {
        className: 'px-5 py-4 flex items-center justify-between',
        style: { background: 'linear-gradient(135deg, #1a365d, #2a4a7f)' }
      },
        h('div', { className: 'text-white' },
          h('h6', { className: 'font-semibold text-sm' }, loan.employee_name),
          h('span', { className: 'text-xs text-white/70' }, loan.bank_name || 'N/A')
        ),
        h('span', {
          className: 'px-2.5 py-1 rounded-full text-xs font-medium ' +
            (isActive ? 'bg-amber-400/20 text-amber-300 border border-amber-400/30' :
             isCompleted ? 'bg-emerald-400/20 text-emerald-300 border border-emerald-400/30' :
             'bg-red-400/20 text-red-300 border border-red-400/30')
        }, loan.status)
      ),

      // Details
      h('div', { className: 'px-5 py-4 space-y-2' },
        h(DetailRow, { label: 'Loan Amount', value: 'GHS ' + numberFormat(loan.loan_amount || 0) }),
        h(DetailRow, { label: 'Interest', value: 'GHS ' + numberFormat(loan.interest_amount || 0) }),
        h(DetailRow, { label: 'Total Receivable', value: 'GHS ' + numberFormat(loan.total_receivable || 0), bold: true, divider: true }),
        h(DetailRow, { label: 'Monthly Deduction', value: 'GHS ' + numberFormat(loan.monthly_deduction || 0) }),
        h(DetailRow, { label: 'Remaining', value: remainingMonths + ' month(s)' }),
        h(DetailRow, { label: 'Amount Paid', value: 'GHS ' + numberFormat(loan.amount_paid || 0), valueClass: 'text-emerald-600 font-medium' }),
        h(DetailRow, { label: 'Balance', value: 'GHS ' + numberFormat(loan.balance || 0), valueClass: 'text-red-600 font-bold', divider: true }),

        // Progress bar
        remainingMonths > 0 && h('div', { className: 'mt-2' },
          h('div', { className: 'flex justify-between text-xs mb-1' },
            h('span', { className: 'text-gray-400' }, 'Progress'),
            h('span', { className: 'font-semibold text-blue-800' }, Math.round(pct * 10) / 10 + '%')
          ),
          h('div', { className: 'h-2 rounded-full bg-gray-200 overflow-hidden' },
            h('div', {
              className: 'h-full rounded-full progress-fill ' + (pct >= 100 ? 'bg-emerald-500' : 'bg-blue-700'),
              style: { width: barWidth + '%' }
            })
          )
        )
      ),

      // Actions
      h('div', { className: 'px-5 py-3 bg-gray-50/80 flex gap-2' },
        isActive && h('button', {
          onClick: function() { onPay(loan.id, loan.employee_name); },
          className: 'flex-1 px-3 py-2 text-xs font-medium rounded-lg border border-emerald-300 text-emerald-700 hover:bg-emerald-50 transition'
        },
          h('i', { className: 'fas fa-coins mr-1' }), ' Pay'
        ),
        isActive && h('button', {
          onClick: function() {
            if (typeof DCLMToast !== 'undefined') {
              DCLMToast.warning('Confirm', 'Mark this loan as Defaulted?', {
                confirmButton: 'Yes, Default',
                onConfirm: function() { onDefault(loan.id); }
              });
            } else {
              if (confirm('Mark this loan as Defaulted?')) onDefault(loan.id);
            }
          },
          className: 'flex-1 px-3 py-2 text-xs font-medium rounded-lg border border-red-300 text-red-600 hover:bg-red-50 transition'
        },
          h('i', { className: 'fas fa-exclamation-triangle mr-1' }), ' Default'
        ),
        h('form', {
          method: 'POST',
          action: '/loans/delete/' + loan.id,
          onSubmit: function(e) {
            if (!confirm('Delete loan for ' + loan.employee_name + '?')) e.preventDefault();
          },
          className: 'flex-1'
        },
          h('button', {
            type: 'submit',
            className: 'w-full px-3 py-2 text-xs font-medium rounded-lg border border-gray-300 text-gray-500 hover:bg-gray-100 transition'
          },
            h('i', { className: 'fas fa-trash' })
          )
        )
      )
    );
  }

  /** DetailRow helper */
  function DetailRow({ label, value, bold, divider, valueClass }) {
    var classes = 'flex justify-between text-sm';
    if (divider) classes += ' border-t border-gray-100 pt-2';

    return h('div', { className: classes },
      h('span', { className: 'text-gray-500' }, label),
      h('span', { className: valueClass || (bold ? 'font-semibold' : '') }, value)
    );
  }

  /** Number formatting helper */
  function numberFormat(num) {
    return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  // ===== MOUNT THE APP =====
  function LoanApp() {
    var employees = [];
    var loans = [];
    try { employees = JSON.parse(document.getElementById('data-loan-employees').textContent); } catch(e) {}
    try { loans = JSON.parse(document.getElementById('data-loan-loans').textContent); } catch(e) {}
    var [paymentModal, setPaymentModal] = useState({ open: false, loanId: null, employeeName: '' });
    var hasLoans = loans.length > 0;

    function openPayment(loanId, empName) {
      setPaymentModal({ open: true, loanId: loanId, employeeName: empName });
    }
    function closePayment() {
      setPaymentModal({ open: false, loanId: null, employeeName: '' });
    }
    function markDefaulted(loanId) {
      fetch('/loans/' + loanId + '/default', { method: 'POST' })
        .then(function(r) { return r.json(); })
        .then(function(data) {
          if (data.success) window.location.reload();
          else if (typeof DCLMToast !== 'undefined') {
            DCLMToast.error('Error', data.message || 'Failed to mark as defaulted');
          } else alert('Error: ' + (data.message || 'Failed'));
        })
        .catch(function(e) {
          if (typeof DCLMToast !== 'undefined') {
            DCLMToast.error('Error', e.message);
          } else alert('Error: ' + e.message);
        });
    }

    return h('div', {},
      // Form + Loan Records grid
      h('div', { className: 'grid grid-cols-1 lg:grid-cols-5 gap-6' },
        // Left: Loan Form
        h('div', { className: 'lg:col-span-2' },
          h('div', { className: 'rounded-2xl glass border border-white/20 shadow-lg overflow-hidden' },
            h('div', { className: 'px-6 py-4 border-b border-gray-200/80 flex items-center gap-2' },
              h('i', { className: 'fas fa-plus-circle text-blue-800' }),
              h('h5', { className: 'font-bold text-sm text-gray-800' }, 'Record New Loan')
            ),
            h('div', { className: 'p-6' },
              h(LoanForm, { employees: employees })
            )
          )
        ),

        // Right: Loan Records
        h('div', { className: 'lg:col-span-3' },
          h('div', { className: 'rounded-2xl glass border border-white/20 shadow-lg overflow-hidden' },
            h('div', { className: 'px-6 py-4 border-b border-gray-200/80 flex items-center justify-between' },
              h('h5', { className: 'font-bold text-sm text-gray-800 flex items-center gap-2' },
                h('i', { className: 'fas fa-file-invoice text-blue-800' }),
                ' Loan Records'
              ),
              h('span', { className: 'px-3 py-1 rounded-full bg-gray-100 text-gray-600 text-xs font-medium' },
                loans.length + ' loans'
              )
            ),
            h('div', { className: 'p-6' },
              hasLoans
                ? h('div', { className: 'grid grid-cols-1 lg:grid-cols-2 gap-4' },
                    loans.map(function(loan) {
                      return h(LoanCard, {
                        key: loan.id,
                        loan: loan,
                        onPay: openPayment,
                        onDefault: markDefaulted
                      });
                    })
                  )
                : h('div', { className: 'text-center py-12' },
                    h('i', { className: 'fas fa-hand-holding-usd text-5xl text-gray-300' }),
                    h('h5', { className: 'mt-4 text-lg font-semibold text-gray-400' }, 'No Loan Records Yet'),
                    h('p', { className: 'text-gray-400 text-sm mt-1' }, 'Record new loans using the form on the left.')
                  )
            )
          )
        )
      ),

      // Payment Modal
      h(PaymentModal, {
        isOpen: paymentModal.open,
        loanId: paymentModal.loanId,
        employeeName: paymentModal.employeeName,
        onClose: closePayment,
        onRecorded: function() { window.location.href = '/loans?success=Payment+recorded+successfully'; }
      })
    );
  }

  // ===== INITIALIZE =====
  // Babel transforms async - DOMContentLoaded may have already fired
  function mountLoans() {
    var mountEl = document.getElementById('loan-app-mount');
    if (!mountEl) return;
    var root = ReactDOM.createRoot(mountEl);
    root.render(h(LoanApp));
  }

  if (document.readyState === "complete" || document.readyState === "interactive") {
    setTimeout(mountLoans, 0);
  } else {
    document.addEventListener("DOMContentLoaded", function() { setTimeout(mountLoans, 0); });
  }

})();
