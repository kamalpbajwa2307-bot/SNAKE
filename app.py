import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, render_template_string, request, redirect, url_for, session, flash, send_file
from datetime import datetime, timedelta, timezone
import os
import math
import json
import sqlite3

from werkzeug.security import generate_password_hash, check_password_hash
import time, uuid, csv
from io import StringIO

# ==========================================
# 1. CONFIGURATION
# ==========================================
app = Flask(__name__)
app.secret_key = 'secure_key_v46_search_approvedby_restored'

# --- AUTO LOGOUT CONFIGURATION ---
app.permanent_session_lifetime = timedelta(minutes=15)

# --- FIREBASE SETUP START ---
# Fetching the variable from Railway Environment Variables
firebase_creds_json = os.getenv('FIREBASE_CONFIG')

db = None
if firebase_creds_json:
    try:
        cred_dict = json.loads(firebase_creds_json)
        cred = credentials.Certificate(cred_dict)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("Firebase successfully initialized!")
    except Exception as e:
        print(f"Error parsing JSON or initializing Firebase: {e}")
else:
    print("CRITICAL ERROR: FIREBASE_CONFIG environment variable not found!")

# --- HTML TEMPLATES & CSS ---

BASE_STYLE = '''
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
    :root { --primary: #4f46e5; --primary-hover: #4338ca; --success: #10b981; --success-bg: #d1fae5; --success-text: #065f46; --danger: #ef4444; --danger-bg: #fee2e2; --danger-text: #991b1b; --warning: #f59e0b; --dark: #1f2937; --gray: #f3f4f6; --text: #374151; --border: #e5e7eb; }
    body { font-family: 'Poppins', sans-serif; background-color: #f8fafc; color: var(--text); margin: 0; padding: 0; }
    .container { width: 98%; max-width: 1400px; margin: 0 auto; padding: 20px 10px; }
    h1, h2, h3 { color: var(--dark); font-weight: 600; margin-top: 0; }
    .navbar { display: flex; gap: 15px; background: linear-gradient(135deg, #4f46e5, #3b82f6); padding: 15px 30px; border-radius: 12px; margin-bottom: 25px; align-items: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); flex-wrap: wrap;}
    .navbar a { color: white; text-decoration: none; padding: 8px 16px; border-radius: 8px; font-weight: 500; transition: 0.3s; background: rgba(255,255,255,0.1); }
    .navbar a:hover { background: rgba(255,255,255,0.2); transform: translateY(-1px); }
    .navbar .active { background: rgba(255,255,255,0.25); box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .navbar .logout { margin-left: auto; background: var(--danger); }
    .navbar .logout:hover { background: #dc2626; }
    .card { background: #ffffff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); margin-bottom: 25px; border: 1px solid var(--border); overflow-x: auto;}
    .balance-card { background: linear-gradient(to right, #ffffff, #f8fafc); text-align: center; border-left: 6px solid var(--primary); padding: 20px; }
    .balance-amount { font-size: 2.8em; font-weight: 700; margin-top: 10px; letter-spacing: -1px; }
    .form-group { margin-bottom: 12px; display: flex; flex-direction: column; }
    label { font-weight: 600; margin-bottom: 5px; font-size: 0.85em; color: #4b5563; }
    input, select { padding: 10px 12px; font-size: 0.95em; border: 1px solid #d1d5db; border-radius: 8px; transition: all 0.2s ease; font-family: inherit; width: 100%; box-sizing: border-box; }
    input:focus, select:focus { outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.15); }
    button, .btn { background-color: var(--primary); color: white; border: none; cursor: pointer; font-weight: 600; padding: 10px 18px; border-radius: 8px; transition: all 0.2s ease; font-family: inherit; text-decoration: none; display: inline-block; text-align: center; }
    button:hover, .btn:hover { background-color: var(--primary-hover); transform: translateY(-1px); }
    .btn-success { background-color: var(--success); } .btn-danger { background-color: var(--danger); }
    .btn-outline { background-color: transparent; border: 2px dashed #cbd5e1; color: var(--text); }
    .btn-sm { padding: 6px 12px; font-size: 0.85em; }
    .ledger-container { display: flex; gap: 20px; flex-wrap: wrap; align-items: flex-start; }
    .ledger-col { flex: 1; min-width: 48%; background: #fff; border-radius: 12px; border: 1px solid var(--border); overflow-x: auto; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
    .ledger-title { margin: 0; padding: 15px; text-align: center; font-size: 1.05em; border-bottom: 1px solid var(--border); background-color: #f8fafc; text-transform: uppercase; }
    table { width: 100%; border-collapse: collapse; }
    th, td { border-bottom: 1px solid var(--border); padding: 10px 12px; text-align: left; font-size: 0.88em; vertical-align: middle; }
    th { background-color: #f1f5f9; color: #475569; font-weight: 600; font-size: 0.85em; text-transform: uppercase; }
    tr:hover td { background-color: #f8fafc; }
    .badge { padding: 4px 10px; border-radius: 999px; font-weight: 600; font-size: 0.8em; display: inline-block; }
    .badge-in { background-color: var(--success-bg); color: var(--success-text); }
    .badge-out { background-color: var(--danger-bg); color: var(--danger-text); }
    .badge-memo { background-color: #e5e7eb; color: #374151; border: 1px solid #d1d5db; }
    .badge-pending { background-color: #fef08a; color: #92400e; border: 1px solid #fde047; }
    .badge-mode { background-color: #e0e7ff; color: #3730a3; font-size: 0.8em; margin-bottom: 4px; border: 1px solid #c7d2fe; }
    .flex-row { display: flex; gap: 15px; flex-wrap: wrap; align-items: flex-end; }
    .flex-1 { flex: 1; }
    .express-entry { background: #e0e7ff; border: 2px solid #818cf8; padding: 20px; border-radius: 12px; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .transfer-entry { background: #e0f2fe; border: 2px solid #38bdf8; padding: 20px; border-radius: 12px; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 25px; }
    .stat-card { background: #fff; padding: 20px; border-radius: 12px; border: 1px solid var(--border); text-align: center; }
    .stat-card h4 { color: #6b7280; margin: 0 0 8px 0; font-size: 0.85em; text-transform: uppercase; }
    .stat-card .value { font-size: 1.6em; font-weight: 700; }

    #splash-screen { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(135deg, #4f46e5, #3b82f6); z-index: 9999; display: flex; flex-direction: column; align-items: center; justify-content: center; color: white; transition: opacity 0.5s ease; }
    .splash-firm { font-size: 3.5em; font-weight: 700; margin-bottom: 10px; animation: popIn 0.8s ease; text-transform: uppercase; letter-spacing: 2px;}
    .splash-user { font-size: 1.5em; font-weight: 300; animation: popIn 1.2s ease; }
    @keyframes popIn { 0% { opacity: 0; transform: translateY(20px); } 100% { opacity: 1; transform: translateY(0); } }

    @media print { .no-print, .navbar, .card form, .express-entry, .transfer-entry, button, select { display: none !important; } body { background: white; color: black; } .card { box-shadow: none; border: none; margin: 0; padding: 0; } }
</style>
<script>
    let isDirty = false;
    function setAutoDateTime() {
        const now = new Date();
        const dateString = new Date(now.getTime() - (now.getTimezoneOffset() * 60000)).toISOString().split('T')[0];
        const timeString = now.toTimeString().slice(0,5);
        document.querySelectorAll('input[type="date"]').forEach(el => { if(!el.value) el.value = dateString; });
        document.querySelectorAll('input[type="time"]').forEach(el => { if(!el.value) el.value = timeString; });
    }
    function toggleNature() {
        const nature = document.getElementById('txn_nature')?.value;
        const pLabel = document.getElementById('primary_label');
        if(!pLabel) return;
        if(nature === 'slip_in') { pLabel.innerHTML = "Ledger Account <small>(- Deducts User Balance)</small>"; pLabel.style.color = "var(--danger)"; }
        else if(nature === 'advance') { pLabel.innerHTML = "Ledger Account <small>(+ Adds Positive Balance)</small>"; pLabel.style.color = "var(--primary)"; }
        else if(nature === 'receive_cash') { pLabel.innerHTML = "Ledger Account <small>(- Deducts User Balance)</small>"; pLabel.style.color = "var(--success)"; }
    }
    function checkNewAccount(sel) {
        const newAcc = document.getElementById('new_account_name');
        if(sel.value === 'new_dasti' || sel.value === 'new_person') {
            newAcc.style.display = 'block'; newAcc.required = true;
        } else { newAcc.style.display = 'none'; newAcc.required = false; }
    }
    function toggleCustomCategory(selectElem) {
        const customInput = selectElem.nextElementSibling;
        if (selectElem.value === 'Other') { customInput.style.display = 'block'; customInput.required = true; }
        else { customInput.style.display = 'none'; customInput.required = false; }
    }
    function addRow(catOptions) {
        const html = `<tr>
            <td style="width: 25%; padding: 10px;"><select name="category[]" onchange="toggleCustomCategory(this)" required style="margin-bottom: 0;">${catOptions}<option value="Other">Other (Type Below)...</option></select><input type="text" name="custom_category[]" placeholder="Custom Category..." style="display:none; margin-top: 8px; border-color: var(--primary);"></td>
            <td style="width: 50%; padding: 10px;"><input type="text" name="description[]" placeholder="Bill No. / Detail" required></td>
            <td style="width: 20%; padding: 10px;"><input type="number" step="0.01" min="0" name="amount[]" placeholder="Amount (₹)" value="0" required></td>
            <td style="width: 5%; text-align: center; vertical-align: middle; padding: 10px;"><button type="button" onclick="this.closest('tr').remove()" style="background: var(--danger); padding: 8px 12px; font-size: 0.9em;">✕</button></td>
        </tr>`;
        if(document.getElementById('entryBody')) document.getElementById('entryBody').insertAdjacentHTML('beforeend', html);
    }
    function initForm(catOptions) {
        setAutoDateTime(); toggleNature();
        if(document.getElementById('entryBody') && document.getElementById('entryBody').children.length === 0) { addRow(catOptions); }
        document.querySelectorAll('form').forEach(f => { f.addEventListener('change', () => isDirty = true); f.addEventListener('submit', () => isDirty = false); });
        window.addEventListener('beforeunload', function(e) { if(isDirty) { e.preventDefault(); e.returnValue = 'You have unsaved entries. Exit without saving?'; } });
    }
</script>
'''

SPLASH_HTML = '''
<div id="splash-screen" class="no-print">
    <div class="splash-firm">{{ session.get('firm_name', 'FIRM') }}</div>
    <div class="splash-user">Welcome, {{ session.get('username', 'User') }}</div>
</div>
<script>
    if (sessionStorage.getItem('splashShown')) {
        document.getElementById('splash-screen').style.display = 'none';
    } else {
        window.addEventListener('load', function() {
            setTimeout(function() {
                const splash = document.getElementById('splash-screen');
                if(splash) {
                    splash.style.opacity = '0';
                    setTimeout(() => { splash.style.display = 'none'; }, 500);
                    sessionStorage.setItem('splashShown', 'true');
                }
            }, 1800);
        });
    }
</script>
'''

NAVBAR_HTML = SPLASH_HTML + '''<div class="navbar no-print">
    <a href="/" class="{% if active_page == 'home' %}active{% endif %}">⚡ Dash</a>
    <a href="/main_ledger" class="{% if active_page == 'main_ledger' %}active{% endif %}">🏢 Main</a>
    <a href="/persons" class="{% if active_page == 'persons' %}active{% endif %}">👥 Ledgers</a>
    <a href="/dasti_ledger" class="{% if active_page == 'dasti_ledger' %}active{% endif %}" style="background: rgba(14, 165, 233, 0.2);">💸 Dasti</a>
    <a href="/reports" class="{% if active_page == 'reports' %}active{% endif %}" style="background: rgba(16, 185, 129, 0.2); color: #065f46;">📊 Reports</a>
    {% if session.get('can_approve') == 1 %}<a href="/approvals" class="{% if active_page == 'approvals' %}active{% endif %}" style="background: var(--warning);">✅ Apprv</a>{% endif %}
    <a href="/trash" class="{% if active_page == 'trash' %}active{% endif %}" style="background: rgba(239, 68, 68, 0.2); color: #991b1b;">🗑️ Trash</a>
    {% if session.get('role') == 'superadmin' %}
        <a href="/manage_users" class="{% if active_page == 'users' %}active{% endif %}" style="background: #8b5cf6;">⚙️ Users</a>
        <a href="/download_cash_json" style="background: #f97316; color: white;">🔥 Get cash.json</a>
    {% endif %}
    <span style="color: rgba(255,255,255,0.9); margin-left: auto; font-size: 0.9em; font-weight: 500;">User: <strong>{{ username }}</strong> <small>({{ session.get('role')|title }})</small></span>
    <a href="/logout" class="logout" style="padding: 6px 12px; font-size:0.9em;" onclick="sessionStorage.removeItem('splashShown');">Logout</a>
</div>'''

