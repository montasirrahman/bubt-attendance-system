# 🎓 BUBT Face Recognition Attendance System

A comprehensive **face recognition-based attendance system** built with **Flask**, **OpenCV**, and **MySQL**.  
This system automatically recognizes registered students and marks their attendance in real time using facial recognition technology.

---

## 🚀 Features

- 👤 **Student Registration** with face capture (200 images per student)  
- 🧠 **Face Recognition** for automatic attendance marking  
- 📸 **Real-time Attendance Tracking** with live camera feed  
- 📑 **Comprehensive Reports** with CSV export functionality  
- 🔐 **Admin Panel** for data management and system cleanup  
- 🏋️ **Training Module** for building recognition models  
- 🗄️ **Database Management** with automatic table creation  

---

## 🛠️ Technology Stack

| Component | Technology |
|------------|-------------|
| **Backend** | Flask (Python) |
| **Face Recognition** | OpenCV, LBPH Recognizer |
| **Database** | MySQL |
| **Frontend** | HTML, CSS, JavaScript, Bootstrap |
| **Computer Vision** | OpenCV, Haar Cascades |

---

## 📋 Prerequisites

- Python 3.8+
- MySQL Server
- Conda (for environment management)

---

## ⚙️ Installation

### 1. Clone the Repository
```bash
git clone https://github.com/montasirrahman/bubt-attendance-system.git
cd bubt-attendance-system
```

### 2. Set Up the Environment
```bash
# Create environment from YAML file
conda env create -f face_app.yml

# Activate the environment
conda activate face_app
```

### 3. Database Setup

The system automatically creates the **database** and **tables** on first run.  
Ensure MySQL is running and update credentials in `app.py` if needed.

**Optional Manual Setup:**
```sql
CREATE DATABASE bubt_attendance_system;
```

**Database Configuration in `app.py`:**
```python
DB_CONFIG = {
    'host': 'localhost',
    'user': 'your_mysql_username',
    'password': 'your_mysql_password',
    'database': 'bubt_attendance_system'
}
```

### 4. Run the Application
```bash
python app.py
```
The app will run at 👉 [http://localhost:5000](http://localhost:5000)

---

## 📁 Project Structure

```
bubt-attendance-system/
├── app.py                 # Main Flask application
├── face_app.yml           # Conda environment configuration
├── templates/             # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── register.html
│   ├── capture_faces.html
│   ├── train.html
│   ├── attendance.html
│   ├── view_attendance.html
│   ├── report.html
│   └── admin.html
├── static/                # Static files (CSS, JS, images)
├── StudentImages/         # Student face images (auto-created)
├── TrainingModel/         # Trained models (auto-created)
└── UnknownFaces/          # Unknown face captures (auto-created)
```

---

## 🗄️ Database Schema

### **Students Table**
| Column | Type | Description |
|--------|------|-------------|
| student_id | INT (PK) | Unique student ID |
| name | VARCHAR | Student name |
| department | VARCHAR | Department name |
| semester | VARCHAR | Semester |
| section | VARCHAR | Section |
| face_data | BLOB | Stored face encodings |
| is_trained | BOOLEAN | Training status |
| created_at | TIMESTAMP | Creation date |
| updated_at | TIMESTAMP | Update date |

### **Attendance Table**
| Column | Type | Description |
|--------|------|-------------|
| attendance_id | INT (AI, PK) | Unique attendance ID |
| student_id | INT (FK) | Linked to student |
| student_name | VARCHAR | Name of student |
| department | VARCHAR | Department name |
| course_code | VARCHAR | Course code |
| date | DATE | Attendance date |
| time | TIME | Attendance time |
| timestamp | DATETIME | Full timestamp |

### **Additional Tables**
- `unknown_faces` – Logs unrecognized faces  
- `courses` – For course management (future use)

---

## 🔧 Usage Guide

### 1. Student Registration
- Navigate to **Register Student**
- Fill in details: ID, Name, Department, etc.
- Capture 200 images per student
- System stores faces in the database

### 2. Model Training
- Go to **Train Model**
- Click **Train Model** button
- Model saved under `TrainingModel/`

### 3. Mark Attendance
- Go to **Mark Attendance**
- Recognizes students in real-time
- Marks attendance automatically
- Prevents duplicate entries per day

### 4. View Reports
- Go to **Reports**
- Select a date to view attendance
- Export attendance as CSV

### 5. Admin Panel
- View system statistics
- Clear:
  - All data
  - Only student data
  - Only attendance data

---

## ⚙️ Configuration

### **Face Recognition Settings**
| Setting | Value |
|----------|--------|
| Training Images | 200 per student |
| Confidence Threshold | < 60% for match |
| Detector | Haar Cascade |
| Recognizer | LBPH Face Recognizer |

### **Camera Settings**
| Setting | Value |
|----------|--------|
| Resolution | 640x480 |
| Frame Rate | Real-time optimized |
| Face Size | 200x200 pixels |

---

## 🗂️ Auto-Created Directories

| Directory | Purpose |
|------------|----------|
| `StudentImages/` | Stores captured student images |
| `TrainingModel/` | Stores trained models |
| `UnknownFaces/` | Stores unrecognized faces |

---

## 🔒 Security Features

- Session-based authentication  
- Input validation and sanitization  
- Secure file handling  
- Database transaction management  

---

## 🐛 Troubleshooting

| Issue | Solution |
|--------|-----------|
| **Camera not working** | Check camera permissions or close other apps |
| **Database connection error** | Verify MySQL is running and credentials are correct |
| **Face recognition not working** | Ensure model is trained and lighting is good |
| **Import errors** | Activate the correct conda environment |

---

## 📊 Performance

- Real-time face detection and recognition  
- Supports multiple students simultaneously  
- Optimized database operations  
- Efficient image processing  

---

## 🤝 Contributing

1. Fork the repository  
2. Create a feature branch  
3. Commit your changes  
4. Push to your branch  
5. Create a Pull Request  

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **BUBT** — for the project inspiration  
- **OpenCV Community** — for facial recognition libraries  
- **Flask Developers** — for the backend framework  

---

> 💡 **Note:** Ensure good lighting and proper camera placement for optimal face recognition accuracy. Works best with front-facing cameras and uniform lighting.
