from flask import Flask, request, render_template, redirect, url_for, jsonify, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, HiddenField
from wtforms.validators import DataRequired
from datetime import datetime, timedelta  # Import timedelta
import calendar
from collections import defaultdict
import logging
import os
from db import db  # Ensure this imports your db object

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///timetable.db'
app.config['SQLALCHEMY_BINDS'] = {
    'second': 'sqlite:///study_material.db'
}
app.secret_key = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static/uploads')
csrf = CSRFProtect(app)  # Initialize CSRF protection
db.init_app(app)
#db = SQLAlchemy(app)
migrate = Migrate(app, db)

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
from admin.routes import admin_bp
from user.routes import user_bp

app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(user_bp, url_prefix='/user')

# Database Models
class Folder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    folder_name = db.Column(db.String(150), nullable=False)

class Batch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    student_names = db.Column(db.String(1000))  # Ensure this matches your form

class Timetable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    folder_id = db.Column(db.Integer, db.ForeignKey('folder.id'), nullable=False)
    day = db.Column(db.String(50), nullable=False)
    timeslot = db.Column(db.String(50), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey('batch.id'))  # Link to batch

    folder = db.relationship('Folder', backref=db.backref('timetables', lazy=True))
    batch = db.relationship('Batch', backref=db.backref('timetables', lazy=True))

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(150), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey('batch.id'), nullable=False)
    folder_id = db.Column(db.Integer, db.ForeignKey('folder.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.now)
    period = db.Column(db.String(100), nullable=False)
    coming_in_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    going_out_time = db.Column(db.DateTime, nullable=True)

    batch = db.relationship('Batch', backref=db.backref('attendances', lazy=True))
    folder = db.relationship('Folder', backref=db.backref('attendances', lazy=True))

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey('batch.id'), nullable=False)
    due_date = db.Column(db.Date, nullable=False)

    batch = db.relationship('Batch', backref=db.backref('assignments', lazy=True))

class AssignmentSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(150), nullable=False)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    submission_link = db.Column(db.String(300), nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    assignment = db.relationship('Assignment', backref=db.backref('submissions', lazy=True))

class ChatMessage(db.Model):
    __tablename__ = 'chat_message'

    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    parent_id = db.Column(db.Integer, db.ForeignKey('chat_message.id'), nullable=True)

    # Relationship for parent message
    parent = db.relationship('ChatMessage', remote_side=[id], backref='replies')

    # Method to get the depth of the message
    @property
    def depth(self):
        if self.parent is None:
            return 0
        return 1 + self.parent.depth

@app.route('/')
@csrf.exempt
def index():
    return render_template('index.html')

@app.route('/save_folder', methods=['POST'])
@csrf.exempt
def save_folder():
    data = request.json
    folder_name = data.get('folderName')
    days = data.get('days')
    timeslots = data.get('timeslots')
    table_data = data.get('tableData')

    if folder_name and days and timeslots and table_data:
        # Save the folder name
        folder = Folder(folder_name=folder_name)
        db.session.add(folder)
        db.session.commit()

        # Save the timetable data
        for day in days:
            for timeslot in timeslots:
                period_key = f"{day}_{timeslot}"
                period_data = table_data.get(period_key)
                
                try:
                    batch_id = int(period_data)
                except ValueError:
                    batch_id = None

                new_timetable = Timetable(
                    folder_id=folder.id,
                    day=day,
                    timeslot=timeslot,
                    batch_id=batch_id
                )
                db.session.add(new_timetable)

        db.session.commit()
        return jsonify({'message': 'Folder and timetable saved successfully!'}), 201

    return jsonify({'message': 'Failed to save folder and timetable'}), 400

@app.route('/view_tables')
@csrf.exempt
def view_tables():
    folders = Folder.query.all()
    return render_template('view_tables.html', folders=folders)

@app.route('/get_table_data/<int:folder_id>', methods=['GET'])
@csrf.exempt
def get_table_data(folder_id):
    # Retrieve timetables for the specified folder
    timetables = Timetable.query.filter_by(folder_id=folder_id).all()
    
    # Define the order of days
    day_order = {
        'Monday': 1, 
        'Tuesday': 2, 
        'Wednesday': 3, 
        'Thursday': 4, 
        'Friday': 5, 
        'Saturday': 6, 
        'Sunday': 7
    }
    
    # Sort timetables by day and timeslot
    sorted_timetables = sorted(timetables, key=lambda x: (day_order.get(x.day, 8), x.timeslot))
    
    # Dictionary to map batch IDs to names
    batch_names = {}
    
    # Populate the batch names dictionary
    for timetable in sorted_timetables:
        if timetable.batch_id not in batch_names:
            batch = Batch.query.get(timetable.batch_id)
            if batch:
                batch_names[timetable.batch_id] = batch.name

    # Prepare data to group attendance by day and period
    attendance_data = {}

    for timetable in sorted_timetables:
        day = timetable.day
        period = timetable.timeslot
        batch_name = batch_names[timetable.batch_id]
        
        # Use a tuple of (day, period) as the key for grouping
        key = (day, period)
        
        # Initialize list for storing student names if key doesn't exist
        if key not in attendance_data:
            attendance_data[key] = []
        
        # Append batch name to the corresponding day/period key
        attendance_data[key].append(batch_name)

    # Format the data for JSON response
    data = []
    for (day, period), names in attendance_data.items():
        data.append((day, period, names))  # Collecting day, period, and list of student names

    return jsonify(data)

@app.route('/create_batch', methods=['GET', 'POST'])
@csrf.exempt
def create_batch():
    if request.method == 'POST':
        try:
            batch_name = request.form['batch_name']
            student_names = request.form['student_names']
            new_batch = Batch(name=batch_name, student_names=student_names)
            db.session.add(new_batch)
            db.session.commit()
            return redirect(url_for('view_batches'))
        except KeyError as e:
            return f"Missing form field: {e}", 400
    else:
        return render_template('create_batch.html')

@app.route('/get_folder')
@csrf.exempt
def get_folder():
    folders = Folder.query.all()
    logging.debug(f"folders fetched: {folders}")  # Log fetched batches
    folders_list = [{"id": folder.id, "name": folder.folder_name} for folder in folders]
    return jsonify(folders_list)

@app.route('/get_batches')
@csrf.exempt
def get_batches():
    batches = Batch.query.all()
    logging.debug(f"Batches fetched: {batches}")  # Log fetched batches
    batch_list = [{"id": batch.id, "name": batch.name, "student_names": batch.student_names} for batch in batches]
    return jsonify(batch_list)

logging.basicConfig(level=logging.DEBUG)

@app.route('/view_batches')
@csrf.exempt
def view_batches():
    batches = Batch.query.all()
    logging.debug(f"Batches fetched: {batches}")
    return render_template('view_batches.html', batches=batches)

@app.route('/get_timetable/<int:class_id>', methods=['GET'])
@csrf.exempt
def get_timetable(class_id):
    # Query the timetable based on the provided class_id (folder_id)
    timetables = Timetable.query.filter_by(folder_id=class_id).all()

    # Prepare a structured response
    timetable_data = []
    day_order = {'Monday': 1, 'Tuesday': 2, 'Wednesday': 3, 'Thursday': 4, 'Friday': 5, 'Saturday': 6, 'Sunday': 7}

    # Create a dictionary to hold timetables organized by day
    timetable_dict = {day: [] for day in day_order}

    for timetable in timetables:
        timetable_dict[timetable.day].append({
            'timeslot': timetable.timeslot,
            'batch_id': timetable.batch_id
        })

    # Convert the timetable dictionary to a list of tuples
    for day in day_order:
        timetable_data.append({
            'day': day,
            'periods': timetable_dict[day]
        })

    return jsonify(timetable_data)

@app.route('/attendance', methods=['GET', 'POST'])
@csrf.exempt
def attendance():
    if request.method == 'POST':
        class_id = request.form['class_id']
        student_name = request.form['student_name']
        now = datetime.now()
        current_day = now.strftime('%A')
        current_time = now.strftime('%H:%M')  # Time in 24-hour format (e.g., 14:30)

        # Get today's date
        today_date = now.date()

        # Fetch the timetable based on the class and batch
        timetables = Timetable.query.filter_by(folder_id=class_id).all()
        current_period = None

        for timetable in timetables:
            if timetable.day == current_day:
                start_time, end_time = timetable.timeslot.split('-')
                if start_time <= current_time <= end_time:
                    current_period = timetable
                    break

        if current_period:
            batch = Batch.query.get(current_period.batch_id)
            if batch and student_name in batch.student_names.split(','):
                # Check if attendance already exists
                print(f"Querying for: student_name={student_name}, batch_id={current_period.batch_id}, "
                      f"date={today_date}, period={current_period.day} {current_period.timeslot}, going_out_time=None")

                existing_attendance = Attendance.query.filter(
                    Attendance.student_name == student_name,
                    Attendance.batch_id == current_period.batch_id,
                    Attendance.date == today_date,
                    Attendance.period == f"{current_period.day} {current_period.timeslot}",
                    Attendance.going_out_time == None  # Ensure None is correct here
                ).first()

                if not existing_attendance:
                    print("No matching attendance record found. Check each field’s format and data.")


                if existing_attendance:
                    existing_attendance.going_out_time = now
                    db.session.commit()
                    return jsonify({'message': 'Going out time recorded successfully!'}), 200
                else:
                    attendance_record = Attendance(
                        student_name=student_name,
                        batch_id=current_period.batch_id,
                        folder_id=class_id,
                        period=f"{current_period.day} {current_period.timeslot}",
                        coming_in_time=now,
                    )
                    db.session.add(attendance_record)
                    db.session.commit()
                    return jsonify({'message': 'Attendance marked successfully!'}), 200
            else:
                return jsonify({'message': 'Student is not in the batch for the current period'}), 400
        else:
            return jsonify({'message': 'No ongoing period found for the current time and day'}), 400

    else:  # GET request
        # Get all classes (folders) for the dropdown
        folders = Folder.query.all()
        return render_template('attendance.html', folders=folders)

    
@app.route('/create_attendance', methods=['POST'])
@csrf.exempt
def create_attendance():
    logging.debug('Received data: %s', request.form)
    try:
        student_name = request.form.get('student_name')
        coming_in_time = request.form.get('coming_in_time')
        going_out_time = request.form.get('going_out_time')
        selected_date = request.form.get('selectedDate')
        selected_day = calendar.day_name[datetime.strptime(selected_date, '%Y-%m-%d').weekday()]  # Assuming date is in 'YYYY-MM-DD' format

        batch_id = request.form.get('batch_id')
        class_id = request.form.get('class_id')  # This is class_id but used for folder_id in the record

        # Validate inputs
        if not student_name or not coming_in_time or not selected_date or not batch_id or not class_id:
            return jsonify({"message": "Missing required fields!"}), 400

        # Fetch the periods of the class for the selected day
        class_periods = get_class_periods_for_day(class_id, selected_day)

        # Convert the coming_in_time and going_out_time to datetime for comparison and storage
        coming_in_time_obj = datetime.strptime(f"{selected_date} {coming_in_time}", '%Y-%m-%d %H:%M')
        going_out_time_obj = datetime.strptime(f"{selected_date} {going_out_time}", '%Y-%m-%d %H:%M') if going_out_time else None

        # Find the correct period based on coming_in_time
        selected_period = None
        for period in class_periods:
            period_start = datetime.strptime(f"{selected_date} {(period.timeslot.split('-'))[0]}", '%Y-%m-%d %H:%M')
            period_end = datetime.strptime(f"{selected_date} {(period.timeslot.split('-'))[1]}", '%Y-%m-%d %H:%M')

            # If the coming_in_time falls within the period time range
            if period_start <= coming_in_time_obj <= period_end:
                selected_period = period
                break

        if not selected_period:
            return jsonify({"message": "No matching period found for the selected time."}), 404
        print("done")

        # Create the attendance record using the correct variable names
        attendance_record = Attendance(
            student_name=student_name,
            batch_id=selected_period.batch_id,
            folder_id=class_id,  # Use class_id as folder_id
            period=f"{selected_day} {selected_period.timeslot}",
            coming_in_time=coming_in_time_obj,
            going_out_time=going_out_time_obj
        )

        db.session.add(attendance_record)
        db.session.commit()

        return jsonify({"message": "Attendance created successfully!"}), 201

    except Exception as e:
        print("Error creating attendance:", str(e))
        return jsonify({"message": "An error occurred while creating attendance."}), 500

def get_class_periods_for_day(class_id, selected_day):
    # Assuming you have a predefined schedule for the class
    # Fetch the periods for the class and day from the database or some predefined structure
    periods = Timetable.query.filter_by(folder_id=class_id, day=selected_day).all()

    return periods

@app.route('/student_dashboard', methods=['GET', 'POST'])
@csrf.exempt
def student_dashboard():
    student_name = request.args.get('student_name', None)

    if not student_name:
        chart_data = {'labels': [], 'data': []}
        return render_template(
            'student_dashboard.html',
            error="Please enter a student name.",
            batch_durations={},
            batches=[],
            attendance_data=[],
            chart_data=chart_data,
            upcoming_assignments={},
            past_due_assignments={},
            submissions={}
        )

    now = datetime.now()
    student_batches = Batch.query.filter(Batch.student_names.like(f'%{student_name}%')).all()
    submissions = defaultdict(list)

    if student_batches:
        batch_ids = [batch.id for batch in student_batches]
        
        # Fetch all relevant assignments
        all_assignments = Assignment.query.filter(
            Assignment.batch_id.in_(batch_ids)
        ).all()

        # Separate assignments by due date
        upcoming_assignments = defaultdict(list)
        past_due_assignments = defaultdict(list)
        for assignment in all_assignments:
            if assignment.due_date >= now.date():
                upcoming_assignments[assignment.batch.name].append(assignment)
            else:
                past_due_assignments[assignment.batch.name].append(assignment)

        # Fetch all submissions for these assignments
        submissions_query = AssignmentSubmission.query.filter(
            AssignmentSubmission.student_name == student_name,
            AssignmentSubmission.assignment_id.in_([assignment.id for assignment in all_assignments])
        ).all()

        # Organize submissions by assignment ID
        for submission in submissions_query:
            submissions[submission.assignment_id].append({
                'student_name': submission.student_name,
                'submission_link': submission.submission_link,
                'submitted_at': submission.submitted_at
            })

        # Set can_resubmit flag for assignments
        for assignment in all_assignments:
            assignment.can_resubmit = assignment.due_date >= now.date() if assignment.id in submissions else True

    # Fetch attendance records for the student
    attendances = Attendance.query.filter_by(student_name=student_name).all()

    # Initialize batch_durations and attendance groups
    batch_durations = {}
    attendance_groups = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(timedelta))))

    # Calculate batch attendance durations and populate attendance_groups
    for attendance in attendances:
        batch = Batch.query.get(attendance.batch_id)
        folder = Folder.query.get(attendance.folder_id)

        if batch:
            if batch.name not in batch_durations:
                batch_durations[batch.name] = timedelta(0)

            # Calculate duration of the class
            if attendance.going_out_time:
                duration = attendance.going_out_time - attendance.coming_in_time
            else:
                duration = now - attendance.coming_in_time

            batch_durations[batch.name] += duration
            attendance_groups[attendance.date][folder.folder_name][batch.name][attendance.period] += duration

    # Prepare data for the attendance table
    attendance_data = []
    for date, folder_groups in attendance_groups.items():
        for folder_name, batch_groups in folder_groups.items():
            for batch_name, period_groups in batch_groups.items():
                for period, total_duration in period_groups.items():
                    attendance_data.append({
                        'date': date,
                        'class_id': folder_name,
                        'batch': batch_name,
                        'period': period,
                        'total_duration': total_duration.total_seconds() / 3600
                    })

    # Prepare data for chart
    weekday_durations = defaultdict(timedelta)
    for date, folder_groups in attendance_groups.items():
        weekday = date.strftime('%A')
        for folder_name, batch_groups in folder_groups.items():
            for batch_name, period_groups in batch_groups.items():
                for period, total_duration in period_groups.items():
                    weekday_durations[weekday] += total_duration

    chart_data = {
        'labels': list(weekday_durations.keys()),
        'data': [duration.total_seconds() / 3600 for duration in weekday_durations.values()]
    }

    return render_template(
        'student_dashboard.html',
        student_name=student_name,
        upcoming_assignments=upcoming_assignments,
        past_due_assignments=past_due_assignments,
        submissions=submissions,
        attendances=attendances,
        batches=student_batches,
        batch_durations=batch_durations,
        attendance_data=attendance_data,
        chart_data=chart_data,
        now=now,
        timedelta=timedelta
    )

