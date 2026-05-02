from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import datetime, date
from abc import ABC, abstractmethod

app = Flask(__name__)
app.secret_key = "Secret123"


# ==========================================
#  ABSTRACTION + ENCAPSULATION (BASE CLASS)
# ===========================================
class Person(ABC):
    def __init__(self, name):
        self._name = name  # Encapsulation

    def get_name(self):
        return self._name

    # ABSTRACT METHOD 
    @abstractmethod
    def display_role(self):
        pass


# ========================================
# USER CLASS (INHERITANCE + POLYMORPHISM)
# =========================================
class User(Person):
    def __init__(self, username, password, role, linked_emp_id=None):
        super().__init__(username)  # Inheritance
        self._password = password
        self._role = role.lower()
        self.linked_emp_id = linked_emp_id

    def get_username(self):
        return self._name

    def get_role(self):
        return self._role.capitalize()

    def check_login(self, input_user, input_pass):
        return self._name == input_user and self._password == input_pass

    # Polymorphism (override)
    def display_role(self):
        return f"User Role: {self.get_role()}"


# =====================================================
# EMPLOYEE CLASS (INHERITANCE + ENCAPSULATION + POLYMORPHISM)
# =====================================================
class Employee(Person):
    employee_data = {}

    def __init__(self, emp_id, name, address, contact):
        super().__init__(name)  # Inheritance
        self._emp_id = str(emp_id)
        self._address = address
        self._contact = contact
        self.leave_credits = 10

    # Encapsulation (getters)
    def get_emp_id(self): return self._emp_id
    def get_address(self): return self._address
    def get_contact(self): return self._contact

    def update_emp_info(self, new_name, new_address, new_contact):
        if new_name:
            self._name = new_name
        if new_address:
            self._address = new_address
        if new_contact:
            self._contact = new_contact

    # Polymorphism
    def display_role(self):
        return "Employee"

    # Abstraction 
    @classmethod
    def add_new_employee(cls, name, emp_id, address, contact, user_name, user_password):
        if str(emp_id) in cls.employee_data:
            return False

        emp = Employee(emp_id, name, address, contact)
        cls.employee_data[str(emp_id)] = emp

        users_db.append(User(user_name, user_password, "Employee", str(emp_id)))
        return True


# ===========================
#  LEAVE SYSTEM (ABSTRACTION)
# ============================
class LeaveSystem:
    leave_requests = []

    @classmethod
    def apply_leave(cls, name, emp_id, reason, leave_date):
        cls.leave_requests.append({
            "name": name,
            "id": str(emp_id),
            "leave_date": leave_date,
            "reason": reason,
            "type": "Leave Request",
            "status": "Pending",
            "date_submitted": datetime.now().strftime("%Y-%m-%d")
        })

    @classmethod
    def request_cancellation(cls, index, reason):
        if 0 <= index < len(cls.leave_requests):
            req = cls.leave_requests[index]
            req['status'] = "Pending Cancellation"
            req['cancel_reason'] = reason
            req['type'] = "Cancellation"
            return True
        return False


# =============
#  DATABASE 
# ============
users_db = [
    User("admin", "admin123", "admin", linked_emp_id="0"),
    User("employee", "employee123", "employee", linked_emp_id="101")
]

Employee.employee_data["101"] = Employee("101", "Juan Dela Cruz", "Manila", "09123456789")


# =======
# ROUTES
# =======
@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        active_user = next((u for u in users_db if u.check_login(username, password)), None)

        if active_user:
            session['user_id'] = active_user.linked_emp_id
            session['role'] = active_user.get_role()
            session['username'] = active_user.get_username()

            # POLYMORPHISM 
            flash(active_user.display_role(), "info")

            if session['role'] == 'Admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('employee_dashboard'))

        # 
        return render_template('login.html', error='Invalid username or password')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# =====================================================
# MODULE 1: ADMIN DASHBOARD and ACTION SELECTION
# =====================================================
@app.route('/admindashboard')
def admin_dashboard():
    if session.get('role') != 'Admin':
        return redirect(url_for('login'))

    #=================================
    #MODULE 4: VIEW ALL EMPLOYEE LIST
    #=================================
    all_emps = list(Employee.employee_data.values())
    leave_reqs = LeaveSystem.leave_requests
    
    #==============================================
    #MODULE 6: VIEW REPORTS (SEARCH FUNCTIONALITY)
    #==============================================
    query = request.args.get('search', '').lower()
    reports = [e for e in all_emps if query in e.get_name().lower()] if query else all_emps

    return render_template(
        'admindashboard.html',employees=all_emps,leaves=leave_reqs,reports=reports,enumerate=enumerate)


# =====================================================
# MODULE 2: REGISTER NEW EMPLOYEE
# =====================================================
@app.route('/register_employee', methods=['POST'])
def register_employee():
    if session.get('role') != 'Admin':
        return redirect(url_for('login'))

    name = request.form.get('name')
    emp_id = request.form.get('emp_id')
    address = request.form.get('address')
    contact = request.form.get('contact_no')
    username = request.form.get('username')
    password = request.form.get('password')

    if Employee.add_new_employee(name, emp_id, address, contact, username, password):
        flash("Employee registered successfully!", "success")
    else:
        flash("Error: Employee ID already exists!", "danger")

    return redirect(url_for('admin_dashboard'))


