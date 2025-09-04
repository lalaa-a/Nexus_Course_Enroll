import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from shared.models import Course, User, UserRole
from shared.database import db
from typing import List, Optional
import uuid
import uvicorn

app = FastAPI(title="Admin Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Course & Program Management
@app.post("/courses", response_model=Course)
async def create_course(course_data: dict):
    """Create a new course"""
    course_id = str(uuid.uuid4())
    
    new_course = Course(
        id=course_id,
        course_code=course_data["course_code"],
        name=course_data["name"],
        description=course_data["description"],
        instructor_id=course_data["instructor_id"],
        instructor_name=course_data["instructor_name"],
        capacity=course_data["capacity"],
        schedule=course_data["schedule"],
        location=course_data["location"],
        prerequisites=course_data.get("prerequisites", []),
        department=course_data["department"],
        credits=course_data["credits"]
    )
    
    db.courses[course_id] = new_course
    db.add_course(new_course)
    return new_course

@app.put("/courses/{course_id}", response_model=Course)
async def update_course(course_id: str, course_data: dict):
    """Update an existing course"""
    course = db.refresh_course_from_db(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Update fields
    for field, value in course_data.items():
        if hasattr(course, field):
            setattr(course, field, value)
    
    db._save_course(course)
    return course

@app.delete("/courses/{course_id}")
async def delete_course(course_id: str):
    """Delete a course"""
    if course_id not in db.courses:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Check if students are enrolled
    enrolled_students = [e for e in db.enrollments.values() 
                        if e.course_id == course_id and e.status == "enrolled"]
    
    if enrolled_students:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete course with {len(enrolled_students)} enrolled students"
        )
    
    del db.courses[course_id]
    db.delete_course(course_id)
    return {"message": "Course deleted successfully"}

@app.get("/courses", response_model=List[Course])
async def get_all_courses():
    """Get all courses"""
    return list(db.get_all_courses_refreshed().values())

# Student & Faculty Management
@app.post("/users", response_model=User)
async def create_user(user_data: dict):
    """Create a new user (student/faculty)"""
    import requests
    
    user_id = str(uuid.uuid4())
    
    new_user = User(
        id=user_id,
        username=user_data["username"],
        email=user_data["email"],
        role=UserRole(user_data["role"]),
        full_name=user_data["full_name"],
        is_active=user_data.get("is_active", True)
    )
    
    # Add user to database
    db.users[user_id] = new_user
    db.add_user(new_user)
    
    # Add password to auth service for immediate login capability
    try:
        auth_response = requests.post(
            "http://127.0.0.1:8001/admin/add-password",
            json={
                "username": user_data["username"],
                "password": user_data["password"]
            },
            timeout=5
        )
        if not auth_response.ok:
            print(f"Warning: Failed to add password for user {user_data['username']}")
    except Exception as e:
        print(f"Warning: Could not communicate with auth service: {e}")
    
    return new_user

@app.put("/users/{user_id}", response_model=User)
async def update_user(user_id: str, user_data: dict):
    """Update user information"""
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    for field, value in user_data.items():
        if hasattr(user, field):
            if field == "role":
                setattr(user, field, UserRole(value))
            else:
                setattr(user, field, value)
    
    db._save_user(user)
    return user

@app.put("/users/{user_id}/deactivate")
async def deactivate_user(user_id: str):
    """Deactivate a user account"""
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = False
    db._save_user(user)
    return {"message": "User deactivated successfully"}

@app.delete("/users/{user_id}")
async def delete_user(user_id: str):
    """Delete a user account"""
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user has any enrollments
    user_enrollments = [e for e in db.enrollments.values() if e.student_id == user_id]
    if user_enrollments:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete user with {len(user_enrollments)} active enrollments"
        )
    
    # Check if user is an instructor for any courses
    instructor_courses = [c for c in db.courses.values() if c.instructor_id == user_id]
    if instructor_courses:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete user who is instructor for {len(instructor_courses)} courses"
        )
    
    db.delete_user(user_id)
    return {"message": "User deleted successfully"}

@app.get("/users", response_model=List[User])
async def get_all_users(role: Optional[str] = None):
    """Get all users, optionally filtered by role"""
    users = list(db.get_all_users_refreshed().values())
    
    if role:
        users = [u for u in users if u.role.value == role]
    
    return users