# Custom Jinja2 filter for formatting datetime
@app.template_filter('datetimeformat')
@csrf.exempt
def datetimeformat(value, format='%Y-%m-%d %H:%M'):
    if value is None:
        return ""
    return value.strftime(format)

@app.route('/get_students/<int:batch_id>')
@csrf.exempt
def get_students(batch_id):
    batch = Batch.query.get(batch_id)
    if batch:
        student_names = batch.student_names.split(',')
        return jsonify(student_names)
    return jsonify([])  # Return an empty list if no batch is found
@app.route('/teacher_dashboard', methods=['GET', 'POST'])
@csrf.exempt
def teacher_dashboard():
    batches = Batch.query.all()
    folders = Folder.query.all()

    # Get the selected batch
    batch_id = request.form.get('batch_id') if request.method == 'POST' else None
    selected_batch = Batch.query.get(batch_id) if batch_id else None

    attendance_data = []
    assignment_data = []
    submission_data = []

    if selected_batch:
        # Fetch relevant attendance records for the selected batch
        attendance_data = Attendance.query.filter_by(batch_id=selected_batch.id).all()

        # Fetch assignments for the selected batch
        assignment_data = Assignment.query.filter_by(batch_id=selected_batch.id).all()

        # Fetch submissions for the selected batch
        submission_data = AssignmentSubmission.query.join(Assignment).filter(
            Assignment.batch_id == selected_batch.id
        ).all()

    # Prepare attendance data with total duration
    formatted_attendance_data = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(timedelta)))))

    for attendance in attendance_data:
        folder = Folder.query.get(attendance.folder_id)

        # Calculate total duration for attendance
        total_duration = None
        if attendance.going_out_time:
            total_duration = attendance.going_out_time - attendance.coming_in_time
        elif attendance.coming_in_time:
            total_duration = datetime.now() - attendance.coming_in_time

        if total_duration:
            formatted_attendance_data[attendance.date][selected_batch.name][folder.folder_name][attendance.period][attendance.student_name] += total_duration

    # Prepare attendance summary for display
    attendance_summary = []
    for date, batches in formatted_attendance_data.items():
        for batch_name, folders in batches.items():
            for folder_name, periods in folders.items():
                for period, students in periods.items():
                    for student_name, total_duration in students.items():
                        attendance_summary.append({
                            'date': date,
                            'batch_name': batch_name,
                            'folder_name': folder_name,
                            'period': period,
                            'student_name': student_name,
                            'total_duration_hours': round(total_duration.total_seconds() / 3600, 2)  # Convert to hours
                        })

    present_count = sum(1 for attendance in attendance_data if attendance.going_out_time)
    absent_count = len(attendance_data) - present_count

    return render_template(
        'teacher_dashboard.html',
        batches=batches,
        folders=folders,
        selected_batch=selected_batch,
        attendance_data=attendance_summary,
        assignment_data=assignment_data,
        submission_data=submission_data,
        present_count=present_count,
        absent_count=absent_count
    )