# =====================================================
# MODULE 3: EDIT EMPLOYEE INFORMATION
# =====================================================
@app.route('/update_employee', methods=['POST'])
def update_employee():
    if session.get('role') != 'Admin':
        return redirect(url_for('login'))

    emp_id = request.form.get('emp_id')
    name = request.form.get('name')
    address = request.form.get('address')
    contact = request.form.get('contact')

    emp = Employee.employee_data.get(str(emp_id))

    if emp:
        emp.update_emp_info(name, address, contact)
        flash("Employee updated successfully!", "success")
    else:
        flash("Employee not found.", "danger")

    return redirect(url_for('admin_dashboard'))


# =====================================================
# MODULE 5: ADMIN APPROVAL PROCESS
# =====================================================
@app.route('/handle_leave/<int:index>/<string:action>')
def handle_leave(index, action):

    if session.get('role') != 'Admin':
        return redirect(url_for('login'))

    if 0 <= index < len(LeaveSystem.leave_requests):

        req = LeaveSystem.leave_requests[index]
        emp = Employee.employee_data.get(str(req['id']))

        if req['status'] not in ['Pending', 'Pending Cancellation']:
            flash("This request has already been processed.", "info")
            return redirect(url_for('admin_dashboard'))

        if action == 'approve':

            if req.get('type') == "Cancellation":
                req['status'] = "Cancelled"
                if emp: emp.leave_credits += 1
                flash("Cancellation Approved. Credit restored.", "success")

            else:
                req['status'] = "Approved"
                if emp: emp.leave_credits -= 1
                flash("Leave Approved. Credit deducted.", "success")

        elif action == 'reject':

            if req.get('type') == "Cancellation":
                req['status'] = "Approved"
                req['type'] = "Leave Request"
                flash("Cancellation Rejected.", "info")

            else:
                req['status'] = "Rejected"
                flash("Leave Request Rejected.", "warning")

    return redirect(url_for('admin_dashboard'))


# =====================================================
# MODULE 7: EMPLOYEE DASHBOARD
# =====================================================
@app.route('/employee_dashboard')
def employee_dashboard():

    emp_id = session.get('user_id')

    if not emp_id:
        flash("Please login first.", "warning")
        return redirect(url_for('login'))

    emp_info = Employee.employee_data.get(str(emp_id))

   # ============================
   # MODULE 9: View Leave History
   # ============================
    emp_history = [
        (i, req) for i, req in enumerate(LeaveSystem.leave_requests)
        if str(req.get('id')) == str(emp_id)
    ]

    return render_template(
        'employee_dashboard.html',
        employee=emp_info,
        history=emp_history,
        enumerate=enumerate
    )


# =====================================================
# MODULE 8: APPLY LEAVE REQUEST
# =====================================================
@app.route('/apply_leave', methods=['POST'])
def apply_leave():

    emp_id = session.get('user_id')
    emp_info = Employee.employee_data.get(str(emp_id))

    if not emp_info:
        flash("Error: Invalid employee session.", "danger")
        return redirect(url_for('employee_dashboard'))

    reason = request.form.get('reason')
    leave_date = request.form.get('leave_date')

    # check missing inputs
    if not reason:
        flash("Error: Please provide a reason.", "warning")
        return redirect(url_for('employee_dashboard'))

    if not leave_date:
        flash("Error: Please provide a leave date.", "warning")
        return redirect(url_for('employee_dashboard'))

    # ✅ convert date safely
    try:
        leave_date_obj = datetime.strptime(leave_date, "%Y-%m-%d").date()
    except ValueError:
        flash("Error: Invalid date format.", "danger")
        return redirect(url_for('employee_dashboard'))

    #BLOCK PAST DATES (IMPORTANT)
    if leave_date_obj < date.today():
        flash("Error: You cannot apply for past dates.", "danger")
        return redirect(url_for('employee_dashboard'))

    # apply leave only if all checks pass
    LeaveSystem.apply_leave(
        emp_info.get_name(),
        emp_id,
        reason,
        leave_date
    )

    flash("Leave request submitted successfully!", "success")
    return redirect(url_for('employee_dashboard'))

# =====================================================
# MODULE 10: LEAVE CANCELLATION
# =====================================================
@app.route('/cancel_leave/<int:index>', methods=['POST'])
def cancel_leave(index):

    emp_id = session.get('user_id')
    req = LeaveSystem.leave_requests[index]

    if str(req.get('id')) != str(emp_id):
        flash("Unauthorized action.", "danger")
        return redirect(url_for('employee_dashboard'))

    reason = request.form.get('cancel_reason')

    if LeaveSystem.request_cancellation(index, reason):
        flash("Cancellation request sent to HR.", "success")
    else:
        flash("Error: Cannot cancel request.", "danger")

    return redirect(url_for('employee_dashboard'))


if __name__ == '__main__':
    app.run(debug=True)