# Manual Enrollment Override
@app.post("/enrollments/override")
async def force_enrollment(enrollment_data: dict):
    """Force enroll a student (override capacity/prerequisites)"""
    from shared.models import Enrollment
    from datetime import datetime
    
    student_id = enrollment_data["student_id"]
    course_id = enrollment_data["course_id"]
    semester = enrollment_data["semester"]
    
    # Validate student and course exist
    if student_id not in db.users:
        raise HTTPException(status_code=404, detail="Student not found")
    
    if course_id not in db.courses:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Create enrollment regardless of constraints
    enrollment_id = str(uuid.uuid4())
    new_enrollment = Enrollment(
        id=enrollment_id,
        student_id=student_id,
        course_id=course_id,
        semester=semester,
        enrollment_date=datetime.now()
    )
    
    db.enrollments[enrollment_id] = new_enrollment
    db.add_enrollment(new_enrollment)
    
    # Update course capacity
    course = db.courses[course_id]
    course.enrolled_count += 1
    db._save_course(course)
    
    return {"message": "Force enrollment successful", "enrollment_id": enrollment_id}

# Reporting & Analytics
@app.get("/reports/enrollment-stats")
async def get_enrollment_statistics(department: Optional[str] = None):
    """Get enrollment statistics by department"""
    courses = list(db.courses.values())
    
    if department:
        courses = [c for c in courses if c.department.lower() == department.lower()]
    
    stats = []
    for course in courses:
        utilization = (course.enrolled_count / course.capacity * 100) if course.capacity > 0 else 0
        
        stats.append({
            "course_code": course.course_code,
            "course_name": course.name,
            "department": course.department,
            "capacity": course.capacity,
            "enrolled": course.enrolled_count,
            "utilization_percent": round(utilization, 2),
            "instructor": course.instructor_name
        })
    
    return {
        "total_courses": len(stats),
        "courses": stats,
        "summary": {
            "total_capacity": sum(s["capacity"] for s in stats),
            "total_enrolled": sum(s["enrolled"] for s in stats),
            "average_utilization": round(
                sum(s["utilization_percent"] for s in stats) / len(stats) if stats else 0, 2
            )
        }
    }

@app.get("/reports/faculty-workload")
async def get_faculty_workload_report():
    """Get faculty workload report"""
    faculty_stats = {}
    
    for course in db.courses.values():
        instructor_id = course.instructor_id
        if instructor_id not in faculty_stats:
            faculty_stats[instructor_id] = {
                "instructor_name": course.instructor_name,
                "courses": [],
                "total_students": 0,
                "total_courses": 0
            }
        
        faculty_stats[instructor_id]["courses"].append({
            "course_code": course.course_code,
            "course_name": course.name,
            "enrolled_students": course.enrolled_count
        })
        faculty_stats[instructor_id]["total_students"] += course.enrolled_count
        faculty_stats[instructor_id]["total_courses"] += 1
    
    return list(faculty_stats.values())

@app.get("/reports/course-popularity")
async def get_course_popularity_trends():
    """Get course popularity trends"""
    courses_with_popularity = []
    
    for course in db.courses.values():
        utilization = (course.enrolled_count / course.capacity * 100) if course.capacity > 0 else 0
        
        # Count waitlisted students (if any)
        waitlisted = len([e for e in db.enrollments.values() 
                         if e.course_id == course.id and e.status == "waitlisted"])
        
        courses_with_popularity.append({
            "course_code": course.course_code,
            "course_name": course.name,
            "department": course.department,
            "enrolled_students": course.enrolled_count,
            "capacity": course.capacity,
            "utilization_percent": round(utilization, 2),
            "waitlisted_students": waitlisted,
            "popularity_score": round(utilization + (waitlisted * 10), 2)  # Simple popularity metric
        })
    
    # Sort by popularity score
    courses_with_popularity.sort(key=lambda x: x["popularity_score"], reverse=True)
    
    return courses_with_popularity

@app.get("/reports/high-capacity-courses")
async def get_high_capacity_courses(threshold: float = 90.0):
    """Get courses above capacity threshold"""
    high_capacity_courses = []
    
    for course in db.courses.values():
        utilization = (course.enrolled_count / course.capacity * 100) if course.capacity > 0 else 0
        
        if utilization >= threshold:
            high_capacity_courses.append({
                "course_code": course.course_code,
                "course_name": course.name,
                "department": course.department,
                "capacity": course.capacity,
                "enrolled": course.enrolled_count,
                "utilization_percent": round(utilization, 2),
                "instructor": course.instructor_name
            })
    
    return {
        "threshold": threshold,
        "courses_above_threshold": len(high_capacity_courses),
        "courses": high_capacity_courses
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "admin"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8004)
