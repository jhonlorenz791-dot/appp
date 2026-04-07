from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import datetime, date

app = Flask(__name__)
app.secret_key = "Secret123"

# --- CLASSES ---

class User:
    def __init__(self, username, password, role, linked_emp_id=None):
        self._username = username
        self._password = password  
        self._role = role.lower()
        self.linked_emp_id = linked_emp_id

    def get_username(self):
        return self._username

    def get_role(self):
        return self._role.capitalize()

    def check_login(self, input_user, input_pass):
        return self._username == input_user and self._password == input_pass

class Employee:
    employee_data = {} 

    def __init__(self, emp_id, name, address, contact):
        self._emp_id = str(emp_id)
        self._name = name
        self._address = address
        self._contact = contact
        self.leave_credits = 10 

    def get_emp_id(self): return self._emp_id
    def get_name(self): return self._name
    def get_address(self): return self._address
    def get_contact(self): return self._contact

    def update_emp_info(self, new_name, new_address, new_contact):
        if new_name: self._name = new_name
        if new_address: self._address = new_address
        if new_contact: self._contact = new_contact

    @classmethod
    def add_new_employee(cls, name, emp_id, address, contact, user_name, user_password):
        if str(emp_id) in cls.employee_data:
            return False
        new_emp = Employee(emp_id, name, address, contact)
        cls.employee_data[str(emp_id)] = new_emp
        users_db.append(User(user_name, user_password, "Employee", linked_emp_id=str(emp_id)))
        return True

class LeaveSystem:
    leave_requests = [] 
    
    @classmethod
    def apply_leave(cls, name, emp_id, reason, leave_date, req_type="Leave Request"):
        request_data = {
            "name": name,
            "id": str(emp_id),
            "leave_date": leave_date,
            "reason": reason, 
            "type": req_type,
            "status": "Pending",
            "date_submitted": datetime.now().strftime("%Y-%m-%d")
        }
        cls.leave_requests.append(request_data)
    
    @classmethod
    def request_cancellation(cls, index, reason):
        if 0 <= index < len(cls.leave_requests):
            req = cls.leave_requests[index]
            # Flowchart Logic: Update to Pending Cancellation
            req['status'] = "Pending Cancellation"
            req['cancel_reason'] = reason
            req['type'] = "Cancellation"
            return True
        return False

# --- DATABASE INITIALIZATION ---

users_db = [
    User("admin", "admin123", "admin"),
    User("employee", "employee123", "employee", linked_emp_id="101")
]
# Initial data para sa testing
Employee.employee_data["101"] = Employee("101", "Juan Dela Cruz", "Manila", "09123456789")

# --- ROUTES ---

@app.route('/')
def index():
    return redirect(url_for('login'))

#MODULE 1: AUTHENTICATION LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Hanapin ang user sa database
        active_user = next((u for u in users_db if u.check_login(username, password)), None)

        if active_user:
            session['user_id'] = active_user.linked_emp_id 
            session['role'] = active_user.get_role() # "Admin" o "Employee"
            session['username'] = active_user.get_username()
            
            if session['role'] == 'Admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('employee_dashboard'))
        
        # kung wrong ang password/username, mobalik sa login nga naay error message 
        return render_template('login.html', error='Invalid username or password')

   
    return render_template('login.html')  

#LOGOUT
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for('login'))

# --- ADMIN ROUTES ---

#ADMIN DASHBOARD
@app.route('/admindashboard')
def admin_dashboard():
    if session.get('role') != 'Admin':       #Security Check
        return redirect(url_for('login'))

    #Kuhaon tanang employee data para ma-display sa admin dashboard
    all_emps = list(Employee.employee_data.values())

    #Kuhaon tanang leave requests para ma-display sa admin dashboard
    leave_reqs = LeaveSystem.leave_requests

    #kuhaon ang search query gikan sa URL parameters, default empty string kung walay gi-provide          
    query = request.args.get('search', '').lower() 

    #Kung naay search query, i-filter ang employee list base sa name nga nag-match sa query (case-insensitive). Kung walay query, ipakita tanan employees. 
    reports = [e for e in all_emps if query in e.get_name().lower()] if query else all_emps 
    
    #Ipadala ang tanan employee data ug leave requests sa admin dashboard template para ma-display. Apil na ang filtered reports base sa search query.
    return render_template('admin_dashboard.html', employees=all_emps, leaves=leave_reqs, reports=reports, enumerate=enumerate) 

#MODULE 2: REGISTER UG EMPLOYEE
@app.route('/register_employee', methods=['POST'])
# Route para sa pag-register ng employee; POST dahil form submission ito

def register_employee():
    if session.get('role') != 'Admin':
        # Security check: siguraduhin na Admin lang ang may access sa route na ito. 
        return redirect(url_for('login'))
        
    name = request.form.get('name')
    emp_id = request.form.get('emp_id')
    address = request.form.get('address')
    contact = request.form.get('contact_no')
    username = request.form.get('username')
    password = request.form.get('password')

    if Employee.add_new_employee(name, emp_id, address, contact, username, password):
                #Tawagon ang class method  para mo gamaw ug Employee object ug corresponding user account. 
        flash("Employee registered successfully!", "success")
    else:
        flash("Error: Employee ID already exists!", "danger")
        
    return redirect(url_for('admin_dashboard'))

#MODULE 3: EDIT EMPLOYEE INFORMATION
@app.route('/update_employee', methods=['POST'])
def update_employee():
    if session.get('role') != 'Admin':
        return redirect(url_for('login'))

    emp_id = request.form.get('emp_id')
    name = request.form.get('name')
    address = request.form.get('address')
    contact = request.form.get('contact')

    emp = Employee.employee_data.get(emp_id)
    if emp:
        emp.update_emp_info(name, address, contact)
        flash("Employee updated successfully!", "success")
    else:
        flash("Employee not found.", "danger")

    return redirect(url_for('admin_dashboard'))