# Route for creating/editing assignments
@app.route('/create_assignment', methods=['GET', 'POST'])
@csrf.exempt
def create_assignment():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        due_date_str = request.form['due_date']
        batch_id = request.form['batch_id']

        # Convert the due date string to a date object
        due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()

        new_assignment = Assignment(title=title, description=description, due_date=due_date, batch_id=batch_id)
        db.session.add(new_assignment)
        db.session.commit()

        flash('Assignment created successfully!', 'success')
        return redirect(url_for('teacher_dashboard'))

    batches = Batch.query.all()
    return render_template('assignment_form.html', batches=batches)

# Route for editing attendance
@app.route('/edit_attendance', methods=['POST'])
@csrf.exempt
def edit_attendance():
    attendance_id = request.form['attendance_id']
    coming_in_time = request.form['coming_in_time']
    going_out_time = request.form['going_out_time']

    attendance = Attendance.query.get(attendance_id)
    if attendance:
        attendance.coming_in_time = datetime.strptime(coming_in_time, '%Y-%m-%dT%H:%M')
        attendance.going_out_time = datetime.strptime(going_out_time, '%Y-%m-%dT%H:%M') if going_out_time else None
        db.session.commit()

    return redirect(url_for('teacher_dashboard'))

# Dynamic route to view submissions for an assignment
@app.route('/view_submissions/<int:assignment_id>')
@csrf.exempt
def view_submissions(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    submissions = AssignmentSubmission.query.filter_by(assignment_id=assignment.id).all()

    return render_template('view_submissions.html', assignment=assignment, submissions=submissions)

@app.route('/submit_assignment', methods=['POST'])
@csrf.exempt
def submit_assignment():
    student_name = request.form['student_name']
    assignment_id = request.form['assignment_id']
    submission_link = request.form['submission_link']

    # Get the due date for the assignment
    assignment = Assignment.query.get(assignment_id)

    if assignment and assignment.due_date >= datetime.now().date():
        # Check if a submission already exists
        existing_submission = AssignmentSubmission.query.filter(
            AssignmentSubmission.student_name == student_name,
            AssignmentSubmission.assignment_id == assignment_id
        ).first()

        if existing_submission:
            # Update the existing submission
            existing_submission.submission_link = submission_link
            existing_submission.submitted_at = datetime.now()
        else:
            # Create a new submission
            new_submission = AssignmentSubmission(
                student_name=student_name,
                assignment_id=assignment_id,
                submission_link=submission_link,
                submitted_at=datetime.now()
            )
            db.session.add(new_submission)

        db.session.commit()
    else:
        # Handle case where due date has passed (optional)
        flash("Cannot submit assignment after the due date.")

    return redirect(url_for('student_dashboard', student_name=student_name))

@app.route('/charts')
@csrf.exempt
def charts():
    # Fetch all attendance records
    attendances = Attendance.query.all()

    # Initialize a defaultdict to accumulate total durations for each weekday
    weekday_durations = defaultdict(timedelta)

    # Calculate the total duration for each day of the week
    for attendance in attendances:
        if attendance.going_out_time:  # Ensure that going_out_time is recorded
            duration = attendance.going_out_time - attendance.coming_in_time
        else:
            duration = datetime.now() - attendance.coming_in_time  # Current time if not checked out

        # Convert the attendance date to a weekday string
        weekday = attendance.date.strftime('%A')
        weekday_durations[weekday] += duration

    # Prepare data for the chart
    chart_data = {
        'labels': list(weekday_durations.keys()),
        'data': [duration.total_seconds() / 3600 for duration in weekday_durations.values()]  # Convert to hours
    }

    # Ensure chart_data is defined
    if not chart_data['labels']:
        chart_data = {'labels': [], 'data': []}

    return render_template('charts.html', chart_data=chart_data)
@app.route('/community_chat', methods=['GET', 'POST'])
@csrf.exempt
def community_chat():
    if request.method == 'POST':
        user_name = request.form['user_name']
        content = request.form['content']
        parent_id = request.form.get('parent_id')  # Optional, for replying to a thread
        
        new_message = ChatMessage(user_name=user_name, content=content, parent_id=parent_id)
        db.session.add(new_message)
        db.session.commit()
        
        flash('Message posted successfully!', 'success')
        return redirect(url_for('community_chat'))
    
    # Fetch all top-level messages (where parent_id is None) and their replies
    chat_messages = ChatMessage.query.filter_by(parent_id=None).order_by(ChatMessage.created_at.desc()).all()

    return render_template('community_chat.html', chat_messages=chat_messages)
@app.route('/reply/<int:message_id>', methods=['POST'])
@csrf.exempt
def reply(message_id):
    parent_message = ChatMessage.query.get_or_404(message_id)
    
    user_name = request.form['user_name']
    content = request.form['content']
    
    reply_message = ChatMessage(user_name=user_name, content=content, parent=parent_message)
    db.session.add(reply_message)
    db.session.commit()
    
    flash('Reply posted successfully!', 'success')
    return redirect(url_for('community_chat'))
@app.route('/study_mat')
def home():
    return render_template('home.html')
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