REGISTER_TEMPLATE = '''<!DOCTYPE html><html><head><title>Setup</title>''' + BASE_STYLE + '''</head><body><div class="container"><div class="card" style="max-width: 450px; margin: 80px auto; text-align: center;">
    <h2 style="color: var(--primary);">Setup Superadmin</h2>
    <form action="/register" method="POST" style="text-align: left;">
        <div class="form-group"><label>Firm Name</label><input type="text" name="firm_name" required></div>
        <div class="form-group"><label>Opening Cash Book Balance (₹)</label><input type="number" step="0.01" min="0" name="opening_balance" value="0" required></div>
        <div class="form-group"><label>Superadmin Username</label><input type="text" name="username" required></div>
        <div class="form-group"><label>Password</label><input type="password" name="password" required></div>
        <button type="submit" style="width: 100%;">Initialize Firm Account</button>
    </form></div></div></body></html>'''

LOGIN_TEMPLATE = '''<!DOCTYPE html><html><head><title>Login</title>''' + BASE_STYLE + '''</head><body><div class="container"><div class="card" style="max-width: 400px; margin: 100px auto; text-align: center;"><h2>Welcome Back</h2><form action="/login" method="POST" style="text-align: left;"><div class="form-group"><label>Username</label><input type="text" name="username" required></div><div class="form-group"><label>Password</label><input type="password" name="password" required></div><button type="submit" style="width: 100%;">Secure Login</button></form></div></div></body></html>'''

TRASH_TEMPLATE = '''<!DOCTYPE html><html><head><title>Trash / Recycle Bin</title>''' + BASE_STYLE + '''</head><body>
    <div class="container">''' + NAVBAR_HTML + '''
        <div class="card" style="padding: 0;">
            <h3 style="padding: 15px 20px; margin: 0; background: #fee2e2; border-bottom: 1px solid var(--border); font-size: 1.2em; color: #991b1b;">🗑️ Deleted Vouchers & Entries (Trash)</h3>
            <table style="width: 100%; border: none;"><tr><th style="padding-left: 20px;">Date & Time</th><th>Category / Detail</th><th style="text-align: right;">Amount</th><th style="text-align: center;">Action</th></tr>
                {% for t in trashed %}<tr>
                    <td style="padding-left: 20px;"><span style="font-weight: 500;">{{ t.date }}</span><br><span style="font-size: 0.85em; color: #6b7280;">{{ t.time }}</span></td>
                    <td><span class="badge badge-mode">{{ t.category }}</span><br><span style="white-space: pre-wrap;">{{ t.description }}</span></td>
                    <td style="text-align: right;"><strong>₹{{ "{:,.2f}".format(t.amount) }}</strong></td>
                    <td style="text-align: center;">
                        <a href="/restore_voucher/{{ t.link_id }}" class="btn btn-sm btn-success" onclick="return confirm('Restore this transaction?');">♻️ Restore</a>
                        <a href="/hard_delete_voucher/{{ t.link_id }}" class="btn btn-sm" style="background:#dc2626; color:white; margin-left:5px;" onclick="return confirm('Permanently delete? This cannot be undone.');">🔥 Delete Forever</a>
                    </td>
                </tr>{% else %}<tr><td colspan="4" style="text-align:center; color:#9ca3af; padding: 40px;">Trash is empty.</td></tr>{% endfor %}
            </table>
        </div>
    </div></body></html>'''

REPORTS_TEMPLATE = '''<!DOCTYPE html><html><head><title>Dynamic Reports</title>''' + BASE_STYLE + '''</head><body>
    <div class="container">''' + NAVBAR_HTML + '''
        <div class="card no-print" style="padding: 25px; margin-bottom: 25px;">
            <h3 style="margin-bottom: 15px; font-size: 1.3em;">📊 Generate Report</h3>
            <form method="GET" action="/reports" style="display: flex; gap: 15px; flex-wrap: wrap; align-items: flex-end;">
                <div class="form-group flex-1" style="min-width: 150px;"><label>From Date</label><input type="date" name="start_date" value="{{ start_date }}"></div>
                <div class="form-group flex-1" style="min-width: 150px;"><label>To Date</label><input type="date" name="end_date" value="{{ end_date }}"></div>
                <div class="form-group flex-1" style="min-width: 200px;"><label>Category Filter</label>
                    <select name="category">
                        <option value="">-- All Categories --</option>
                        {% for c in categories %}<option value="{{ c }}" {% if category == c %}selected{% endif %}>{{ c }}</option>{% endfor %}
                    </select>
                </div>
                <div class="form-group flex-1" style="min-width: 250px;"><label>Select Account / Ledger</label>
                    <select name="report_account" style="font-weight:bold; color:var(--primary);">
                        <option value="main" {% if report_account == 'main' %}selected{% endif %}>🏢 Main Cash Book</option>
                        <optgroup label="👥 Person Ledgers">
                            {% for p in persons %}<option value="person_{{ p.id }}" {% if report_account == 'person_'~p.id|string %}selected{% endif %}>👤 {{ p.name }}</option>{% endfor %}
                        </optgroup>
                        <optgroup label="💸 Dasti Ledgers">
                            {% for d in dasti_persons %}<option value="dasti_{{ d.id }}" {% if report_account == 'dasti_'~d.id|string %}selected{% endif %}>💸 {{ d.name }}</option>{% endfor %}
                        </optgroup>
                    </select>
                </div>
                <button class="btn-success" type="submit" style="padding: 10px 25px; height: 45px;">Generate</button>
            </form>
        </div>

        <div class="no-print" style="margin-bottom: 20px; display: flex; gap: 10px; justify-content: flex-end;">
            <button onclick="window.print()" class="btn btn-outline" style="background: white;">🖨️ Print Report</button>
            <a href="{{ url_for('export_reports', start_date=start_date, end_date=end_date, category=category, report_account=report_account) }}" class="btn btn-success" style="background: #10b981;">📥 Download Excel (CSV)</a>
        </div>

        <div class="stats-grid">
            <div class="stat-card" style="border-top: 4px solid var(--success);"><h4>Report Incomes / Received</h4><div class="value" style="color: var(--success);">+ ₹{{ "{:,.2f}".format(total_in) }}</div></div>
            <div class="stat-card" style="border-top: 4px solid var(--danger);"><h4>Report Expenses / Advances</h4><div class="value" style="color: var(--danger);">- ₹{{ "{:,.2f}".format(total_out) }}</div></div>
            <div class="stat-card" style="border-top: 4px solid var(--primary); background: #f8fafc;"><h4>Report Net Flow</h4><div class="value">{% if (total_in - total_out) >= 0 %}<span style="color: var(--success);">+ ₹{{ "{:,.2f}".format(total_in - total_out) }}</span>{% else %}<span style="color: var(--danger);">- ₹{{ "{:,.2f}".format((total_in - total_out)|abs) }}</span>{% endif %}</div></div>
        </div>

        <div class="card" style="padding: 0; overflow-x: auto;">
            <h3 style="padding: 18px 25px; margin: 0; background: #f8fafc; border-bottom: 1px solid var(--border);">Report Results</h3>
            <table style="width: 100%; min-width: 800px;">
                <thead><tr><th style="padding-left: 25px; width: 15%;">Date & Time</th><th style="width: 15%;">Mode/Category</th><th style="width: 50%;">Detail</th><th style="text-align: right; width: 20%;">Amount</th></tr></thead>
                <tbody>
                    {% for txn in results %}<tr>
                        <td style="padding-left: 25px;"><span style="font-weight: 500;">{{ txn.date }}</span><br><span style="color: #6b7280; font-size: 0.85em;">{{ txn.time }}</span></td>
                        <td><span class="badge badge-mode">{{ txn.payment_mode }}</span><br><span style="font-size: 0.85em; color: #4b5563;">{{ txn.category }}</span></td>
                        <td style="white-space: pre-wrap;">{{ txn.description }}
                            {% if txn.approved_by %}<br><span style="color: var(--success); font-size: 0.85em; font-weight: 600;">✓ Apprv: {{ txn.approved_by }}</span>{% endif %}
                        </td>
                        <td style="text-align: right;">
                            {% if txn.type in ['expense', 'dasti_out', 'batch_ledger_out', 'dasti_voucher_out', 'advance'] %}<span class="badge badge-out">- ₹{{ "{:,.2f}".format(txn.amount) }}</span>
                            {% else %}<span class="badge badge-in">+ ₹{{ "{:,.2f}".format(txn.amount) }}</span>{% endif %}
                        </td>
                    </tr>{% else %}<tr><td colspan="4" style="text-align:center; color:#9ca3af; padding: 40px;">No records found for these filters.</td></tr>{% endfor %}
                </tbody>
            </table>
        </div>
    </div></body></html>'''

USERS_TEMPLATE = '''<!DOCTYPE html><html><head><title>Manage Users</title>''' + BASE_STYLE + '''</head><body>
    <div class="container">''' + NAVBAR_HTML + '''
        <div class="card" style="margin-bottom: 20px; padding: 20px;">
            <h3 style="font-size: 1.2em;">👤 Create New Firm User</h3>
            <form action="/add_user" method="POST" style="display:flex; gap:15px; align-items: flex-end; flex-wrap:wrap;">
                <div class="form-group flex-1"><label>Username</label><input type="text" name="new_username" required></div>
                <div class="form-group flex-1"><label>Password</label><input type="password" name="new_password" required></div>
                <div class="form-group flex-1"><label>Role</label>
                    <select name="role" required><option value="admin">Admin</option><option value="superadmin">Superadmin</option><option value="cashier">Cashier</option><option value="market">Market</option></select></div>
                <div class="form-group" style="padding-bottom: 10px;"><label><input type="checkbox" name="can_approve" value="1"> Grant Approval Rights</label></div>
                <button class="btn-success" type="submit" style="padding: 10px 25px; height: 45px;">Create User</button>
            </form>
        </div>
        <div class="card" style="padding: 0;">
            <h3 style="padding: 15px 20px; margin: 0; background: #f8fafc; border-bottom: 1px solid var(--border); font-size: 1.2em;">🛡️ Registered Firm Users</h3>
            <table style="width: 100%; border: none;"><tr><th style="padding-left: 20px;">Username</th><th>Role</th><th>Approver</th><th style="text-align:center;">Action</th></tr>
                {% for u in users %}<tr>
                    <td style="padding-left: 20px; font-weight: 500;">{{ u.username }}</td>
                    <td><span class="badge badge-mode">{{ u.role|title }}</span></td>
                    <td>{% if u.can_approve %}<span class="badge badge-success" style="background:#d1fae5; color:#065f46;">Yes</span>{% else %}<span class="badge badge-danger" style="background:#fee2e2; color:#991b1b;">No</span>{% endif %}</td>
                    <td style="text-align: center;"><a href="/edit_user/{{ u.id }}" class="btn btn-sm" style="background:#f59e0b;color:white;">✏️ Edit User</a></td>
                </tr>{% endfor %}
            </table>
        </div>
    </div></body></html>'''

EDIT_USER_TEMPLATE = '''<!DOCTYPE html><html><head><title>Edit User</title>''' + BASE_STYLE + '''</head><body>
    <div class="container">''' + NAVBAR_HTML + '''
        <div class="card" style="max-width: 500px; margin: 0 auto;">
            <h2 style="color: var(--primary); margin-bottom: 20px;">⚙️ Edit User Profile</h2>
            <form action="/edit_user/{{ edit_user.id }}" method="POST">
                <div class="form-group"><label>Username</label><input type="text" name="username" value="{{ edit_user.username }}" required></div>
                <div class="form-group"><label>New Password <small>(Leave blank to keep current password)</small></label><input type="password" name="password"></div>
                <div class="form-group"><label>User Role</label>
                    <select name="role" required>
                        <option value="superadmin" {% if edit_user.role == 'superadmin' %}selected{% endif %}>Superadmin</option>
                        <option value="admin" {% if edit_user.role == 'admin' %}selected{% endif %}>Admin</option>
                        <option value="cashier" {% if edit_user.role == 'cashier' %}selected{% endif %}>Cashier</option>
                        <option value="market" {% if edit_user.role == 'market' %}selected{% endif %}>Market</option>
                    </select>
                </div>
                <div class="form-group" style="padding-bottom: 15px; margin-top: 10px;">
                    <label style="display:flex; align-items:center; gap:10px; cursor:pointer;">
                        <input type="checkbox" name="can_approve" value="1" {% if edit_user.can_approve %}checked{% endif %} style="width: auto;"> Grant Voucher Approval Rights
                    </label>
                </div>
                <div style="display: flex; gap: 15px;">
                    <a href="/manage_users" class="btn btn-outline" style="flex:1;">Cancel</a>
                    <button class="btn-success" type="submit" style="flex:1;">Save Updates</button>
                </div>
            </form>
        </div>
    </div></body></html>'''