# MODULE 4: APPROVE/REJECT LEAVE REQUESTS
@app.route('/handle_leave/<int:index>/<string:action>')
# Route na tumatanggap ng:
# index = position ng leave request sa list
# action = "approve" or "reject"

def handle_leave(index, action):
    # Function na magha-handle ng approval/rejection

    if session.get('role') != 'Admin': 
        # Security check: Admin lang ang pwede
        return redirect(url_for('login'))
        # Kung hindi admin, balik login

    if 0 <= index < len(LeaveSystem.leave_requests):
        # Check kung valid ang index (para iwas error)

        req = LeaveSystem.leave_requests[index]
        # Kunin ang specific leave request gamit ang index

        emp = Employee.employee_data.get(str(req['id']))
        # pangitaon ang employee nga nag-request gamit ang ID

        # Check if the request is still pending to avoid double processing
        if req['status'] not in ['Pending', 'Pending Cancellation']:
            # Kung na-process na (Approved/Rejected/Cancelled)

            flash("This request has already been processed.", "info")
            return redirect(url_for('admin_dashboard'))
            # Iwas double approve/reject

        if action == 'approve':
            # Kapag pinili ng admin ay APPROVE

            if req.get('type') == "Cancellation":
                # Kung cancellation leave request

                req['status'] = "Cancelled"
                # I-set nga cancelled

                if emp: emp.leave_credits += 1
                # Ibalik ang leave credit sa employee

                flash("Cancellation Approved. Credit restored.", "success")

            else:
                # Kung normal leave request

                req['status'] = "Approved"
                # I-approve ang leave

                if emp: emp.leave_credits -= 1
                # Bawasan ng 1 ang leave credits

                flash("Leave Approved. Credit deducted.", "success")

        elif action == 'reject':
            # Kapag REJECT ang pinili

            if req.get('type') == "Cancellation":
                # Kung cancellation leave request

                req['status'] = "Approved"
                # Ibalik sa approved leave (hindi natuloy ang cancel)

                req['type'] = "Leave Request"
                # Ibalik sa original type

                flash("Cancellation Rejected.", "info")

            else:
                # Kung normal leave request

                req['status'] = "Rejected"
                # I-reject ang leave

                flash("Leave Request Rejected.", "warning")

        return redirect(url_for('admin_dashboard'))
        # Pagkatapos ng action, balik sa dashboard
    
# --- EMPLOYEE ROUTES ---

@app.route('/employeedashboard')
def employee_dashboard():
    # 1. Security Check: Siguraduhin na may naka-login
    emp_id = session.get('user_id')
    if not emp_id:
        flash("Please login first.", "warning")
        return redirect(url_for('login'))

    # 2. Kunin ang Employee Data
    emp_info = Employee.employee_data.get(str(emp_id))
    if not emp_info:
        flash("Employee record not found.", "danger")
        return redirect(url_for('login'))

    # 3. Kunin ang Leave History ng employee na ito (Correction: Filter history here)
    # Gagamit tayo ng list comprehension para makuha lang ang requests ng user na ito
    emp_history = [
        (i, req) for i, req in enumerate(LeaveSystem.leave_requests) 
        if str(req.get('id')) == str(emp_id)
    ]

    # 4. I-render ang iisang template kasama ang lahat ng kailangang data
    return render_template('employee_dashboard.html', employee=emp_info, history=emp_history,enumerate=enumerate)

@app.route('/apply_leave', methods=['POST'])
def apply_leave():
    emp_id = session.get('user_id')
    if not emp_id:
        return redirect(url_for('login'))

    emp_id = str(emp_id)
    emp_info = Employee.employee_data.get(emp_id)

    if emp_info:
        # 1. Check credits
        if emp_info.leave_credits <= 0:
            flash("Error: You have 0 leave credits left.", "danger")
            return redirect(url_for('employee_dashboard'))

        # 2. Reason
        reason = request.form.get('reason')
        if not reason:
            flash("Error: Please provide a reason.", "warning")
            return redirect(url_for('employee_dashboard'))

        # 3. Leave date
        leave_date = request.form.get('leave_date')
        if not leave_date:
            flash("Error: Please provide a leave date.", "warning")
            return redirect(url_for('employee_dashboard'))

        # 4. Date validation
        leave_date_obj = datetime.strptime(leave_date, "%Y-%m-%d").date()
        if leave_date_obj < date.today():
            flash("Error: Cannot select past dates.", "danger")
            return redirect(url_for('employee_dashboard'))

        # 5. Save
        LeaveSystem.apply_leave(emp_info.get_name(), emp_id, reason, leave_date)
        flash("Leave request submitted successfully!", "success")
        return redirect(url_for('employee_dashboard'))

    # if no employee
    flash("Error: Employee information not found.", "danger")
    return redirect(url_for('login'))
    
@app.route('/cancel_leave/<int:index>', methods=['POST'])
def cancel_leave(index):
    # 1. Kunin ang reason mula sa form
    reason = request.form.get('cancel_reason')
    
    # 2. Tawagin ang class method para i-update ang status sa "Pending Cancellation"
    if LeaveSystem.request_cancellation(index, reason):
        flash("Cancellation request sent to HR.", "success")
    else:
        flash("Error: Cannot cancel leave or invalid request.", "danger")
    
    # 3. LAGING redirect pabalik sa main dashboard
    # Ito ang magpapatakbo ulit ng logic sa employee_dashboard() route
    return redirect(url_for('employee_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
  