from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    STUDENT = "student"
    FACULTY = "faculty"
    ADMIN = "admin"

class User(BaseModel):
    id: str
    username: str
    email: str
    role: UserRole
    full_name: str
    is_active: bool = True

class Course(BaseModel):
    id: str
    course_code: str
    name: str
    description: str
    instructor_id: str
    instructor_name: str
    capacity: int
    enrolled_count: int = 0
    schedule: str
    location: str
    prerequisites: List[str] = []
    department: str
    credits: int

class Enrollment(BaseModel):
    id: str
    student_id: str
    course_id: str
    semester: str
    status: str = "enrolled"  # enrolled, dropped, waitlisted
    enrollment_date: datetime

class Grade(BaseModel):
    id: str
    student_id: str
    course_id: str
    grade: str
    semester: str
    status: str = "pending"  # pending, submitted
    submitted_by: str
    submitted_date: Optional[datetime] = None

class Schedule(BaseModel):
    student_id: str
    semester: str
    courses: List[Course]

class Notification(BaseModel):
    id: str
    user_id: str
    message: str
    type: str  # enrollment, grade, system
    is_read: bool = False
    created_at: datetime

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    user: User

class EnrollmentRequest(BaseModel):
    student_id: str
    course_id: str
    semester: str

class GradeSubmission(BaseModel):
    course_id: str
    grades: List[dict]  # [{"student_id": "123", "grade": "A"}]

class SignupRequest(BaseModel):
    username: str
    password: str
    email: str
    full_name: str

class SignupResponse(BaseModel):
    message: str
    user: User