APPROVALS_TEMPLATE = '''<!DOCTYPE html><html><head><title>Pending Approvals</title>''' + BASE_STYLE + '''</head><body>
    <div class="container">''' + NAVBAR_HTML + '''
        <div class="card" style="padding: 0;">
            <h3 style="padding: 15px 20px; margin: 0; background: #fef08a; border-bottom: 1px solid var(--border); font-size: 1.2em; color: #92400e;">⏳ Pending Advanced Vouchers</h3>
            <table style="width: 100%; border: none;"><tr><th style="padding-left: 20px;">Date & Time</th><th>Description / Detail</th><th style="text-align: right;">Amount</th><th style="text-align: center;">Action</th></tr>
                {% for t in pending %}<tr>
                    <td style="padding-left: 20px;"><span style="font-weight: 500;">{{ t.date }}</span><br><span style="font-size: 0.85em; color: #6b7280;">{{ t.time }}</span></td>
                    <td><span class="badge badge-pending">Pending</span><br><span style="white-space: pre-wrap;">{{ t.description }}</span></td>
                    <td style="text-align: right;"><strong>₹{{ "{:,.2f}".format(t.amount) }}</strong></td>
                    <td style="text-align: center;">
                        <a href="/approve_voucher/{{ t.link_id }}" class="btn btn-sm btn-success" onclick="return confirm('Approve this transaction?');">✅ Approve</a>
                        <a href="/reject_voucher/{{ t.link_id }}" class="btn btn-sm btn-danger" onclick="return confirm('Reject & Delete this transaction?');">❌ Reject</a>
                    </td>
                </tr>{% else %}<tr><td colspan="4" style="text-align:center; color:#9ca3af; padding: 40px;">No pending vouchers requiring approval.</td></tr>{% endfor %}
            </table>
        </div>
    </div></body></html>'''

EXPRESS_ENTRY_HTML = '''
<div class="express-entry no-print">
    <h3 style="margin-top: 0; color: #3730a3; font-size: 1.15em;">🚀 Express Direct Entry (Main Book)</h3>
    <form action="/add_express" method="POST" style="display: flex; gap: 15px; align-items: center; flex-wrap: wrap;">
        <input type="hidden" name="date" id="express_date"><input type="hidden" name="time" id="express_time">
        <input type="text" name="description" placeholder="Description / Reason" required style="flex: 3; min-width: 200px; border-color: #a5b4fc;">
        <select name="type" required style="flex: 1; min-width: 150px; font-weight: bold; border-color: #a5b4fc;">
            <option value="income">➕ Cash In</option>
            <option value="expense">➖ Cash Out</option>
        </select>
        <input type="number" step="0.01" min="0" name="amount" placeholder="Amount (₹)" value="0" required style="flex: 1; min-width: 120px; border-color: #a5b4fc;">
        <button class="btn" type="submit" style="flex: 1; min-width: 150px; background: #4f46e5;">⚡ Save Instant</button>
    </form>
</div>
'''

ENTRY_FORM_HTML = '''
<form action="/add_batch_unified" method="POST" class="no-print">
    <input type="hidden" name="source_page" value="{{ active_page }}">
    <div style="background: #f8fafc; padding: 20px; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 20px;">
        <div class="flex-row" style="margin-bottom: 15px;">
            <div class="form-group flex-1" style="min-width: 140px; margin-bottom: 0;"><label>Date</label><input type="date" name="date" required></div>
            <div class="form-group flex-1" style="min-width: 140px; margin-bottom: 0;"><label>Time</label><input type="time" name="time" required></div>
            <div class="form-group flex-1" style="min-width: 150px; margin-bottom: 0;"><label>Payment Mode</label><select name="payment_mode" required><option value="Cash">💵 Cash</option><option value="Online">💳 Online</option></select></div>
        </div>
        <div class="flex-row">
            <div class="form-group flex-1" style="min-width: 200px; margin-bottom: 0;">
                <label>Transaction Nature</label>
                <select name="txn_nature" id="txn_nature" onchange="toggleNature()" required style="border-color: var(--primary); font-weight: bold; font-size: 1.05em;">
                    <option value="slip_in" style="color:var(--danger);">➖ Submit Slip / Bill (- Deduct from User Bal)</option>
                    <option value="advance" style="color:var(--primary);">📤 Give Advance Payment (+ Positive User Bal)</option>
                    <option value="receive_cash" style="color:var(--success);">📥 Receive Cash Settlement (- Deduct from User Bal)</option>
                </select>
            </div>
            <div class="form-group flex-1" style="min-width: 250px; margin-bottom: 0; flex: 2;">
                <label id="primary_label" style="color: var(--primary);">Ledger Account</label>
                <select name="primary_account" id="primary_account" onchange="checkNewAccount(this)" required style="border-color: var(--primary); font-weight: bold; background: white; font-size: 1.05em;">
                    <option value="main" style="font-weight:bold;">🏢 Main Cash Book (Default)</option>
                    <optgroup label="👥 Person Ledgers">
                        {% for p in persons %}<option value="person_{{ p.id }}">👤 {{ p.name }}'s Account</option>{% endfor %}
                    </optgroup>
                    <optgroup label="💸 Dasti Accounts">
                        {% for dp in dasti_persons %}<option value="dasti_{{ dp.id }}">💸 {{ dp.name }}'s Dasti</option>{% endfor %}
                    </optgroup>
                    <option value="new_dasti" style="color: #0ea5e9; font-weight: bold;">➕ Create New Dasti Account...</option>
                    <option value="new_person" style="color: var(--success); font-weight: bold;">➕ Create New Person Account...</option>
                </select>
                <input type="text" name="new_account_name" id="new_account_name" placeholder="Type New Name Here..." style="display:none; margin-top: 8px; border-color: var(--primary); width: 100%;">
            </div>
        </div>
    </div>
    <div style="border: 1px solid var(--border); border-radius: 8px; margin-bottom: 20px; background: #fff; overflow-x: auto;">
        <table style="width: 100%; min-width: 800px; margin: 0; background: transparent;">
            <thead style="background: #f1f5f9;"><tr><th style="width: 25%;">Category</th><th style="width: 50%;">Bill Detail / Description</th><th style="width: 20%;">Amount (₹)</th><th style="width: 5%; text-align: center;">Act</th></tr></thead>
            <tbody id="entryBody"></tbody>
        </table>
    </div>
    <div style="display: flex; gap: 15px; justify-content: space-between;">
        <button type="button" class="btn-outline" onclick="addRow('{% for c in categories %}<option value=\\\'{{c}}\\\'>{{c}}</option>{% endfor %}')" style="min-width: 200px; font-size: 1em;">+ Add Another Row</button>
        <button class="btn-success" type="submit" style="min-width: 250px; font-size: 1.1em; padding: 12px;">💾 Save Batch Voucher</button>
    </div>
</form>
<script>document.addEventListener("DOMContentLoaded", function() { initForm('{% for c in categories %}<option value="{{c}}">{{c}}</option>{% endfor %}'); });</script>
'''

EDIT_TEMPLATE = '''<!DOCTYPE html><html><head><title>Edit Entry</title>''' + BASE_STYLE + '''</head><body>
    <div class="container">''' + NAVBAR_HTML + '''
        <div class="card" style="max-width: 600px; margin: 0 auto;">
            <h2 style="color: var(--primary); margin-bottom: 20px;">✏️ Edit Transaction</h2>
            <form action="/edit/{{ table_name }}/{{ entry.id }}" method="POST">
                <div class="flex-row">
                    <div class="form-group flex-1"><label>Date</label><input type="date" name="date" value="{{ entry.date }}" required></div>
                    <div class="form-group flex-1"><label>Time</label><input type="time" name="time" value="{{ entry.time }}" required></div>
                </div>
                <div class="flex-row">
                    <div class="form-group flex-1"><label>Mode</label>
                        <select name="payment_mode" required><option value="Cash" {% if entry.payment_mode == 'Cash' %}selected{% endif %}>Cash</option><option value="Online" {% if entry.payment_mode == 'Online' %}selected{% endif %}>Online</option></select>
                    </div>
                    <div class="form-group flex-1"><label>Category</label><input type="text" name="category" value="{{ entry.category }}" required></div>
                </div>
                <div class="form-group"><label>Description / Bill Details</label><input type="text" name="description" value="{{ entry.description }}" required></div>

                {% if session.get('role') in ['admin', 'superadmin'] and entry.status == 'approved' %}
                <div class="form-group">
                    <label>Approved By <small>(Admin Override)</small></label>
                    <input type="text" name="approved_by" value="{{ entry.approved_by }}" style="border-color: var(--warning);">
                </div>
                {% endif %}

                <div class="flex-row">
                    <div class="form-group flex-1"><label>Type</label>
                        <select name="type" required>
                            <option value="income" {% if entry.type == 'income' %}selected{% endif %}>➕ Main In</option><option value="expense" {% if entry.type == 'expense' %}selected{% endif %}>➖ Main Out</option>
                            <option value="dasti_out" {% if entry.type == 'dasti_out' %}selected{% endif %}>📤 Transfer (Main Out)</option>
                            <option value="batch_ledger_out" {% if entry.type == 'batch_ledger_out' %}selected{% endif %}>➖ Ledger Slip Out</option>
                            <option value="dasti_voucher_out" {% if entry.type == 'dasti_voucher_out' %}selected{% endif %}>💸 Dasti Voucher Out</option>
                            <option value="dasti_voucher_in" {% if entry.type == 'dasti_voucher_in' %}selected{% endif %}>💸 Dasti Settlement In</option>
                            <option value="settlement" {% if entry.type == 'settlement' %}selected{% endif %}>➖ Person Bill / Settlement</option>
                            <option value="advance" {% if entry.type == 'advance' %}selected{% endif %}>➕ Person Advance</option>
                        </select>
                    </div>
                    <div class="form-group flex-1"><label>Amount (₹)</label><input type="number" step="0.01" min="0" name="amount" value="{{ entry.amount }}" required></div>
                </div>
                <div style="display: flex; gap: 15px; margin-top: 20px;">
                    <a href="javascript:history.back()" class="btn btn-outline" style="flex:1;">Cancel / Exit</a>
                    <button class="btn-success" type="submit" style="flex:1;">Save Changes</button>
                </div>
            </form>
        </div>
    </div></body></html>'''

