from flask import Flask, render_template, request, jsonify, Response, session, redirect, url_for
import cv2
import os
import numpy as np
from PIL import Image
import mysql.connector
from mysql.connector import Error
import pickle
import io
from datetime import date, datetime, timedelta
import csv
import time
import shutil

app = Flask(__name__)
app.secret_key = 'bubt_attendance_secret_key_2025'
app.config['SESSION_TYPE'] = 'filesystem'

# ---------------- Database Configuration ----------------
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'bubt_attendance_system'
}

# -------- CHANGED: Simple global variables with reset function --------
# Global variables for face capture
capture_complete = False
captured_faces = []
capture_in_progress = False

def reset_capture_globals():
    """Reset global capture variables"""
    global capture_complete, captured_faces, capture_in_progress
    capture_complete = False
    captured_faces = []
    capture_in_progress = False
    print("✓ Capture globals reset")

# ---------------- Database Functions ----------------
def create_connection():
    """Create database connection"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def initialize_database():
    """Create database and tables if they don't exist"""
    try:
        # First connect without database to create it
        temp_config = DB_CONFIG.copy()
        temp_config.pop('database', None)
        
        connection = mysql.connector.connect(**temp_config)
        cursor = connection.cursor()
        
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
        cursor.execute(f"USE {DB_CONFIG['database']}")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                student_id VARCHAR(20) PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                department VARCHAR(50),
                semester VARCHAR(20),
                section VARCHAR(10),
                face_data LONGBLOB,
                is_trained BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                attendance_id INT AUTO_INCREMENT PRIMARY KEY,
                student_id VARCHAR(20) NOT NULL,
                student_name VARCHAR(100) NOT NULL,
                department VARCHAR(50),
                course_code VARCHAR(20),
                date DATE NOT NULL,
                time TIME NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(student_id),
                UNIQUE KEY unique_attendance (student_id, date, course_code)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS unknown_faces (
                id INT AUTO_INCREMENT PRIMARY KEY,
                image_path VARCHAR(255),
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                course_code VARCHAR(20) PRIMARY KEY,
                course_name VARCHAR(100) NOT NULL,
                department VARCHAR(50),
                semester VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        connection.commit()
        cursor.close()
        connection.close()
        print("Database initialized successfully")
        return True
    except Error as e:
        print(f"Error initializing database: {e}")
        return False

def insert_student(student_id, name, department="CSE", semester="", section=""):
    """Insert new student into database"""
    try:
        connection = create_connection()
        if connection:
            cursor = connection.cursor()
            query = """
                INSERT INTO students (student_id, name, department, semester, section) 
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (student_id, name, department, semester, section))
            connection.commit()
            cursor.close()
            connection.close()
            return True
    except Error as e:
        print(f"Error inserting student: {e}")
        return False

def save_face_data(student_id, face_images, labels):
    """Save individual student's face training data to database"""
    try:
        connection = create_connection()
        if connection:
            cursor = connection.cursor()
            
            face_data = {
                'images': face_images,
                'labels': labels
            }
            serialized_data = pickle.dumps(face_data)
            
            query = """
                UPDATE students 
                SET face_data = %s, is_trained = TRUE, updated_at = CURRENT_TIMESTAMP
                WHERE student_id = %s
            """
            cursor.execute(query, (serialized_data, student_id))
            connection.commit()
            cursor.close()
            connection.close()
            return True
    except Error as e:
        print(f"Error saving face data: {e}")
        return False

def get_all_face_data():
    """Retrieve all trained face data from database"""
    try:
        connection = create_connection()
        if connection:
            cursor = connection.cursor()
            query = """
                SELECT student_id, face_data 
                FROM students 
                WHERE is_trained = TRUE AND face_data IS NOT NULL
            """
            cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()
            connection.close()
            
            all_faces = []
            all_labels = []
            student_id_map = {}
            
            for idx, (student_id, face_data_blob) in enumerate(results):
                if face_data_blob:
                    face_data = pickle.loads(face_data_blob)
                    all_faces.extend(face_data['images'])
                    if student_id not in student_id_map:
                        student_id_map[student_id] = idx
                    all_labels.extend([idx] * len(face_data['images']))
            
            return all_faces, all_labels, student_id_map
    except Error as e:
        print(f"Error retrieving face data: {e}")
        return [], [], {}

def get_student_name(student_id):
    """Get student name by ID"""
    try:
        connection = create_connection()
        if connection:
            cursor = connection.cursor()
            query = "SELECT name, department FROM students WHERE student_id = %s"
            cursor.execute(query, (student_id,))
            result = cursor.fetchone()
            cursor.close()
            connection.close()
            return result if result else (None, None)
    except Error as e:
        print(f"Error fetching student: {e}")
        return None, None

def get_trained_students_count():
    """Get count of trained students"""
    try:
        connection = create_connection()
        if connection:
            cursor = connection.cursor()
            query = "SELECT COUNT(*) FROM students WHERE is_trained = TRUE"
            cursor.execute(query)
            result = cursor.fetchone()
            cursor.close()
            connection.close()
            return result[0] if result else 0
    except Error as e:
        print(f"Error getting count: {e}")
        return 0

def insert_attendance(student_id, student_name, department, date_val, time_val, course_code=""):
    """Insert attendance record"""
    try:
        connection = create_connection()
        if connection:
            cursor = connection.cursor()
            query = """
                INSERT INTO attendance (student_id, student_name, department, course_code, date, time) 
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE time = %s
            """
            cursor.execute(query, (student_id, student_name, department, course_code, date_val, time_val, time_val))
            connection.commit()
            cursor.close()
            connection.close()
            return True
    except Error as e:
        print(f"Error inserting attendance: {e}")
        return False

def get_today_attendance():
    """Get today's attendance records with properly formatted time"""
    try:
        connection = create_connection()
        if connection:
            cursor = connection.cursor()
            today = date.today()
            query = """
                SELECT student_id, student_name, department, time 
                FROM attendance 
                WHERE date = %s
                ORDER BY time DESC
            """
            cursor.execute(query, (today,))
            results = cursor.fetchall()
            cursor.close()
            connection.close()
            
            # Format time properly
            formatted_results = []
            for record in results:
                student_id, name, dept, time_val = record
                if time_val:
                    # Handle both time objects and timedelta objects
                    if isinstance(time_val, timedelta):
                        total_seconds = int(time_val.total_seconds())
                        hours = total_seconds // 3600
                        minutes = (total_seconds % 3600) // 60
                        seconds = total_seconds % 60
                        formatted_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    else:
                        formatted_time = str(time_val)
                else:
                    formatted_time = "00:00:00"
                
                formatted_results.append((student_id, name, dept, formatted_time))
            
            return formatted_results
    except Error as e:
        print(f"Error fetching attendance: {e}")
        return []

def get_all_students():
    """Get all registered students"""
    try:
        connection = create_connection()
        if connection:
            cursor = connection.cursor()
            query = "SELECT student_id, name, department, is_trained FROM students ORDER BY created_at DESC"
            cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()
            connection.close()
            return results
    except Error as e:
        print(f"Error fetching students: {e}")
        return []

def log_unknown_face(image_path):
    """Log unknown face detection"""
    try:
        connection = create_connection()
        if connection:
            cursor = connection.cursor()
            query = "INSERT INTO unknown_faces (image_path) VALUES (%s)"
            cursor.execute(query, (image_path,))
            connection.commit()
            cursor.close()
            connection.close()
    except Error as e:
        print(f"Error logging unknown face: {e}")

def get_full_report_by_date(selected_date):
    """
    Get a full report: all students LEFT JOIN grouped attendance times for the selected date.
    """
    try:
        connection = create_connection()
        if connection:
            cursor = connection.cursor()
            
            attendance_summary_query = """
                SELECT 
                    student_id, 
                    MIN(timestamp) AS in_time_dt,
                    MAX(time) AS out_time_col
                FROM attendance
                WHERE date = %s
                GROUP BY student_id
            """
            
            main_query = """
                SELECT 
                    s.student_id, 
                    s.name, 
                    s.department,
                    T.in_time_dt,
                    T.out_time_col
                FROM students s
                LEFT JOIN ({}) AS T
                ON s.student_id = T.student_id
                ORDER BY s.student_id ASC;
            """.format(attendance_summary_query)
            
            cursor.execute(main_query, (selected_date,))
            results = cursor.fetchall()
            cursor.close()
            connection.close()

            report = []
            for row in results:
                student_id, name, dept, in_time_dt, out_time_col = row
                
                status = "Present" if in_time_dt or out_time_col else "Absent"
                
                # Format in_time (datetime object)
                in_time_display = in_time_dt.strftime('%H:%M:%S') if in_time_dt else "-"
                
                # Format out_time (could be timedelta or time object)
                if out_time_col:
                    if isinstance(out_time_col, timedelta):
                        total_seconds = int(out_time_col.total_seconds())
                        hours = total_seconds // 3600
                        minutes = (total_seconds % 3600) // 60
                        seconds = total_seconds % 60
                        out_time_display = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    else:
                        out_time_display = str(out_time_col)
                else:
                    out_time_display = "-"

                report.append({
                    'id': student_id,
                    'name': name,
                    'department': dept,
                    'in_time': in_time_display,
                    'out_time': out_time_display,
                    'status': status
                })
            return report
            
    except Error as e:
        print(f"Error fetching full attendance report: {e}")
        return []

# Global variables for face recognition
recognizer = None
faceCascade = None
id_to_student = {}
# -------- CHANGED: Remove tracked_today set to allow multiple attendance marks --------
# We'll track attendance in database instead of memory

def initialize_face_recognition():
    """Initialize face recognition components"""
    global recognizer, faceCascade, id_to_student
    
    # Load face detector
    harcascadePath = "haarcascade_frontalface_default.xml"
    if os.path.exists(harcascadePath):
        faceCascade = cv2.CascadeClassifier(harcascadePath)
    else:
        print("Warning: haarcascade_frontalface_default.xml not found")
        faceCascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    # Load trained model if exists
    if os.path.exists("TrainingModel/BUBTModel.yml"):
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.read("TrainingModel/BUBTModel.yml")
        
        # Load student mapping
        if os.path.exists("TrainingModel/student_map.pkl"):
            with open("TrainingModel/student_map.pkl", "rb") as f:
                student_id_map = pickle.load(f)
                id_to_student = {v: k for k, v in student_id_map.items()}

# Context processor to make current_date available to all templates
@app.context_processor
def inject_current_date():
    return {'current_date': date.today()}

# Initialize on startup
initialize_database()
initialize_face_recognition()

# Create necessary directories
os.makedirs("StudentImages", exist_ok=True)
os.makedirs("TrainingModel", exist_ok=True)
os.makedirs("UnknownFaces", exist_ok=True)

# ---------------- Routes ----------------
@app.route('/')
def index():
    """Home page"""
    today_attendance = get_today_attendance()
    total_students = len(get_all_students())
    trained_count = get_trained_students_count()
    
    return render_template('index.html', 
                         attendance_count=len(today_attendance),
                         total_students=total_students,
                         trained_count=trained_count,
                         today_attendance=today_attendance)

@app.route('/register')
def register_page():
    """Student registration page"""
    return render_template('register.html')

@app.route('/register_student', methods=['POST'])
def register_student():
    """Handle student registration with face capture"""
    student_id = request.form.get('student_id', '').strip()
    name = request.form.get('name', '').strip()
    department = request.form.get('department', 'CSE').strip()
    
    if not student_id or not name:
        return jsonify({'success': False, 'message': 'Please fill Student ID and Name!'})
    
    if not name.replace(" ", "").isalpha():
        return jsonify({'success': False, 'message': 'Name must contain only letters!'})
    
    # Check if student already exists
    existing_name, existing_dept = get_student_name(student_id)
    if existing_name:
        return jsonify({'success': False, 'message': f'Student ID {student_id} already exists!'})
    
    # -------- CHANGED: Reset capture before new registration --------
    reset_capture_globals()
    
    # Store in session for face capture
    session['registering_student'] = {
        'student_id': student_id,
        'name': name,
        'department': department
    }
    
    return jsonify({'success': True, 'message': 'Ready for face capture'})

@app.route('/capture_faces')
def capture_faces():
    """Face capture page"""
    if 'registering_student' not in session:
        return redirect(url_for('register_page'))
    
    return render_template('capture_faces.html')

@app.route('/start_capture')
def start_capture():
    """Initialize face capture session"""
    global capture_complete, captured_faces, capture_in_progress
    
    print("\n=== START_CAPTURE CALLED ===")
    
    # -------- CHANGED: Reset all capture state using function --------
    reset_capture_globals()
    capture_in_progress = True
    
    print(f"Capture state: complete={capture_complete}, in_progress={capture_in_progress}, faces={len(captured_faces)}")
    
    return jsonify({'success': True, 'message': 'Capture started'})

@app.route('/check_capture_status')
def check_capture_status():
    """Check if face capture is complete"""
    global capture_complete, captured_faces, capture_in_progress
    
    return jsonify({
        'complete': capture_complete,
        'in_progress': capture_in_progress,
        'face_count': len(captured_faces)
    })

@app.route('/save_captured_faces', methods=['POST'])
def save_captured_faces():
    """Save the captured faces to database"""
    global captured_faces
    
    print(f"\n=== SAVE_CAPTURED_FACES CALLED ===")
    print(f"Captured faces count: {len(captured_faces)}")
    
    if 'registering_student' not in session:
        return jsonify({
            'success': False, 
            'message': 'No student data in session'
        })
    
    if len(captured_faces) < 20:
        return jsonify({
            'success': False, 
            'message': f'Not enough faces captured: {len(captured_faces)}/20 minimum'
        })
    
    try:
        student_data = session['registering_student']
        student_id = student_data['student_id']
        name = student_data['name']
        department = student_data['department']
        
        print(f"Saving data for: {student_id} - {name}")
        
        # Insert student first
        if not insert_student(student_id, name, department):
            return jsonify({
                'success': False,
                'message': 'Failed to insert student into database'
            })
        
        # Create labels array
        labels = [student_id] * len(captured_faces)
        
        # Save face data to database
        if not save_face_data(student_id, captured_faces, labels):
            return jsonify({
                'success': False,
                'message': 'Failed to save face data to database'
            })
        
        # Save images to folder for backup
        student_folder = os.path.join("StudentImages", student_id)
        os.makedirs(student_folder, exist_ok=True)
        
        for idx, face_img in enumerate(captured_faces):
            img_path = os.path.join(student_folder, f"face_{idx+1}.jpg")
            cv2.imwrite(img_path, face_img)
        
        # -------- CHANGED: Clear session but don't reset globals yet --------
        session.pop('registering_student', None)
        
        return jsonify({
            'success': True,
            'message': f'Successfully registered {name} with {len(captured_faces)} face samples'
        })
        
    except Exception as e:
        print(f"Error in save_captured_faces: {e}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        })

@app.route('/train')
def train_page():
    """Model training page"""
    trained_count = get_trained_students_count()
    total_students = len(get_all_students())
    return render_template('train.html', 
                         trained_count=trained_count,
                         total_students=total_students)

@app.route('/train_model', methods=['POST'])
def train_model():
    """Train the face recognition model"""
    try:
        faces, ids, student_map = get_all_face_data()
        
        if len(faces) == 0:
            return jsonify({'success': False, 'message': 'No training data found! Please register students first.'})
        
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.train(faces, np.array(ids))
        
        os.makedirs("TrainingModel", exist_ok=True)
        recognizer.save("TrainingModel/BUBTModel.yml")
        
        with open("TrainingModel/student_map.pkl", "wb") as f:
            pickle.dump(student_map, f)
        
        trained_count = get_trained_students_count()
        
        # Reload the model
        initialize_face_recognition()
        
        return jsonify({
            'success': True, 
            'message': f'Model trained successfully! Trained {trained_count} students with {len(faces)} samples.'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error training model: {str(e)}'})

@app.route('/attendance')
def attendance_page():
    """Attendance marking page"""
    return render_template('attendance.html')

@app.route('/view_attendance')
def view_attendance_page():
    """View attendance records page"""
    today_attendance = get_today_attendance()
    all_students = get_all_students()
    return render_template('view_attendance.html', 
                         attendance=today_attendance,
                         students=all_students)

@app.route('/attendance_report', methods=['GET', 'POST'])
def attendance_report():
    """Attendance report page"""
    today = date.today().strftime('%Y-%m-%d')
    report_data = []
    selected_date = today
    message = "Select a date to view attendance report."

    if request.method == 'POST':
        selected_date = request.form.get('report_date')
    
    try:
        datetime.strptime(selected_date, '%Y-%m-%d')
        report_data = get_full_report_by_date(selected_date)
        
        present_count = sum(1 for student in report_data if student['status'] == 'Present')
        total_students = len(report_data)

        if total_students > 0:
            message = f"Report for {selected_date}: {present_count} Present out of {total_students} Registered."
        else:
            message = "No students registered in the system."

    except ValueError:
        message = "Invalid date format. Please use YYYY-MM-DD."
        selected_date = today
    except Exception as e:
        message = f"An error occurred: {e}"
            
    return render_template('report.html', 
                           report_data=report_data, 
                           selected_date=selected_date,
                           message=message)

@app.route('/download_csv/<date_str>')
def download_report(date_str):
    """Route to generate and download the CSV report."""
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return "Invalid date format", 400

    report_data = get_full_report_by_date(date_str)
    
    if not report_data:
        return f"No report data found for {date_str}", 404

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Student ID', 'Name', 'Department', 'In Time', 'Out Time', 'Status'])
    
    # Write data
    for student in report_data:
        writer.writerow([
            student['id'],
            student['name'],
            student['department'],
            student['in_time'],
            student['out_time'],
            student['status']
        ])
    
    # Prepare response
    output.seek(0)
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=BUBT_Attendance_Report_{date_str}.csv"}
    )

# ---------------- Data Cleaning Routes ----------------
@app.route('/admin')
def admin_page():
    """Admin page for data management"""
    total_students = len(get_all_students())
    trained_count = get_trained_students_count()
    today_attendance = get_today_attendance()
    
    return render_template('admin.html',
                         total_students=total_students,
                         trained_count=trained_count,
                         attendance_count=len(today_attendance))

@app.route('/clear_all_data', methods=['POST'])
def clear_all_data():
    """Clear all data from the system"""
    try:
        connection = create_connection()
        if connection:
            cursor = connection.cursor()
            
            # Clear all tables
            cursor.execute("DELETE FROM attendance")
            cursor.execute("DELETE FROM unknown_faces")
            cursor.execute("DELETE FROM students")
            cursor.execute("DELETE FROM courses")
            
            connection.commit()
            cursor.close()
            connection.close()
            
            # Clear training model files
            if os.path.exists("TrainingModel/BUBTModel.yml"):
                os.remove("TrainingModel/BUBTModel.yml")
            if os.path.exists("TrainingModel/student_map.pkl"):
                os.remove("TrainingModel/student_map.pkl")
            
            # Clear directories
            if os.path.exists("StudentImages"):
                shutil.rmtree("StudentImages")
                os.makedirs("StudentImages", exist_ok=True)
            
            if os.path.exists("UnknownFaces"):
                shutil.rmtree("UnknownFaces")
                os.makedirs("UnknownFaces", exist_ok=True)
            
            # Reset face recognition
            global recognizer, id_to_student
            recognizer = None
            id_to_student = {}
            
            return jsonify({'success': True, 'message': 'All system data cleared successfully'})
    except Error as e:
        print(f"Error clearing all data: {e}")
        return jsonify({'success': False, 'message': f'Error clearing data: {e}'})

@app.route('/clear_students_only', methods=['POST'])
def clear_students_only():
    """Clear only student data but keep attendance records"""
    try:
        connection = create_connection()
        if connection:
            cursor = connection.cursor()
            
            # Clear students table
            cursor.execute("DELETE FROM students")
            
            connection.commit()
            cursor.close()
            connection.close()
            
            # Clear training model files
            if os.path.exists("TrainingModel/BUBTModel.yml"):
                os.remove("TrainingModel/BUBTModel.yml")
            if os.path.exists("TrainingModel/student_map.pkl"):
                os.remove("TrainingModel/student_map.pkl")
            
            # Clear StudentImages directory
            if os.path.exists("StudentImages"):
                shutil.rmtree("StudentImages")
                os.makedirs("StudentImages", exist_ok=True)
            
            # Reset face recognition
            global recognizer, id_to_student
            recognizer = None
            id_to_student = {}
            
            return jsonify({'success': True, 'message': 'All student data cleared successfully'})
    except Error as e:
        print(f"Error clearing students: {e}")
        return jsonify({'success': False, 'message': f'Error clearing students: {e}'})

@app.route('/clear_attendance_only', methods=['POST'])
def clear_attendance_only():
    """Clear only attendance records"""
    try:
        connection = create_connection()
        if connection:
            cursor = connection.cursor()
            
            # Clear attendance table
            cursor.execute("DELETE FROM attendance")
            
            connection.commit()
            cursor.close()
            connection.close()
            
            return jsonify({'success': True, 'message': 'All attendance records cleared successfully'})
    except Error as e:
        print(f"Error clearing attendance: {e}")
        return jsonify({'success': False, 'message': f'Error clearing attendance: {e}'})

@app.route('/video_feed')
def video_feed():
    """Video streaming route for face capture"""
    return Response(generate_frames(), 
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/attendance_feed')
def attendance_feed():
    """Video streaming route for attendance marking"""
    return Response(generate_attendance_frames(), 
                   mimetype='multipart/x-mixed-replace; boundary=frame')

def generate_frames():
    """Generate frames for face capture"""
    global capture_complete, captured_faces, capture_in_progress
    
    print("\n=== GENERATE_FRAMES STARTED ===")
    
    if not capture_in_progress:
        print("Capture not in progress, returning...")
        return
    
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        print("Error: Could not open camera")
        capture_complete = True
        capture_in_progress = False
        return
    
    print("Camera opened successfully")
    
    # Set camera properties
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    face_detector = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    sample_num = 0
    frame_count = 0
    
    print("Starting face capture loop...")
    
    try:
        while sample_num < 200 and capture_in_progress:
            success, frame = camera.read()
            if not success:
                print("Failed to read frame from camera")
                break
            
            frame_count += 1
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = face_detector.detectMultiScale(
                gray, 
                scaleFactor=1.1, 
                minNeighbors=5, 
                minSize=(30, 30)
            )
            
            # Process detected faces
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                
                # Capture face (every frame when face is detected)
                if sample_num < 200:
                    sample_num += 1
                    face_roi = gray[y:y+h, x:x+w]
                    
                    # Resize to standard size
                    face_roi = cv2.resize(face_roi, (200, 200))
                    captured_faces.append(face_roi)
                    
                    print(f"✓ Captured face {sample_num}/200")
                
                # Display counter on frame
                cv2.putText(frame, f"Face {sample_num}/200", (x, y-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            # Display status messages
            if len(faces) == 0:
                cv2.putText(frame, "No face detected - Position face in camera", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            else:
                cv2.putText(frame, "Face detected - Keep looking at camera", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            cv2.putText(frame, f"Captured: {sample_num}/200 faces", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Encode and yield frame
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                print("Failed to encode frame")
                break
                
            frame_bytes = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        print(f"\nCapture completed: {sample_num} faces captured")
        print(f"Total faces in memory: {len(captured_faces)}")
        
    except Exception as e:
        print(f"ERROR in generate_frames: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        camera.release()
        capture_in_progress = False
        capture_complete = True
        print("Camera released")
        print(f"Final state: complete={capture_complete}, in_progress={capture_in_progress}")


def generate_attendance_frames():
    """Generate frames for attendance marking"""
    # -------- CHANGED: Removed tracked_today set to allow multiple attendance marks --------
    # Now it will always update the time when a face is recognized
    
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        print("Error: Could not open camera")
        return
    
    while True:
        success, frame = camera.read()
        if not success:
            break
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces_detected = faceCascade.detectMultiScale(gray, 1.2, 5)
        
        for (x, y, w, h) in faces_detected:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (46, 125, 50), 3)
            
            if recognizer:
                label_id, conf = recognizer.predict(gray[y:y+h, x:x+w])
                confidence_percent = round(100 - conf)
                
                if conf < 60 and label_id in id_to_student:
                    student_id = id_to_student[label_id]
                    name, department = get_student_name(student_id)
                    
                    if name:
                        ts = time.time()
                        date_str = datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                        time_str = datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                        
                        # -------- CHANGED: Always insert/update attendance to track both in-time and out-time --------
                        if insert_attendance(student_id, name, department, date_str, time_str):
                            print(f"✓ Attendance Updated: {student_id} - {name} ({department}) at {time_str}")
                        
                        display_text = f"{name}"
                        display_text2 = f"ID: {student_id} | {department}"
                        color = (46, 125, 50)
                    else:
                        display_text = "Unknown Person"
                        display_text2 = "Not Registered"
                        color = (244, 67, 54)
                else:
                    display_text = "Unknown Person"
                    display_text2 = "Not Registered"
                    color = (244, 67, 54)
                    
                    if conf > 80:
                        noOfFile = len(os.listdir("UnknownFaces")) + 1
                        unknown_path = f"UnknownFaces/Unknown_{noOfFile}.jpg"
                        cv2.imwrite(unknown_path, frame[y:y+h, x:x+w])
                        log_unknown_face(unknown_path)
                
                cv2.putText(frame, display_text, (x+5, y-30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                cv2.putText(frame, display_text2, (x+5, y-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                cv2.putText(frame, f"Confidence: {confidence_percent}%", (x+5, y+h+25), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        cv2.putText(frame, "BUBT Attendance System - Live", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    
    camera.release()



@app.route('/get_attendance_stats')
def get_attendance_stats():
    """Get current attendance statistics"""
    today_attendance = get_today_attendance()
    return jsonify({
        'count': len(today_attendance),
        'attendance': [{'id': a[0], 'name': a[1], 'dept': a[2], 'time': a[3]} 
                      for a in today_attendance]
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)