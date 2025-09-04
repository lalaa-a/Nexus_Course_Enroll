import sqlite3
import json
from typing import Dict, List, Optional
from shared.models import User, Course, Enrollment, Grade, Notification, UserRole
from datetime import datetime
import os

class SQLiteDatabase:
    def __init__(self, db_path: str = "nexus_enroll.db"):
        self.db_path = db_path
        self.users: Dict[str, User] = {}
        self.courses: Dict[str, Course] = {}
        self.enrollments: Dict[str, Enrollment] = {}
        self.grades: Dict[str, Grade] = {}
        self.notifications: Dict[str, Notification] = {}
        
        self._init_database()
        self._load_data()
    
    def _init_database(self):
        """Initialize SQLite database with tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                role TEXT NOT NULL,
                full_name TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')
        
        # Create courses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS courses (
                id TEXT PRIMARY KEY,
                course_code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                instructor_id TEXT NOT NULL,
                instructor_name TEXT NOT NULL,
                capacity INTEGER NOT NULL,
                enrolled_count INTEGER DEFAULT 0,
                schedule TEXT,
                location TEXT,
                prerequisites TEXT,
                department TEXT,
                credits INTEGER,
                FOREIGN KEY (instructor_id) REFERENCES users (id)
            )
        ''')
        
        # Create enrollments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS enrollments (
                id TEXT PRIMARY KEY,
                student_id TEXT NOT NULL,
                course_id TEXT NOT NULL,
                semester TEXT NOT NULL,
                status TEXT DEFAULT 'enrolled',
                enrollment_date TEXT NOT NULL,
                FOREIGN KEY (student_id) REFERENCES users (id),
                FOREIGN KEY (course_id) REFERENCES courses (id)
            )
        ''')
        
        # Create grades table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS grades (
                id TEXT PRIMARY KEY,
                student_id TEXT NOT NULL,
                course_id TEXT NOT NULL,
                grade TEXT NOT NULL,
                semester TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                submitted_by TEXT NOT NULL,
                submitted_date TEXT,
                FOREIGN KEY (student_id) REFERENCES users (id),
                FOREIGN KEY (course_id) REFERENCES courses (id),
                FOREIGN KEY (submitted_by) REFERENCES users (id)
            )
        ''')
        
        # Create notifications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                message TEXT NOT NULL,
                type TEXT NOT NULL,
                is_read BOOLEAN DEFAULT FALSE,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
        # Initialize with sample data if database is empty
        if self._is_database_empty():
            self._init_sample_data()
    
    def _is_database_empty(self) -> bool:
        """Check if database has any users"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        conn.close()
        return count == 0
    
    def _load_data(self):
        """Load all data from SQLite into memory dictionaries for compatibility"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Load users
        cursor.execute("SELECT * FROM users")
        for row in cursor.fetchall():
            user = User(
                id=row[0], username=row[1], email=row[2],
                role=UserRole(row[3]), full_name=row[4], is_active=bool(row[5])
            )
            self.users[user.id] = user
        
        # Load courses
        cursor.execute("SELECT * FROM courses")
        for row in cursor.fetchall():
            prerequisites = json.loads(row[10]) if row[10] else []
            course = Course(
                id=row[0], course_code=row[1], name=row[2], description=row[3],
                instructor_id=row[4], instructor_name=row[5], capacity=row[6],
                enrolled_count=row[7], schedule=row[8], location=row[9],
                prerequisites=prerequisites, department=row[11], credits=row[12]
            )
            self.courses[course.id] = course
        
        # Load enrollments
        cursor.execute("SELECT * FROM enrollments")
        for row in cursor.fetchall():
            enrollment = Enrollment(
                id=row[0], student_id=row[1], course_id=row[2],
                semester=row[3], status=row[4],
                enrollment_date=datetime.fromisoformat(row[5])
            )
            self.enrollments[enrollment.id] = enrollment
        
        # Load grades
        cursor.execute("SELECT * FROM grades")
        for row in cursor.fetchall():
            submitted_date = datetime.fromisoformat(row[7]) if row[7] else None
            grade = Grade(
                id=row[0], student_id=row[1], course_id=row[2],
                grade=row[3], semester=row[4], status=row[5],
                submitted_by=row[6], submitted_date=submitted_date
            )
            self.grades[grade.id] = grade
        
        # Load notifications
        cursor.execute("SELECT * FROM notifications")
        for row in cursor.fetchall():
            notification = Notification(
                id=row[0], user_id=row[1], message=row[2],
                type=row[3], is_read=bool(row[4]),
                created_at=datetime.fromisoformat(row[5])
            )
            self.notifications[notification.id] = notification
        
        conn.close()
    
    def _save_user(self, user: User):
        """Save user to SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO users 
            (id, username, email, role, full_name, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user.id, user.username, user.email, user.role.value, user.full_name, user.is_active))
        conn.commit()
        conn.close()
        self.users[user.id] = user
    
    def _save_course(self, course: Course):
        """Save course to SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        prerequisites_json = json.dumps(course.prerequisites)
        cursor.execute('''
            INSERT OR REPLACE INTO courses 
            (id, course_code, name, description, instructor_id, instructor_name, 
             capacity, enrolled_count, schedule, location, prerequisites, department, credits)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (course.id, course.course_code, course.name, course.description,
              course.instructor_id, course.instructor_name, course.capacity,
              course.enrolled_count, course.schedule, course.location,
              prerequisites_json, course.department, course.credits))
        conn.commit()
        conn.close()
        self.courses[course.id] = course
    
    def _save_enrollment(self, enrollment: Enrollment):
        """Save enrollment to SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO enrollments 
            (id, student_id, course_id, semester, status, enrollment_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (enrollment.id, enrollment.student_id, enrollment.course_id,
              enrollment.semester, enrollment.status, enrollment.enrollment_date.isoformat()))
        conn.commit()
        conn.close()
        self.enrollments[enrollment.id] = enrollment
    
    def _save_grade(self, grade: Grade):
        """Save grade to SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        submitted_date = grade.submitted_date.isoformat() if grade.submitted_date else None
        cursor.execute('''
            INSERT OR REPLACE INTO grades 
            (id, student_id, course_id, grade, semester, status, submitted_by, submitted_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (grade.id, grade.student_id, grade.course_id, grade.grade,
              grade.semester, grade.status, grade.submitted_by, submitted_date))
        conn.commit()
        conn.close()
        self.grades[grade.id] = grade
    
    def _save_notification(self, notification: Notification):
        """Save notification to SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO notifications 
            (id, user_id, message, type, is_read, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (notification.id, notification.user_id, notification.message,
              notification.type, notification.is_read, notification.created_at.isoformat()))
        conn.commit()
        conn.close()
        self.notifications[notification.id] = notification
    
    def sync_to_database(self):
        """Sync all in-memory changes back to database"""
        # This method ensures any direct modifications to the dictionaries are saved
        for user in self.users.values():
            self._save_user(user)
        for course in self.courses.values():
            self._save_course(course)
        for enrollment in self.enrollments.values():
            self._save_enrollment(enrollment)
        for grade in self.grades.values():
            self._save_grade(grade)
        for notification in self.notifications.values():
            self._save_notification(notification)
    
    def add_user(self, user: User):
        """Add a new user"""
        self._save_user(user)
    
    def add_course(self, course: Course):
        """Add a new course"""
        self._save_course(course)
    
    def add_enrollment(self, enrollment: Enrollment):
        """Add a new enrollment"""
        self._save_enrollment(enrollment)
    
    def add_grade(self, grade: Grade):
        """Add a new grade"""
        self._save_grade(grade)
    
    def add_notification(self, notification: Notification):
        """Add a new notification"""
        self._save_notification(notification)
    
    def refresh_user_from_db(self, user_id: str) -> Optional[User]:
        """Refresh a specific user from database if not in memory"""
        if user_id in self.users:
            return self.users[user_id]
        
        # User not in memory, try to load from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            user = User(
                id=row[0], username=row[1], email=row[2],
                role=UserRole(row[3]), full_name=row[4], is_active=bool(row[5])
            )
            self.users[user.id] = user  # Cache it in memory
            return user
        
        return None
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID, refreshing from database if needed"""
        return self.refresh_user_from_db(user_id)
    
    def refresh_course_from_db(self, course_id: str) -> Optional[Course]:
        """Refresh a specific course from database if not in memory"""
        if course_id in self.courses:
            return self.courses[course_id]
        
        # Course not in memory, try to load from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM courses WHERE id = ?", (course_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            prerequisites = json.loads(row[10]) if row[10] else []
            course = Course(
                id=row[0], course_code=row[1], name=row[2], description=row[3],
                instructor_id=row[4], instructor_name=row[5], capacity=row[6],
                enrolled_count=row[7], schedule=row[8], location=row[9],
                prerequisites=prerequisites, department=row[11], credits=row[12]
            )
            self.courses[course.id] = course  # Cache it in memory
            return course
        
        return None
    
    def refresh_all_courses_from_db(self):
        """Refresh all courses from database to get newly created ones"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM courses")
        
        for row in cursor.fetchall():
            prerequisites = json.loads(row[10]) if row[10] else []
            course = Course(
                id=row[0], course_code=row[1], name=row[2], description=row[3],
                instructor_id=row[4], instructor_name=row[5], capacity=row[6],
                enrolled_count=row[7], schedule=row[8], location=row[9],
                prerequisites=prerequisites, department=row[11], credits=row[12]
            )
            self.courses[course.id] = course  # Update/add to memory cache
        
        conn.close()
    
    def get_all_courses_refreshed(self) -> Dict[str, Course]:
        """Get all courses, refreshing from database to include new ones"""
        self.refresh_all_courses_from_db()
        return self.courses
    
    def refresh_all_users_from_db(self):
        """Refresh all users from database to get newly created ones"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users")
        
        for row in cursor.fetchall():
            user = User(
                id=row[0], username=row[1], email=row[2],
                role=UserRole(row[3]), full_name=row[4], is_active=bool(row[5])
            )
            self.users[user.id] = user  # Update/add to memory cache
        
        conn.close()
    
    def get_all_users_refreshed(self) -> Dict[str, User]:
        """Get all users, refreshing from database to include new ones"""
        self.refresh_all_users_from_db()
        return self.users
    
    def update_course_enrollment_count(self, course_id: str, new_count: int):
        """Update course enrollment count"""
        if course_id in self.courses:
            self.courses[course_id].enrolled_count = new_count
            self._save_course(self.courses[course_id])
    
    def delete_user(self, user_id: str):
        """Delete a user"""
        if user_id in self.users:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            conn.close()
            del self.users[user_id]
    
    def delete_course(self, course_id: str):
        """Delete a course"""
        if course_id in self.courses:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM courses WHERE id = ?", (course_id,))
            conn.commit()
            conn.close()
            del self.courses[course_id]
    
    def _init_sample_data(self):
        """Initialize database with sample data"""
        # Sample users
        users_data = [
            User(id="admin1", username="admin", email="admin@nexus.edu",
                 role=UserRole.ADMIN, full_name="System Administrator"),
            User(id="faculty1", username="prof_smith", email="smith@nexus.edu",
                 role=UserRole.FACULTY, full_name="Dr. John Smith"),
            User(id="faculty2", username="prof_jones", email="jones@nexus.edu",
                 role=UserRole.FACULTY, full_name="Dr. Sarah Jones"),
            User(id="student1", username="john_doe", email="john@student.nexus.edu",
                 role=UserRole.STUDENT, full_name="John Doe"),
            User(id="student2", username="jane_smith", email="jane@student.nexus.edu",
                 role=UserRole.STUDENT, full_name="Jane Smith")
        ]
        
        for user in users_data:
            self._save_user(user)
        
        # Sample courses
        courses_data = [
            Course(id="cs101", course_code="CS101", name="Introduction to Programming",
                   description="Basic programming concepts using Python",
                   instructor_id="faculty1", instructor_name="Dr. John Smith",
                   capacity=30, enrolled_count=15, schedule="MWF 9:00-10:00",
                   location="Room 101", department="Computer Science", credits=3),
            Course(id="cs201", course_code="CS201", name="Data Structures",
                   description="Advanced data structures and algorithms",
                   instructor_id="faculty1", instructor_name="Dr. John Smith",
                   capacity=25, enrolled_count=20, schedule="TTh 11:00-12:30",
                   location="Room 102", prerequisites=["cs101"],
                   department="Computer Science", credits=3),
            Course(id="math101", course_code="MATH101", name="Calculus I",
                   description="Differential and integral calculus",
                   instructor_id="faculty2", instructor_name="Dr. Sarah Jones",
                   capacity=40, enrolled_count=35, schedule="MWF 10:00-11:00",
                   location="Room 201", department="Mathematics", credits=4),
            Course(id="bus101", course_code="BUS101", name="Business Fundamentals",
                   description="Introduction to business principles",
                   instructor_id="faculty2", instructor_name="Dr. Sarah Jones",
                   capacity=50, enrolled_count=45, schedule="TTh 2:00-3:30",
                   location="Room 301", department="Business", credits=3)
        ]
        
        for course in courses_data:
            self._save_course(course)
        
        # Sample enrollments
        enrollments_data = [
            Enrollment(id="enr1", student_id="student1", course_id="cs101",
                      semester="Fall 2024", enrollment_date=datetime.now()),
            Enrollment(id="enr2", student_id="student1", course_id="math101",
                      semester="Fall 2024", enrollment_date=datetime.now()),
            Enrollment(id="enr3", student_id="student2", course_id="cs101",
                      semester="Fall 2024", enrollment_date=datetime.now())
        ]
        
        for enrollment in enrollments_data:
            self._save_enrollment(enrollment)
        
        # Sample grades
        grades_data = [
            Grade(id="grade1", student_id="student1", course_id="cs101",
                  grade="A", semester="Spring 2024", status="submitted",
                  submitted_by="faculty1", submitted_date=datetime.now())
        ]
        
        for grade in grades_data:
            self._save_grade(grade)

# Global database instance
db = SQLiteDatabase()