INDEX_TEMPLATE = '''<!DOCTYPE html><html><head><title>Main Cash Book Dashboard</title>''' + BASE_STYLE + '''</head><body>
    <div class="container">''' + NAVBAR_HTML + '''

        <div class="card no-print" style="padding: 20px; background: linear-gradient(to right, #ffffff, #f1f5f9);">
            <h3 style="margin-bottom: 15px; font-size: 1.2em; color: #475569;">📈 Account Flow Summary</h3>
            <div class="stats-grid" style="grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin-bottom: 0;">
                <div class="stat-card" style="padding: 15px;"><h4>Today</h4><div style="color:var(--success); font-weight:bold;">+ ₹{{ "{:,.2f}".format(s_d_in) }}</div><div style="color:var(--danger); font-weight:bold;">- ₹{{ "{:,.2f}".format(s_d_out) }}</div></div>
                <div class="stat-card" style="padding: 15px;"><h4>Last 7 Days</h4><div style="color:var(--success); font-weight:bold;">+ ₹{{ "{:,.2f}".format(s_w_in) }}</div><div style="color:var(--danger); font-weight:bold;">- ₹{{ "{:,.2f}".format(s_w_out) }}</div></div>
                <div class="stat-card" style="padding: 15px;"><h4>This Month</h4><div style="color:var(--success); font-weight:bold;">+ ₹{{ "{:,.2f}".format(s_m_in) }}</div><div style="color:var(--danger); font-weight:bold;">- ₹{{ "{:,.2f}".format(s_m_out) }}</div></div>
                <div class="stat-card" style="padding: 15px;"><h4>This Year</h4><div style="color:var(--success); font-weight:bold;">+ ₹{{ "{:,.2f}".format(s_y_in) }}</div><div style="color:var(--danger); font-weight:bold;">- ₹{{ "{:,.2f}".format(s_y_out) }}</div></div>
            </div>
        </div>

        ''' + EXPRESS_ENTRY_HTML + '''

        <div class="card balance-card">
            <h2 style="color: #64748b; font-size: 1.1em; text-transform: uppercase; margin-bottom: 0;">🏢 Available Main Cash Book Balance</h2>
            <div class="balance-amount" style="color: {{ 'var(--success)' if balance >= 0 else 'var(--danger)' }}">₹{{ "{:,.2f}".format(balance) }}</div>

            <div style="display: flex; justify-content: center; gap: 30px; margin-top: 15px; flex-wrap: wrap;">
                <div style="color: #0369a1; background: #e0f2fe; padding: 10px 15px; border-radius: 8px; border: 1px solid #bae6fd; min-width: 250px;">
                    <strong style="font-size: 0.85em; color: #0284c7; text-transform: uppercase;">Person Ledger Advances (Outstanding)</strong><br>
                    <span style="font-size: 1.2em; font-weight: bold;">₹{{ "{:,.2f}".format(total_dasti) }}</span>
                    {% if dasti_breakdown %}
                    <div style="margin-top: 8px; font-size: 0.85em; color: #0369a1; text-align: left; border-top: 1px solid #bae6fd; padding-top: 8px;">
                        {% for d in dasti_breakdown %}
                        <div style="display: flex; justify-content: space-between; margin-bottom: 3px;">
                            <span>👤 {{ d.name }}</span> <strong>₹{{ "{:,.2f}".format(d.amount) }}</strong>
                        </div>
                        {% endfor %}
                    </div>
                    {% endif %}
                </div>
            </div>
        </div>

        <div class="card no-print" style="padding: 25px;"><h3 style="margin-bottom: 15px; font-size: 1.3em;">⚡ Master Advanced Batch Entry</h3>''' + ENTRY_FORM_HTML + '''</div>

        <div class="ledger-container">
            <div class="ledger-col"><h3 class="ledger-title" style="color: var(--success); border-bottom: 3px solid var(--success);">Receipts (+ IN)</h3>
                <table style="width: 100%; font-size: 0.95em;"><tr><th style="width: 5%;">Sr.</th><th>Date</th><th>Mode/Cat</th><th>Detail</th><th style="text-align: right;">Amount</th><th class="no-print">Act</th></tr>
                    {% for t in incomes %}<tr>
                        <td style="color: #64748b; font-weight: bold;">{{ loop.index }}</td>
                        <td><span style="font-weight: 500;">{{ t.date }}</span><br><span style="font-size: 0.85em; color: #6b7280;">{{ t.time }}</span></td>
                        <td><span class="badge badge-mode">{{ t.payment_mode }}</span><br><span style="font-size: 0.85em; color: #4b5563;">{{ t.category }}</span></td>
                        <td style="white-space: pre-wrap;">{{ t.description }}
                            {% if t.status == 'approved' and t.approved_by %}<br><span style="color: var(--success); font-size: 0.85em; font-weight: 600;">✓ Apprv: {{ t.approved_by }}</span>{% endif %}
                        </td>
                        <td style="text-align: right;">
                            {% if t.status == 'pending' %}<span class="badge badge-pending">⏳ Pending</span><br>{% endif %}
                            <span class="badge badge-in">+ ₹{{ "{:,.2f}".format(t.amount) }}</span>
                        </td>
                        <td style="text-align: center;" class="no-print"><a href="/edit/transactions/{{ t.id }}" class="btn btn-sm" style="background:#f59e0b;color:white;">✏️</a> <br> <a href="/delete/transactions/{{ t.id }}" class="btn btn-sm btn-danger" onclick="return confirm('Move to Trash?');">🗑️</a></td>
                    </tr>{% else %}<tr><td colspan="6" style="text-align: center; color: #9ca3af; padding: 40px 0;">No entries yet.</td></tr>{% endfor %}
                </table>
            </div>
            <div class="ledger-col"><h3 class="ledger-title" style="color: var(--danger); border-bottom: 3px solid var(--danger);">Payments (- OUT)</h3>
                <table style="width: 100%; font-size: 0.95em;"><tr><th style="width: 5%;">Sr.</th><th>Date</th><th>Mode/Cat</th><th>Detail</th><th style="text-align: right;">Amount</th><th class="no-print">Act</th></tr>
                    {% for t in expenses %}<tr>
                        <td style="color: #64748b; font-weight: bold;">{{ loop.index }}</td>
                        <td><span style="font-weight: 500;">{{ t.date }}</span><br><span style="font-size: 0.85em; color: #6b7280;">{{ t.time }}</span></td>
                        <td><span class="badge badge-mode">{{ t.payment_mode }}</span><br><span style="font-size: 0.85em; color: #4b5563;">{{ t.category }}</span></td>
                        <td style="white-space: pre-wrap;">{{ t.description }}
                            {% if t.status == 'approved' and t.approved_by %}<br><span style="color: var(--success); font-size: 0.85em; font-weight: 600;">✓ Apprv: {{ t.approved_by }}</span>{% endif %}
                        </td>
                        <td style="text-align: right;">
                            {% if t.status == 'pending' %}<span class="badge badge-pending">⏳ Pending</span><br>{% endif %}
                            <span class="badge badge-out">- ₹{{ "{:,.2f}".format(t.amount) }}</span>
                        </td>
                        <td style="text-align: center;" class="no-print"><a href="/edit/transactions/{{ t.id }}" class="btn btn-sm" style="background:#f59e0b;color:white;">✏️</a> <br> <a href="/delete/transactions/{{ t.id }}" class="btn btn-sm btn-danger" onclick="return confirm('Move to Trash?');">🗑️</a></td>
                    </tr>{% else %}<tr><td colspan="6" style="text-align: center; color: #9ca3af; padding: 40px 0;">No entries yet.</td></tr>{% endfor %}
                </table>
            </div>
        </div>
    </div></body></html>'''

MAIN_LEDGER_TEMPLATE = '''<!DOCTYPE html><html><head><title>Main Cash Book Ledger</title>''' + BASE_STYLE + '''</head><body>
    <div class="container">''' + NAVBAR_HTML + '''
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <h2 style="margin: 0; font-size: 1.6em;">🏢 Main Cash Book Complete Ledger</h2>
        </div>
        <div class="stats-grid">
            <div class="stat-card" style="border-top: 4px solid var(--success);"><h4>Total Received (+ In)</h4><div class="value" style="color: var(--success);">+ ₹{{ "{:,.2f}".format(total_in) }}</div></div>
            <div class="stat-card" style="border-top: 4px solid var(--danger);"><h4>Total Payments & Advances (- Out)</h4><div class="value" style="color: var(--danger);">- ₹{{ "{:,.2f}".format(total_out + total_dasti + total_dasti_vouchers) }}</div></div>
            <div class="stat-card" style="border-top: 4px solid var(--primary); background: #f8fafc;"><h4>Available Balance</h4><div class="value">
                {% if balance >= 0 %}<span style="color: var(--success);">₹{{ "{:,.2f}".format(balance) }}</span>
                {% else %}<span style="color: var(--danger);">₹{{ "{:,.2f}".format(balance) }}</span>{% endif %}
            </div></div>
        </div>
        <div class="card" style="padding: 0; overflow-x: auto;">
            <h3 style="padding: 18px 25px; margin: 0; background: #f8fafc; border-bottom: 1px solid var(--border);">Detailed Transaction History</h3>
            <table style="width: 100%; min-width: 800px;">
                <thead><tr><th style="padding-left: 25px; width: 15%;">Date & Time</th><th style="width: 15%;">Mode/Category</th><th style="width: 45%;">Bill No / Details & Link</th><th style="text-align: right; width: 15%;">Amount</th><th style="text-align: center; width: 10%;">Act</th></tr></thead>
                <tbody>
                    {% for txn in txns %}<tr>
                        <td style="padding-left: 25px;"><span style="font-weight: 500;">{{ txn.date }}</span><br><span style="color: #6b7280; font-size: 0.85em;">{{ txn.time }}</span></td>
                        <td><span class="badge badge-mode">{{ txn.payment_mode }}</span><br><span style="font-size: 0.85em; color: #4b5563;">{{ txn.category }}</span></td>
                        <td style="white-space: pre-wrap;">{{ txn.description }}
                            {% if txn.status == 'approved' and txn.approved_by %}<br><span style="color: var(--success); font-size: 0.85em; font-weight: 600;">✓ Apprv: {{ txn.approved_by }}</span>{% endif %}
                        </td>
                        <td style="text-align: right;">
                            {% if txn.status == 'pending' %}<span class="badge badge-pending">⏳ Pending</span><br>{% endif %}
                            {% if txn.type in ['expense', 'dasti_out', 'batch_ledger_out', 'dasti_voucher_out'] %}<span class="badge badge-out">- ₹{{ "{:,.2f}".format(txn.amount) }} <br><small>({% if txn.type == 'dasti_out' %}Transfer Out{% elif txn.type == 'batch_ledger_out' %}Ledger Slip Out{% elif txn.type == 'dasti_voucher_out' %}Dasti Advance Out{% else %}Payment Out{% endif %})</small></span>
                            {% else %}<span class="badge badge-in">+ ₹{{ "{:,.2f}".format(txn.amount) }} <br><small>(Receipt/In)</small></span>{% endif %}
                        </td>
                        <td style="text-align: center;"><a href="/edit/transactions/{{ txn.id }}" class="btn btn-sm" style="background:#f59e0b;color:white;">✏️</a> <br> <a href="/delete/transactions/{{ txn.id }}" class="btn btn-sm btn-danger" onclick="return confirm('Move to Trash?');">🗑️</a></td>
                    </tr>{% else %}<tr><td colspan="5" style="text-align:center; color:#9ca3af; padding: 40px;">No entries found in Main Cash Book.</td></tr>{% endfor %}
                </tbody>
            </table>
        </div>
    </div></body></html>'''

PERSONS_TEMPLATE = '''<!DOCTYPE html><html><head><title>Person Ledgers</title>''' + BASE_STYLE + '''</head><body>
    <div class="container">''' + NAVBAR_HTML + '''
        <div class="card" style="padding: 0;">
            <h3 style="padding: 15px 20px; margin: 0; background: #f8fafc; border-bottom: 1px solid var(--border); font-size: 1.2em;">📊 Outstanding Balances & Person Ledgers</h3>
            <table style="width: 100%; border: none;"><tr><th style="padding-left: 20px; font-size: 1em;">Name</th><th style="text-align: right; font-size: 1em;">Net Status</th><th style="text-align: center; width: 220px; padding-right: 20px; font-size: 1em;">Action</th></tr>
                {% for b in balances %}<tr>
                    <td style="padding-left: 20px; font-weight: 500; font-size: 1.1em;">{{ b.name }}</td>
                    <td style="text-align: right;">{% if b.net > 0 %}<span class="badge badge-primary" style="font-size: 1em; padding: 6px 12px; background: #e0e7ff; color: #3730a3; border-radius: 8px;">+ ₹{{ "{:,.2f}".format(b.net) }} (Owes Firm)</span>{% elif b.net < 0 %}<span class="badge badge-success" style="font-size: 1em; padding: 6px 12px; background: #d1fae5; color: #065f46; border-radius: 8px;">- ₹{{ "{:,.2f}".format(b.net|abs) }} (Firm Owes)</span>{% else %}<span style="color: #9ca3af; font-weight: 600;">✓ Settled</span>{% endif %}</td>
                    <td style="text-align: center; padding-right: 20px;">
                        <a href="/person_account/{{ b.id }}" class="btn btn-outline btn-sm">View</a>
                        <button onclick="let n=prompt('Edit Name:', '{{ b.name }}'); if(n) window.location='/edit_person/{{ b.id }}?name='+encodeURIComponent(n);" class="btn btn-sm" style="background:#f59e0b; color:white;">✏️</button>
                    </td>
                </tr>{% else %}<tr><td colspan="3" style="text-align:center; color:#9ca3af; padding: 40px;">No active profiles. Create one from the Dashboard Batch Entry!</td></tr>{% endfor %}
            </table>
        </div>
    </div></body></html>'''

PERSON_ACCOUNT_TEMPLATE = '''<!DOCTYPE html><html><head><title>Account: {{ person.name }}</title>''' + BASE_STYLE + '''</head><body>
    <div class="container">''' + NAVBAR_HTML + '''
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;"><a href="/persons" class="btn-outline" style="text-decoration: none; padding: 8px 15px; border-radius: 8px; font-size: 0.9em;">← Back to Ledgers</a><h2 style="margin: 0; font-size: 1.6em;">Person Ledger: <span style="color: var(--primary);">{{ person.name }}</span></h2></div>
        <div class="stats-grid">
            <div class="stat-card" style="border-top: 4px solid var(--primary);"><h4>Total Advances (Received from Main)</h4><div class="value" style="color: var(--primary);">+ ₹{{ "{:,.2f}".format(advances) }}</div></div>
            <div class="stat-card" style="border-top: 4px solid var(--success);"><h4>Total Slips / Settlements</h4><div class="value" style="color: var(--success);">- ₹{{ "{:,.2f}".format(settlements) }}</div></div>
            <div class="stat-card" style="border-top: 4px solid #8b5cf6; background: #f8fafc;"><h4>Net Status</h4><div class="value">{% if balance > 0 %}<span style="color: var(--primary);">+ ₹{{ "{:,.2f}".format(balance) }}<br><small style="font-size: 0.5em; color: #4b5563; text-transform: uppercase;">Owes Firm</small></span>{% elif balance < 0 %}<span style="color: var(--success);">- ₹{{ "{:,.2f}".format(balance|abs) }}<br><small style="font-size: 0.5em; color: #4b5563; text-transform: uppercase;">Firm Owes</small></span>{% else %}<span style="color: #6b7280; font-size: 0.9em;">Fully Settled</span>{% endif %}</div></div>
        </div>
        <div class="card" style="padding: 0; overflow-x: auto;">
            <h3 style="padding: 18px 25px; margin: 0; background: #f8fafc; border-bottom: 1px solid var(--border);">Detailed Transaction History</h3>
            <table style="width: 100%; min-width: 800px;">
                <thead><tr><th style="padding-left: 25px; width: 15%;">Date & Time</th><th style="width: 15%;">Mode/Category</th><th style="width: 45%;">Bill No / Details & Link</th><th style="text-align: right; width: 15%;">Amount</th><th style="text-align: center; width: 10%;">Act</th></tr></thead>
                <tbody>
                    {% for txn in txns %}<tr>
                        <td style="padding-left: 25px;"><span style="font-weight: 500;">{{ txn.date }}</span><br><span style="color: #6b7280; font-size: 0.85em;">{{ txn.time }}</span></td>
                        <td><span class="badge badge-mode">{{ txn.payment_mode }}</span><br><span style="font-size: 0.85em; color: #4b5563;">{{ txn.category }}</span></td>
                        <td style="white-space: pre-wrap;">{{ txn.description }}
                            {% if txn.status == 'approved' and txn.approved_by %}<br><span style="color: var(--success); font-size: 0.85em; font-weight: 600;">✓ Apprv: {{ txn.approved_by }}</span>{% endif %}
                        </td>
                        <td style="text-align: right;">
                            {% if txn.status == 'pending' %}<span class="badge badge-pending">⏳ Pending</span><br>{% endif %}
                            {% if txn.type == 'advance' %}<span class="badge badge-in" style="background:#e0e7ff; color:#3730a3;">+ ₹{{ "{:,.2f}".format(txn.amount) }} <br><small>(Advance)</small></span>
                            {% else %}<span class="badge badge-out" style="background:#d1fae5; color:#065f46;">- ₹{{ "{:,.2f}".format(txn.amount) }} <br><small>(Slip / Settle)</small></span>{% endif %}
                        </td>
                        <td style="text-align: center;"><a href="/edit/person_ledger/{{ txn.id }}" class="btn btn-sm" style="background:#f59e0b;color:white;">✏️</a> <br> <a href="/delete/person_ledger/{{ txn.id }}" class="btn btn-sm btn-danger" onclick="return confirm('Move to Trash?');">🗑️</a></td>
                    </tr>{% else %}<tr><td colspan="5" style="text-align:center; color:#9ca3af; padding: 40px;">No historical entries found for this person.</td></tr>{% endfor %}
                </tbody>
            </table>
        </div>
    </div></body></html>'''

DASTI_LEDGER_TEMPLATE = '''<!DOCTYPE html><html><head><title>Dasti Ledger</title>''' + BASE_STYLE + '''</head><body>
    <div class="container">''' + NAVBAR_HTML + '''

        <div class="card balance-card" style="margin-bottom: 25px;">
            <h2 style="color: #64748b; font-size: 1.1em; text-transform: uppercase; margin-bottom: 0;">🏢 Available Main Cash Book Balance</h2>
            <div class="balance-amount" style="color: {{ 'var(--success)' if balance >= 0 else 'var(--danger)' }}">₹{{ "{:,.2f}".format(balance) }}</div>

            <div style="display: flex; justify-content: center; margin-top: 15px;">
                <div style="color: #0369a1; background: #e0f2fe; padding: 10px 15px; border-radius: 8px; border: 1px solid #bae6fd; min-width: 250px;">
                    <strong style="font-size: 0.85em; color: #0284c7; text-transform: uppercase;">💸 Total Dasti Balance (Outstanding)</strong><br>
                    <span style="font-size: 1.2em; font-weight: bold;">₹{{ "{:,.2f}".format(total_outstanding_dasti) }}</span>
                </div>
            </div>
        </div>

        <div class="card no-print" style="padding: 0;">
            <h3 style="padding: 15px 20px; margin: 0; background: #f8fafc; border-bottom: 1px solid var(--border); font-size: 1.2em;">📊 Outstanding Dasti Accounts</h3>
            <table style="width: 100%; border: none;"><tr><th style="padding-left: 20px; font-size: 1em;">Dasti Name</th><th style="text-align: right; font-size: 1em;">Net Status</th><th style="text-align: center; width: 220px; padding-right: 20px; font-size: 1em;">Action</th></tr>
                {% for b in balances %}<tr>
                    <td style="padding-left: 20px; font-weight: 500; font-size: 1.1em;">{{ b.name }}</td>
                    <td style="text-align: right;">{% if b.net > 0 %}<span class="badge badge-primary" style="font-size: 1em; padding: 6px 12px; background: #e0f2fe; color: #0369a1; border-radius: 8px;">+ ₹{{ "{:,.2f}".format(b.net) }} (Owes Firm)</span>{% elif b.net < 0 %}<span class="badge badge-success" style="font-size: 1em; padding: 6px 12px; background: #d1fae5; color: #065f46; border-radius: 8px;">- ₹{{ "{:,.2f}".format(b.net|abs) }} (Firm Owes)</span>{% else %}<span style="color: #9ca3af; font-weight: 600;">✓ Settled</span>{% endif %}</td>
                    <td style="text-align: center; padding-right: 20px;">
                        <a href="/dasti_account/{{ b.id }}" class="btn btn-outline btn-sm">View</a>
                        <button onclick="let n=prompt('Edit Name:', '{{ b.name }}'); if(n) window.location='/edit_dasti_person/{{ b.id }}?name='+encodeURIComponent(n);" class="btn btn-sm" style="background:#f59e0b; color:white;">✏️</button>
                    </td>
                </tr>{% else %}<tr><td colspan="3" style="text-align:center; color:#9ca3af; padding: 40px;">No active Dasti accounts yet. Type a name in the Master Batch voucher to create one!</td></tr>{% endfor %}
            </table>
        </div>
    </div></body></html>'''

DASTI_ACCOUNT_TEMPLATE = '''<!DOCTYPE html><html><head><title>Dasti Account: {{ person.name }}</title>''' + BASE_STYLE + '''</head><body>
    <div class="container">''' + NAVBAR_HTML + '''
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;"><a href="/dasti_ledger" class="btn-outline" style="text-decoration: none; padding: 8px 15px; border-radius: 8px; font-size: 0.9em;">← Back to Dasti Ledgers</a><h2 style="margin: 0; font-size: 1.6em;">Dasti Ledger: <span style="color: #0ea5e9;">{{ person.name }}</span></h2></div>
        <div class="stats-grid">
            <div class="stat-card" style="border-top: 4px solid #0ea5e9;"><h4>Total Advances (Given Out)</h4><div class="value" style="color: #0ea5e9;">+ ₹{{ "{:,.2f}".format(advances) }}</div></div>
            <div class="stat-card" style="border-top: 4px solid var(--success);"><h4>Total Slips / Settlements</h4><div class="value" style="color: var(--success);">- ₹{{ "{:,.2f}".format(settlements) }}</div></div>
            <div class="stat-card" style="border-top: 4px solid #8b5cf6; background: #f8fafc;"><h4>Net Status</h4><div class="value">{% if balance > 0 %}<span style="color: #0ea5e9;">+ ₹{{ "{:,.2f}".format(balance) }}<br><small style="font-size: 0.5em; color: #4b5563; text-transform: uppercase;">Owes Firm</small></span>{% elif balance < 0 %}<span style="color: var(--success);">- ₹{{ "{:,.2f}".format(balance|abs) }}<br><small style="font-size: 0.5em; color: #4b5563; text-transform: uppercase;">Firm Owes</small></span>{% else %}<span style="color: #6b7280; font-size: 0.9em;">Fully Settled</span>{% endif %}</div></div>
        </div>
        <div class="card" style="padding: 0; overflow-x: auto;">
            <h3 style="padding: 18px 25px; margin: 0; background: #f8fafc; border-bottom: 1px solid var(--border);">Detailed Transaction History</h3>
            <table style="width: 100%; min-width: 800px;">
                <thead><tr><th style="padding-left: 25px; width: 15%;">Date & Time</th><th style="width: 15%;">Mode/Category</th><th style="width: 45%;">Dasti Detail & Link</th><th style="text-align: right; width: 15%;">Amount</th><th style="text-align: center; width: 10%;">Act</th></tr></thead>
                <tbody>
                    {% for txn in txns %}<tr>
                        <td style="padding-left: 25px;"><span style="font-weight: 500;">{{ txn.date }}</span><br><span style="color: #6b7280; font-size: 0.85em;">{{ txn.time }}</span></td>
                        <td><span class="badge badge-mode">{{ txn.payment_mode }}</span><br><span style="font-size: 0.85em; color: #4b5563;">{{ txn.category }}</span></td>
                        <td style="white-space: pre-wrap;">{{ txn.description }}
                            {% if txn.status == 'approved' and txn.approved_by %}<br><span style="color: var(--success); font-size: 0.85em; font-weight: 600;">✓ Apprv: {{ txn.approved_by }}</span>{% endif %}
                        </td>
                        <td style="text-align: right;">
                            {% if txn.status == 'pending' %}<span class="badge badge-pending">⏳ Pending</span><br>{% endif %}
                            {% if txn.type == 'advance' %}<span class="badge badge-in" style="background:#e0f2fe; color:#0369a1;">+ ₹{{ "{:,.2f}".format(txn.amount) }} <br><small>(Advance Given)</small></span>
                            {% else %}<span class="badge badge-out" style="background:#d1fae5; color:#065f46;">- ₹{{ "{:,.2f}".format(txn.amount) }} <br><small>(Slip / Settle)</small></span>{% endif %}
                        </td>
                        <td style="text-align: center;"><a href="/edit/dasti_ledger/{{ txn.id }}" class="btn btn-sm" style="background:#f59e0b;color:white;">✏️</a> <br> <a href="/delete/dasti_ledger/{{ txn.id }}" class="btn btn-sm btn-danger" onclick="return confirm('Move to Trash?');">🗑️</a></td>
                    </tr>{% else %}<tr><td colspan="5" style="text-align:center; color:#9ca3af; padding: 40px;">No historical entries found for this person.</td></tr>{% endfor %}
                </tbody>
            </table>
        </div>
    </div></body></html>'''

# --- DATABASE LOGIC ---

def init_db():
    conn = sqlite3.connect('cashbook.db'); c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, firm_name TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS persons (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, name TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS dasti_persons (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, name TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, date TEXT, time TEXT, payment_mode TEXT, category TEXT, description TEXT, type TEXT, amount REAL, link_id TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS person_ledger (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, person_id INTEGER, date TEXT, time TEXT, payment_mode TEXT, category TEXT, description TEXT, type TEXT, amount REAL, link_id TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS dasti_ledger (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, dasti_person_id INTEGER, date TEXT, time TEXT, payment_mode TEXT, category TEXT, description TEXT, type TEXT, amount REAL, link_id TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, firm_id INTEGER, name TEXT UNIQUE)''')

    try: c.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'superadmin'")
    except: pass
    try: c.execute("ALTER TABLE users ADD COLUMN firm_id INTEGER")
    except: pass
    try: c.execute("ALTER TABLE users ADD COLUMN can_approve INTEGER DEFAULT 1")
    except: pass

    for table in ['transactions', 'person_ledger', 'dasti_ledger']:
        for col, default in [('time', "'00:00'"), ('payment_mode', "'Cash'"), ('category', "'General'"), ('link_id', "''"), ('status', "'approved'"), ('approved_by', "''"), ('deleted', "0")]:
            try: c.execute(f"ALTER TABLE {table} ADD COLUMN {col} TEXT DEFAULT {default}")
            except sqlite3.OperationalError: pass

    c.execute("UPDATE users SET firm_id = id WHERE firm_id IS NULL")
    conn.commit(); conn.close()

def has_users():
    conn = sqlite3.connect('cashbook.db'); c = conn.cursor(); c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]; conn.close()
    return count > 0

def get_categories(firm_id):
    conn = sqlite3.connect('cashbook.db'); c = conn.cursor()
    custom = [r[0] for r in c.execute("SELECT name FROM categories WHERE firm_id=?", (firm_id,)).fetchall()]
    conn.close()
    return ['General', 'Sales', 'Purchase', 'Salary', 'Transport'] + custom

# --- ROUTES ---

@app.route('/')
def index():
    if not has_users(): return redirect(url_for('register'))
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = sqlite3.connect('cashbook.db'); conn.row_factory = sqlite3.Row; c = conn.cursor(); firm_id = session['firm_id']
    persons = c.execute("SELECT * FROM persons WHERE user_id = ? ORDER BY name ASC", (firm_id,)).fetchall()
    dasti_persons = c.execute("SELECT * FROM dasti_persons WHERE user_id = ? ORDER BY name ASC", (firm_id,)).fetchall()

    incomes = c.execute("SELECT * FROM transactions WHERE user_id = ? AND type='income' AND deleted=0 ORDER BY date DESC, time DESC, id DESC", (firm_id,)).fetchall()
    expenses = c.execute("SELECT * FROM transactions WHERE user_id = ? AND type IN ('expense', 'batch_ledger_out') AND deleted=0 ORDER BY date ASC, time ASC, id ASC", (firm_id,)).fetchall()

    total_in_actual = c.execute("SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type IN ('income', 'dasti_voucher_in') AND status='approved' AND deleted=0", (firm_id,)).fetchone()[0] or 0.0

    # CRITICAL MATH FIX: We only subtract physical cash out (expense, dasti_out, dasti_voucher_out).
    # 'batch_ledger_out' (Slips) are ignored here so we don't double-deduct the firm's balance!
    total_out_actual = c.execute("SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type IN ('expense', 'dasti_out', 'dasti_voucher_out') AND status='approved' AND deleted=0", (firm_id,)).fetchone()[0] or 0.0

    summary_txns = c.execute("SELECT date, type, amount FROM transactions WHERE user_id=? AND deleted=0 AND status='approved'", (firm_id,)).fetchall()
    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')
    month_str = now.strftime('%Y-%m')
    year_str = now.strftime('%Y')
    week_ago_str = (now - timedelta(days=7)).strftime('%Y-%m-%d')

    s_d_in = s_d_out = s_w_in = s_w_out = s_m_in = s_m_out = s_y_in = s_y_out = 0
    for r in summary_txns:
        amt, d, ttype = r['amount'], r['date'], r['type']
        is_in = ttype in ('income', 'dasti_voucher_in')
        is_out = ttype in ('expense', 'dasti_out', 'dasti_voucher_out')

        if d.startswith(year_str):
            if is_in: s_y_in += amt
            elif is_out: s_y_out += amt
        if d.startswith(month_str):
            if is_in: s_m_in += amt
            elif is_out: s_m_out += amt
        if d >= week_ago_str:
            if is_in: s_w_in += amt
            elif is_out: s_w_out += amt
        if d == today_str:
            if is_in: s_d_in += amt
            elif is_out: s_d_out += amt

    total_dasti_ledger = 0.0
    dasti_breakdown = []
    for p in persons:
        adv = c.execute("SELECT SUM(amount) FROM person_ledger WHERE user_id = ? AND person_id = ? AND type='advance' AND status='approved' AND deleted=0", (firm_id, p['id'])).fetchone()[0] or 0.0
        setl = c.execute("SELECT SUM(amount) FROM person_ledger WHERE user_id = ? AND person_id = ? AND type='settlement' AND status='approved' AND deleted=0", (firm_id, p['id'])).fetchone()[0] or 0.0
        owed = adv - setl
        if owed > 0:
            total_dasti_ledger += owed
            dasti_breakdown.append({'name': p['name'], 'amount': owed})

    conn.close()
    balance = total_in_actual - total_out_actual
    cats = get_categories(firm_id)
    return render_template_string(INDEX_TEMPLATE, persons=persons, dasti_persons=dasti_persons, incomes=incomes, expenses=expenses, balance=balance, total_dasti=total_dasti_ledger, dasti_breakdown=dasti_breakdown, categories=cats, s_d_in=s_d_in, s_d_out=s_d_out, s_w_in=s_w_in, s_w_out=s_w_out, s_m_in=s_m_in, s_m_out=s_m_out, s_y_in=s_y_in, s_y_out=s_y_out, username=session['username'], active_page='home')

@app.route('/main_ledger')
def main_ledger():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = sqlite3.connect('cashbook.db'); conn.row_factory = sqlite3.Row; c = conn.cursor(); firm_id = session['firm_id']

    txns = c.execute("SELECT * FROM transactions WHERE user_id = ? AND deleted=0 ORDER BY date DESC, time DESC, id DESC", (firm_id,)).fetchall()
    total_in = c.execute("SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type IN ('income', 'dasti_voucher_in') AND status='approved' AND deleted=0", (firm_id,)).fetchone()[0] or 0.0
    total_out = c.execute("SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type='expense' AND status='approved' AND deleted=0", (firm_id,)).fetchone()[0] or 0.0
    total_dasti = c.execute("SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type='dasti_out' AND status='approved' AND deleted=0", (firm_id,)).fetchone()[0] or 0.0
    total_dasti_vouchers = c.execute("SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type='dasti_voucher_out' AND status='approved' AND deleted=0", (firm_id,)).fetchone()[0] or 0.0

    conn.close()
    balance = total_in - (total_out + total_dasti + total_dasti_vouchers)
    return render_template_string(MAIN_LEDGER_TEMPLATE, txns=txns, balance=balance, total_in=total_in, total_out=total_out, total_dasti=total_dasti, total_dasti_vouchers=total_dasti_vouchers, username=session['username'], active_page='main_ledger')

@app.route('/dasti_ledger')
def dasti_ledger():
    if 'user_id' not in session: return redirect(url_for('login'))
    firm_id = session['firm_id']
    conn = sqlite3.connect('cashbook.db'); conn.row_factory = sqlite3.Row; c = conn.cursor()

    total_in = c.execute("SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type IN ('income', 'dasti_voucher_in') AND status='approved' AND deleted=0", (firm_id,)).fetchone()[0] or 0.0
    total_out = c.execute("SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type IN ('expense', 'dasti_out', 'dasti_voucher_out') AND status='approved' AND deleted=0", (firm_id,)).fetchone()[0] or 0.0
    main_balance = total_in - total_out

    dasti_persons = c.execute("SELECT * FROM dasti_persons WHERE user_id = ? ORDER BY name ASC", (firm_id,)).fetchall()
    balances = []
    total_outstanding_dasti = 0.0

    for p in dasti_persons:
        adv = c.execute("SELECT SUM(amount) FROM dasti_ledger WHERE user_id = ? AND dasti_person_id = ? AND type='advance' AND status='approved' AND deleted=0", (firm_id, p['id'])).fetchone()[0] or 0.0
        setl = c.execute("SELECT SUM(amount) FROM dasti_ledger WHERE user_id = ? AND dasti_person_id = ? AND type='settlement' AND status='approved' AND deleted=0", (firm_id, p['id'])).fetchone()[0] or 0.0
        net = adv - setl
        balances.append({'id': p['id'], 'name': p['name'], 'net': net})
        if net > 0:
            total_outstanding_dasti += net

    conn.close()
    return render_template_string(DASTI_LEDGER_TEMPLATE, balances=balances, balance=main_balance, total_outstanding_dasti=total_outstanding_dasti, username=session['username'], active_page='dasti_ledger')

@app.route('/dasti_account/<int:person_id>')
def dasti_account(person_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    firm_id = session['firm_id']
    conn = sqlite3.connect('cashbook.db'); conn.row_factory = sqlite3.Row; c = conn.cursor()
    person = c.execute("SELECT * FROM dasti_persons WHERE id = ? AND user_id = ?", (person_id, firm_id)).fetchone()
    if not person: conn.close(); return redirect(url_for('dasti_ledger'))

    txns = c.execute("SELECT * FROM dasti_ledger WHERE dasti_person_id = ? AND user_id = ? AND deleted=0 ORDER BY date DESC, time DESC, id DESC", (person_id, firm_id)).fetchall()
    advances = c.execute("SELECT SUM(amount) FROM dasti_ledger WHERE dasti_person_id = ? AND user_id = ? AND type='advance' AND status='approved' AND deleted=0", (person_id, firm_id)).fetchone()[0] or 0.0
    settlements = c.execute("SELECT SUM(amount) FROM dasti_ledger WHERE dasti_person_id = ? AND user_id = ? AND type='settlement' AND status='approved' AND deleted=0", (person_id, firm_id)).fetchone()[0] or 0.0
    conn.close()
    return render_template_string(DASTI_ACCOUNT_TEMPLATE, person=person, txns=txns, balance=(advances - settlements), advances=advances, settlements=settlements, username=session['username'], active_page='dasti_ledger')

@app.route('/edit_dasti_person/<int:id>')
def edit_dasti_person(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    new_name = request.args.get('name')
    if new_name:
        conn = sqlite3.connect('cashbook.db'); c = conn.cursor()
        c.execute("UPDATE dasti_persons SET name=? WHERE id=? AND user_id=?", (new_name, id, session['firm_id']))
        conn.commit(); conn.close()
    return redirect(url_for('dasti_ledger'))

@app.route('/persons')
def persons():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = sqlite3.connect('cashbook.db'); conn.row_factory = sqlite3.Row; c = conn.cursor(); firm_id = session['firm_id']
    person_list = c.execute("SELECT * FROM persons WHERE user_id = ? ORDER BY name ASC", (firm_id,)).fetchall()
    balances = []
    for p in person_list:
        advances = c.execute("SELECT SUM(amount) FROM person_ledger WHERE user_id = ? AND person_id = ? AND type='advance' AND status='approved' AND deleted=0", (firm_id, p['id'])).fetchone()[0] or 0.0
        settlements = c.execute("SELECT SUM(amount) FROM person_ledger WHERE user_id = ? AND person_id = ? AND type='settlement' AND status='approved' AND deleted=0", (firm_id, p['id'])).fetchone()[0] or 0.0
        balances.append({'id': p['id'], 'name': p['name'], 'net': advances - settlements})
    conn.close()
    return render_template_string(PERSONS_TEMPLATE, balances=balances, username=session['username'], active_page='persons')

@app.route('/person_account/<int:person_id>')
def person_account(person_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = sqlite3.connect('cashbook.db'); conn.row_factory = sqlite3.Row; c = conn.cursor(); firm_id = session['firm_id']
    person = c.execute("SELECT * FROM persons WHERE id = ? AND user_id = ?", (person_id, firm_id)).fetchone()
    if not person: conn.close(); return redirect(url_for('persons'))
    txns = c.execute("SELECT * FROM person_ledger WHERE person_id = ? AND user_id = ? AND deleted=0 ORDER BY date DESC, time DESC, id DESC", (person_id, firm_id)).fetchall()
    advances = c.execute("SELECT SUM(amount) FROM person_ledger WHERE person_id = ? AND user_id = ? AND type='advance' AND status='approved' AND deleted=0", (person_id, firm_id)).fetchone()[0] or 0.0
    settlements = c.execute("SELECT SUM(amount) FROM person_ledger WHERE person_id = ? AND user_id = ? AND type='settlement' AND status='approved' AND deleted=0", (person_id, firm_id)).fetchone()[0] or 0.0
    conn.close()
    return render_template_string(PERSON_ACCOUNT_TEMPLATE, person=person, txns=txns, balance=(advances - settlements), advances=advances, settlements=settlements, username=session['username'], active_page='persons')

@app.route('/edit_person/<int:id>')
def edit_person(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    new_name = request.args.get('name')
    if new_name:
        conn = sqlite3.connect('cashbook.db'); c = conn.cursor()
        c.execute("UPDATE persons SET name=? WHERE id=? AND user_id=?", (new_name, id, session['firm_id']))
        conn.commit(); conn.close()
    return redirect(url_for('persons'))

@app.route('/delete/<string:table_name>/<int:row_id>')
def delete_entry(table_name, row_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    if table_name not in ['transactions', 'person_ledger', 'dasti_ledger']: return "Invalid", 400
    conn = sqlite3.connect('cashbook.db'); c = conn.cursor()
    res = c.execute(f"SELECT link_id FROM {table_name} WHERE id=? AND user_id=?", (row_id, session['firm_id'])).fetchone()
    link_id = res[0] if res else ""
    if link_id:
        c.execute("UPDATE transactions SET deleted=1 WHERE link_id=? AND user_id=?", (link_id, session['firm_id']))
        c.execute("UPDATE person_ledger SET deleted=1 WHERE link_id=? AND user_id=?", (link_id, session['firm_id']))
        c.execute("UPDATE dasti_ledger SET deleted=1 WHERE link_id=? AND user_id=?", (link_id, session['firm_id']))
    else: c.execute(f"UPDATE {table_name} SET deleted=1 WHERE id=? AND user_id=?", (row_id, session['firm_id']))
    conn.commit(); conn.close()
    return redirect(request.referrer or url_for('index'))

@app.route('/trash')
def trash():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = sqlite3.connect('cashbook.db'); conn.row_factory = sqlite3.Row; c = conn.cursor()
    trashed = c.execute("SELECT * FROM transactions WHERE user_id=? AND deleted=1 ORDER BY date DESC, time DESC", (session['firm_id'],)).fetchall()
    conn.close()
    return render_template_string(TRASH_TEMPLATE, trashed=trashed, username=session['username'], active_page='trash')

@app.route('/restore_voucher/<string:link_id>')
def restore_voucher(link_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = sqlite3.connect('cashbook.db'); c = conn.cursor()
    c.execute("UPDATE transactions SET deleted=0 WHERE link_id=? AND user_id=?", (link_id, session['firm_id']))
    c.execute("UPDATE person_ledger SET deleted=0 WHERE link_id=? AND user_id=?", (link_id, session['firm_id']))
    c.execute("UPDATE dasti_ledger SET deleted=0 WHERE link_id=? AND user_id=?", (link_id, session['firm_id']))
    conn.commit(); conn.close()
    return redirect(url_for('trash'))

@app.route('/hard_delete_voucher/<string:link_id>')
def hard_delete_voucher(link_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = sqlite3.connect('cashbook.db'); c = conn.cursor()
    c.execute("DELETE FROM transactions WHERE link_id=? AND user_id=?", (link_id, session['firm_id']))
    c.execute("DELETE FROM person_ledger WHERE link_id=? AND user_id=?", (link_id, session['firm_id']))
    c.execute("DELETE FROM dasti_ledger WHERE link_id=? AND user_id=?", (link_id, session['firm_id']))
    conn.commit(); conn.close()
    return redirect(url_for('trash'))

@app.route('/reports')
def reports():
    if 'user_id' not in session: return redirect(url_for('login'))
    firm_id = session['firm_id']
    conn = sqlite3.connect('cashbook.db'); conn.row_factory = sqlite3.Row; c = conn.cursor()

    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    category = request.args.get('category', '')
    report_account = request.args.get('report_account', 'main')

    query = "SELECT * FROM transactions WHERE user_id=? AND deleted=0 AND status='approved'"
    params = [firm_id]

    if report_account.startswith('person_'):
        pid = report_account.split('_')[1]
        query = "SELECT * FROM person_ledger WHERE user_id=? AND person_id=? AND deleted=0 AND status='approved'"
        params = [firm_id, pid]
    elif report_account.startswith('dasti_'):
        did = report_account.split('_')[1]
        query = "SELECT * FROM dasti_ledger WHERE user_id=? AND dasti_person_id=? AND deleted=0 AND status='approved'"
        params = [firm_id, did]

    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    if category:
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY date DESC, time DESC"
    results = c.execute(query, tuple(params)).fetchall()

    total_in = sum(r['amount'] for r in results if r['type'] in ('income', 'settlement', 'dasti_voucher_in'))

    # Reports should only sum physical money out, bypass 'batch_ledger_out' (Slips) to prevent double counting
    total_out = sum(r['amount'] for r in results if r['type'] in ('expense', 'advance', 'dasti_out', 'dasti_voucher_out'))

    persons = c.execute("SELECT * FROM persons WHERE user_id = ? ORDER BY name ASC", (firm_id,)).fetchall()
    dasti_persons = c.execute("SELECT * FROM dasti_persons WHERE user_id = ? ORDER BY name ASC", (firm_id,)).fetchall()
    cats = get_categories(firm_id)

    conn.close()
    return render_template_string(REPORTS_TEMPLATE, results=results, total_in=total_in, total_out=total_out, categories=cats, persons=persons, dasti_persons=dasti_persons, start_date=start_date, end_date=end_date, category=category, report_account=report_account, username=session['username'], active_page='reports')

@app.route('/export_reports')
def export_reports():
    if 'user_id' not in session: return redirect(url_for('login'))
    firm_id = session['firm_id']
    conn = sqlite3.connect('cashbook.db'); conn.row_factory = sqlite3.Row; c = conn.cursor()

    start_date, end_date, category, report_account = request.args.get('start_date', ''), request.args.get('end_date', ''), request.args.get('category', ''), request.args.get('report_account', 'main')

    query = "SELECT date, time, payment_mode, category, description, type, amount, approved_by FROM transactions WHERE user_id=? AND deleted=0 AND status='approved'"
    params = [firm_id]
    if report_account.startswith('person_'):
        pid = report_account.split('_')[1]
        query = "SELECT date, time, payment_mode, category, description, type, amount, approved_by FROM person_ledger WHERE user_id=? AND person_id=? AND deleted=0 AND status='approved'"
        params = [firm_id, pid]
    elif report_account.startswith('dasti_'):
        did = report_account.split('_')[1]
        query = "SELECT date, time, payment_mode, category, description, type, amount, approved_by FROM dasti_ledger WHERE user_id=? AND dasti_person_id=? AND deleted=0 AND status='approved'"
        params = [firm_id, did]

    if start_date: query += " AND date >= ?"; params.append(start_date)
    if end_date: query += " AND date <= ?"; params.append(end_date)
    if category: query += " AND category = ?"; params.append(category)
    query += " ORDER BY date ASC, time ASC"

    results = c.execute(query, tuple(params)).fetchall()
    conn.close()

    def generate():
        data = StringIO()
        writer = csv.writer(data)
        writer.writerow(('Date', 'Time', 'Mode', 'Category', 'Description', 'Type', 'Amount (INR)', 'Approved By'))
        yield data.getvalue(); data.seek(0); data.truncate(0)
        for r in results:
            writer.writerow((r['date'], r['time'], r['payment_mode'], r['category'], r['description'], r['type'], r['amount'], r['approved_by']))
            yield data.getvalue(); data.seek(0); data.truncate(0)

    return Response(generate(), mimetype='text/csv', headers={"Content-Disposition": "attachment; filename=Firm_Report_Export.csv"})

@app.route('/download_cash_json')
def download_cash_json():
    if 'user_id' not in session or session.get('role') != 'superadmin': return redirect(url_for('index'))
    conn = sqlite3.connect('cashbook.db'); conn.row_factory = sqlite3.Row; c = conn.cursor()
    data = {
        "users": [dict(row) for row in c.execute("SELECT * FROM users").fetchall()],
        "categories": [dict(row) for row in c.execute("SELECT * FROM categories").fetchall()],
        "persons": [dict(row) for row in c.execute("SELECT * FROM persons").fetchall()],
        "dasti_persons": [dict(row) for row in c.execute("SELECT * FROM dasti_persons").fetchall()],
        "transactions": [dict(row) for row in c.execute("SELECT * FROM transactions").fetchall()],
        "person_ledger": [dict(row) for row in c.execute("SELECT * FROM person_ledger").fetchall()],
        "dasti_ledger": [dict(row) for row in c.execute("SELECT * FROM dasti_ledger").fetchall()]
    }
    conn.close()
    return Response(json.dumps(data, indent=4), mimetype='application/json', headers={"Content-Disposition": "attachment; filename=cash.json"})

@app.route('/edit/<string:table_name>/<int:row_id>', methods=['GET', 'POST'])
def edit_entry(table_name, row_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    if table_name not in ['transactions', 'person_ledger', 'dasti_ledger']: return "Invalid", 400
    conn = sqlite3.connect('cashbook.db'); conn.row_factory = sqlite3.Row; c = conn.cursor()
    entry = c.execute(f"SELECT * FROM {table_name} WHERE id=? AND user_id=?", (row_id, session['firm_id'])).fetchone()

    if request.method == 'POST':
        date, time_v, mode, cat, desc, req_type, amt = request.form['date'], request.form['time'], request.form['payment_mode'], request.form['category'], request.form['description'], request.form['type'], float(request.form['amount'])
        approved_by = request.form.get('approved_by', entry['approved_by']) # Manual Admin Override

        if entry['link_id']:
            c.execute("UPDATE transactions SET date=?, time=?, payment_mode=?, category=?, amount=?, approved_by=? WHERE link_id=? AND user_id=?", (date, time_v, mode, cat, amt, approved_by, entry['link_id'], session['firm_id']))
            c.execute("UPDATE person_ledger SET date=?, time=?, payment_mode=?, category=?, amount=?, approved_by=? WHERE link_id=? AND user_id=?", (date, time_v, mode, cat, amt, approved_by, entry['link_id'], session['firm_id']))
            c.execute("UPDATE dasti_ledger SET date=?, time=?, payment_mode=?, category=?, amount=?, approved_by=? WHERE link_id=? AND user_id=?", (date, time_v, mode, cat, amt, approved_by, entry['link_id'], session['firm_id']))
        else:
            c.execute(f"UPDATE {table_name} SET date=?, time=?, payment_mode=?, category=?, description=?, type=?, amount=?, approved_by=? WHERE id=? AND user_id=?", (date, time_v, mode, cat, desc, req_type, amt, approved_by, row_id, session['firm_id']))
        conn.commit(); conn.close()
        return redirect(request.referrer or url_for('index'))
    conn.close()
    return render_template_string(EDIT_TEMPLATE, entry=entry, table_name=table_name, username=session['username'])

@app.route('/manage_users')
def manage_users():
    if 'user_id' not in session or session.get('role') != 'superadmin': return redirect(url_for('index'))
    conn = sqlite3.connect('cashbook.db'); conn.row_factory = sqlite3.Row; c = conn.cursor()
    users = c.execute("SELECT id, username, role, can_approve FROM users WHERE firm_id=?", (session['firm_id'],)).fetchall()
    conn.close()
    return render_template_string(USERS_TEMPLATE, users=users, username=session['username'], active_page='users')

@app.route('/edit_user/<int:uid>', methods=['GET', 'POST'])
def edit_user(uid):
    if 'user_id' not in session or session.get('role') != 'superadmin': return redirect(url_for('index'))
    conn = sqlite3.connect('cashbook.db'); conn.row_factory = sqlite3.Row; c = conn.cursor()

    if request.method == 'POST':
        uname = request.form['username']
        role = request.form['role']
        can_app = int(request.form.get('can_approve', 0))
        new_pw = request.form.get('password', '').strip()

        if new_pw:
            c.execute("UPDATE users SET username=?, role=?, can_approve=?, password=? WHERE id=? AND firm_id=?", (uname, role, can_app, generate_password_hash(new_pw), uid, session['firm_id']))
        else:
            c.execute("UPDATE users SET username=?, role=?, can_approve=? WHERE id=? AND firm_id=?", (uname, role, can_app, uid, session['firm_id']))
        conn.commit(); conn.close()
        return redirect(url_for('manage_users'))

    user_data = c.execute("SELECT * FROM users WHERE id=? AND firm_id=?", (uid, session['firm_id'])).fetchone()
    conn.close()
    return render_template_string(EDIT_USER_TEMPLATE, edit_user=user_data, username=session['username'], active_page='users')

@app.route('/add_user', methods=['POST'])
def add_user():
    if 'user_id' not in session or session.get('role') != 'superadmin': return redirect(url_for('index'))
    conn = sqlite3.connect('cashbook.db'); c = conn.cursor()
    c.execute("INSERT INTO users (username, password, firm_name, firm_id, role, can_approve) VALUES (?, ?, ?, ?, ?, ?)",
              (request.form['new_username'], generate_password_hash(request.form['new_password']), session['firm_name'], session['firm_id'], request.form['role'], int(request.form.get('can_approve', 0))))
    conn.commit(); conn.close()
    return redirect(url_for('manage_users'))

@app.route('/approvals')
def approvals():
    if 'user_id' not in session or session.get('can_approve') != 1: return redirect(url_for('index'))
    conn = sqlite3.connect('cashbook.db'); conn.row_factory = sqlite3.Row; c = conn.cursor()
    pending = c.execute("SELECT * FROM transactions WHERE user_id=? AND status='pending' AND deleted=0 ORDER BY id DESC", (session['firm_id'],)).fetchall()
    conn.close()
    return render_template_string(APPROVALS_TEMPLATE, pending=pending, username=session['username'], active_page='approvals')

@app.route('/approve_voucher/<string:link_id>')
def approve_voucher(link_id):
    if 'user_id' not in session or session.get('can_approve') != 1: return redirect(url_for('index'))
    conn = sqlite3.connect('cashbook.db'); c = conn.cursor()
    c.execute("UPDATE transactions SET status='approved', approved_by=? WHERE link_id=? AND user_id=?", (session['username'], link_id, session['firm_id']))
    c.execute("UPDATE person_ledger SET status='approved', approved_by=? WHERE link_id=? AND user_id=?", (session['username'], link_id, session['firm_id']))
    c.execute("UPDATE dasti_ledger SET status='approved', approved_by=? WHERE link_id=? AND user_id=?", (session['username'], link_id, session['firm_id']))
    conn.commit(); conn.close()
    return redirect(request.referrer or url_for('approvals'))

@app.route('/reject_voucher/<string:link_id>')
def reject_voucher(link_id):
    if 'user_id' not in session or session.get('can_approve') != 1: return redirect(url_for('index'))
    conn = sqlite3.connect('cashbook.db'); c = conn.cursor()
    c.execute("UPDATE transactions SET deleted=1 WHERE link_id=? AND user_id=?", (link_id, session['firm_id']))
    c.execute("UPDATE person_ledger SET deleted=1 WHERE link_id=? AND user_id=?", (link_id, session['firm_id']))
    c.execute("UPDATE dasti_ledger SET deleted=1 WHERE link_id=? AND user_id=?", (link_id, session['firm_id']))
    conn.commit(); conn.close()
    return redirect(request.referrer or url_for('approvals'))

@app.route('/add_express', methods=['POST'])
def add_express():
    if 'user_id' not in session: return redirect(url_for('login'))
    txn_status = 'approved' if session.get('can_approve') == 1 else 'pending'
    approver = session['username'] if txn_status == 'approved' else ''

    conn = sqlite3.connect('cashbook.db'); c = conn.cursor()
    link_id = uuid.uuid4().hex[:12]
    c.execute("INSERT INTO transactions (user_id, date, time, payment_mode, category, description, type, amount, link_id, status, approved_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
              (session['firm_id'], request.form['date'], request.form['time'], 'Cash', 'General', request.form['description'], request.form['type'], float(request.form['amount']), link_id, txn_status, approver))
    conn.commit(); conn.close()
    return redirect(request.referrer or url_for('index'))

@app.route('/add_transfer', methods=['POST'])
def add_transfer():
    if 'user_id' not in session: return redirect(url_for('login'))
    firm_id = session['firm_id']
    date_val, time_val, direction, person_id = request.form['date'], request.form['time'], request.form['direction'], request.form['person_id']
    desc, amt = request.form['description'].strip(), float(request.form['amount'])

    txn_status = 'approved' if session.get('can_approve') == 1 else 'pending'
    approver = session['username'] if txn_status == 'approved' else ''

    conn = sqlite3.connect('cashbook.db'); conn.row_factory = sqlite3.Row; c = conn.cursor()
    person = c.execute("SELECT name FROM persons WHERE id = ? AND user_id = ?", (person_id, firm_id)).fetchone()
    if not person: conn.close(); return redirect(request.referrer)

    person_name, link_id = person['name'], uuid.uuid4().hex[:12]

    if direction == 'main_to_person':
        c.execute("INSERT INTO transactions (user_id, date, time, payment_mode, category, description, type, amount, link_id, status, approved_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (firm_id, date_val, time_val, 'Cash', 'General', f"Transfer to {person_name}: {desc}", 'dasti_out', amt, link_id, txn_status, approver))
        c.execute("INSERT INTO person_ledger (user_id, person_id, date, time, payment_mode, category, description, type, amount, link_id, status, approved_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (firm_id, person_id, date_val, time_val, 'Cash', 'General', f"Rcvd from Main: {desc}", 'advance', amt, link_id, txn_status, approver))
    else:
        c.execute("INSERT INTO person_ledger (user_id, person_id, date, time, payment_mode, category, description, type, amount, link_id, status, approved_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (firm_id, person_id, date_val, time_val, 'Cash', 'General', f"Paid to Main: {desc}", 'settlement', amt, link_id, txn_status, approver))
        c.execute("INSERT INTO transactions (user_id, date, time, payment_mode, category, description, type, amount, link_id, status, approved_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (firm_id, date_val, time_val, 'Cash', 'General', f"Transfer from {person_name}: {desc}", 'income', amt, link_id, txn_status, approver))

    conn.commit(); conn.close()
    return redirect(request.referrer or url_for('index'))

@app.route('/add_batch_unified', methods=['POST'])
def add_batch_unified():
    if 'user_id' not in session: return redirect(url_for('login'))
    firm_id = session['firm_id']
    date_val, time_val, mode, txn_nature = request.form['date'], request.form['time'], request.form['payment_mode'], request.form['txn_nature']
    primary_account_raw = request.form['primary_account']
    new_account_name = request.form.get('new_account_name', '').strip()

    cats, cust_cats, descs, amts = request.form.getlist('category[]'), request.form.getlist('custom_category[]'), request.form.getlist('description[]'), request.form.getlist('amount[]')

    txn_status = 'approved' if session.get('can_approve') == 1 else 'pending'
    approver = session['username'] if txn_status == 'approved' else ''

    conn = sqlite3.connect('cashbook.db'); conn.row_factory = sqlite3.Row; c = conn.cursor()
    existing_cats = get_categories(firm_id)
    account_type = 'main'
    primary_id = None
    person_name = ''

    if primary_account_raw == 'new_dasti':
        c.execute("INSERT INTO dasti_persons (user_id, name) VALUES (?, ?)", (firm_id, new_account_name))
        primary_id = c.lastrowid
        account_type, person_name = 'dasti', new_account_name
    elif primary_account_raw == 'new_person':
        c.execute("INSERT INTO persons (user_id, name) VALUES (?, ?)", (firm_id, new_account_name))
        primary_id = c.lastrowid
        account_type, person_name = 'person', new_account_name
    elif primary_account_raw.startswith('person_'):
        primary_id = int(primary_account_raw.split('_')[1])
        account_type = 'person'
        res = c.execute("SELECT name FROM persons WHERE id=? AND user_id=?", (primary_id, firm_id)).fetchone()
        if res: person_name = res['name']
    elif primary_account_raw.startswith('dasti_'):
        primary_id = int(primary_account_raw.split('_')[1])
        account_type = 'dasti'
        res = c.execute("SELECT name FROM dasti_persons WHERE id=? AND user_id=?", (primary_id, firm_id)).fetchone()
        if res: person_name = res['name']

    for i in range(len(descs)):
        if amts[i].strip() and float(amts[i]) >= 0:
            amt, desc = float(amts[i]), descs[i].strip()
            cat = cust_cats[i].strip() if cats[i] == 'Other' and cust_cats[i].strip() else cats[i]
            if cat not in existing_cats:
                try: c.execute("INSERT INTO categories (firm_id, name) VALUES (?, ?)", (firm_id, cat))
                except sqlite3.IntegrityError: pass
            link_id = uuid.uuid4().hex[:12]

            if account_type == 'main':
                db_type = 'income' if txn_nature == 'receive_cash' else 'expense'
                c.execute("INSERT INTO transactions (user_id, date, time, payment_mode, category, description, type, amount, link_id, status, approved_by) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (firm_id, date_val, time_val, mode, cat, desc, db_type, amt, link_id, txn_status, approver))
            elif account_type == 'person':
                if txn_nature == 'slip_in':
                    c.execute("INSERT INTO person_ledger (user_id, person_id, date, time, payment_mode, category, description, type, amount, link_id, status, approved_by) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (firm_id, primary_id, date_val, time_val, mode, cat, desc, 'settlement', amt, link_id, txn_status, approver))
                    c.execute("INSERT INTO transactions (user_id, date, time, payment_mode, category, description, type, amount, link_id, status, approved_by) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (firm_id, date_val, time_val, mode, cat, f"Slip ({person_name}): {desc}", 'batch_ledger_out', amt, link_id, txn_status, approver))
                elif txn_nature == 'advance':
                    c.execute("INSERT INTO person_ledger (user_id, person_id, date, time, payment_mode, category, description, type, amount, link_id, status, approved_by) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (firm_id, primary_id, date_val, time_val, mode, cat, desc, 'advance', amt, link_id, txn_status, approver))
                    c.execute("INSERT INTO transactions (user_id, date, time, payment_mode, category, description, type, amount, link_id, status, approved_by) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (firm_id, date_val, time_val, mode, cat, f"Transfer Out ({person_name}): {desc}", 'dasti_out', amt, link_id, txn_status, approver))
                elif txn_nature == 'receive_cash':
                    c.execute("INSERT INTO person_ledger (user_id, person_id, date, time, payment_mode, category, description, type, amount, link_id, status, approved_by) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (firm_id, primary_id, date_val, time_val, mode, cat, desc, 'settlement', amt, link_id, txn_status, approver))
                    c.execute("INSERT INTO transactions (user_id, date, time, payment_mode, category, description, type, amount, link_id, status, approved_by) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (firm_id, date_val, time_val, mode, cat, f"Transfer In ({person_name}): {desc}", 'income', amt, link_id, txn_status, approver))
            elif account_type == 'dasti':
                if txn_nature == 'slip_in':
                    c.execute("INSERT INTO dasti_ledger (user_id, dasti_person_id, date, time, payment_mode, category, description, type, amount, link_id, status, approved_by) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (firm_id, primary_id, date_val, time_val, mode, cat, desc, 'settlement', amt, link_id, txn_status, approver))
                    c.execute("INSERT INTO transactions (user_id, date, time, payment_mode, category, description, type, amount, link_id, status, approved_by) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (firm_id, date_val, time_val, mode, cat, f"Dasti Slip ({person_name}): {desc}", 'batch_ledger_out', amt, link_id, txn_status, approver))
                elif txn_nature == 'advance':
                    c.execute("INSERT INTO dasti_ledger (user_id, dasti_person_id, date, time, payment_mode, category, description, type, amount, link_id, status, approved_by) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (firm_id, primary_id, date_val, time_val, mode, cat, desc, 'advance', amt, link_id, txn_status, approver))
                    c.execute("INSERT INTO transactions (user_id, date, time, payment_mode, category, description, type, amount, link_id, status, approved_by) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (firm_id, date_val, time_val, mode, cat, f"Dasti Out ({person_name}): {desc}", 'dasti_voucher_out', amt, link_id, txn_status, approver))
                elif txn_nature == 'receive_cash':
                    c.execute("INSERT INTO dasti_ledger (user_id, dasti_person_id, date, time, payment_mode, category, description, type, amount, link_id, status, approved_by) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (firm_id, primary_id, date_val, time_val, mode, cat, desc, 'settlement', amt, link_id, txn_status, approver))
                    c.execute("INSERT INTO transactions (user_id, date, time, payment_mode, category, description, type, amount, link_id, status, approved_by) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (firm_id, date_val, time_val, mode, cat, f"Dasti In ({person_name}): {desc}", 'dasti_voucher_in', amt, link_id, txn_status, approver))
    conn.commit(); conn.close()
    return redirect(request.referrer or url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if not has_users(): return redirect(url_for('register'))
    if request.method == 'POST':
        conn = sqlite3.connect('cashbook.db'); conn.row_factory = sqlite3.Row; c = conn.cursor()
        user = c.execute("SELECT * FROM users WHERE username = ?", (request.form['username'],)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], request.form['password']):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['firm_name'] = user['firm_name']
            session['firm_id'] = user['firm_id'] or user['id']
            session['role'] = user['role']
            session['can_approve'] = user['can_approve']
            return redirect(url_for('index'))
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if has_users(): return "Setup complete. Ask the Superadmin to create an account for you.", 403
    if request.method == 'POST':
        conn = sqlite3.connect('cashbook.db'); c = conn.cursor()
        c.execute("INSERT INTO users (username, password, firm_name, role, can_approve) VALUES (?, ?, ?, 'superadmin', 1)", (request.form['username'], generate_password_hash(request.form['password']), request.form['firm_name']))
        user_id = c.lastrowid
        c.execute("UPDATE users SET firm_id = ? WHERE id = ?", (user_id, user_id))

        session['user_id'], session['firm_id'], session['username'], session['firm_name'] = user_id, user_id, request.form['username'], request.form['firm_name']
        session['role'], session['can_approve'] = 'superadmin', 1

        opening_balance = float(request.form.get('opening_balance', 0))
        if opening_balance > 0:
            now = datetime.now()
            c.execute("INSERT INTO transactions (user_id, date, time, payment_mode, category, description, type, amount, link_id, status, approved_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'approved', ?)",
                      (user_id, now.strftime('%Y-%m-%d'), now.strftime('%H:%M'), 'Cash', 'General', 'Opening Balance', 'income', opening_balance, uuid.uuid4().hex[:12], session['username']))

        conn.commit(); conn.close()
        return redirect(url_for('index'))
    return render_template_string(REGISTER_TEMPLATE)

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
