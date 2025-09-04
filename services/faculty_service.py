import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from shared.models import Course, Grade, GradeSubmission, User
from shared.database import db
from typing import List
from datetime import datetime
import uuid
import uvicorn

app = FastAPI(title="Faculty Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/faculty/{faculty_id}/courses", response_model=List[Course])
async def get_faculty_courses(faculty_id: str):
    """Get all courses taught by a faculty member"""
    faculty_courses = [c for c in db.get_all_courses_refreshed().values() if c.instructor_id == faculty_id]
    return faculty_courses

@app.get("/courses/{course_id}/roster")
async def get_course_roster(course_id: str):
    """Get real-time roster for a course"""
    course = db.refresh_course_from_db(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Get enrolled students
    enrolled_students = []
    for enrollment in db.enrollments.values():
        if (enrollment.course_id == course_id and 
            enrollment.status == "enrolled"):
            student = db.get_user_by_id(enrollment.student_id)
            if student:
                enrolled_students.append({
                    "student_id": student.id,
                    "name": student.full_name,
                    "email": student.email,
                    "enrollment_date": enrollment.enrollment_date
                })
    
    return {
        "course": course,
        "enrolled_students": enrolled_students,
        "enrollment_count": len(enrolled_students)
    }

@app.post("/courses/{course_id}/grades")
async def submit_grades(course_id: str, grade_submission: GradeSubmission):
    """Submit grades for a course"""
    course = db.refresh_course_from_db(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    submitted_grades = []
    errors = []
    
    for grade_data in grade_submission.grades:
        try:
            student_id = grade_data["student_id"]
            grade_value = grade_data["grade"]
            
            # Validate student is enrolled
            is_enrolled = any(
                e.student_id == student_id and 
                e.course_id == course_id and 
                e.status == "enrolled"
                for e in db.enrollments.values()
            )
            
            if not is_enrolled:
                errors.append(f"Student {student_id} is not enrolled in this course")
                continue
            
            # Validate grade
            if grade_value not in ["A", "B", "C", "D", "F", "I", "W"]:
                errors.append(f"Invalid grade '{grade_value}' for student {student_id}")
                continue
            
            # Create or update grade
            grade_id = str(uuid.uuid4())
            new_grade = Grade(
                id=grade_id,
                student_id=student_id,
                course_id=course_id,
                grade=grade_value,
                semester="Fall 2024",  # In production, get from request
                status="pending",
                submitted_by=course.instructor_id,
                submitted_date=datetime.now()
            )
            
            db.grades[grade_id] = new_grade
            db.add_grade(new_grade)
            submitted_grades.append(new_grade)
            
        except KeyError as e:
            errors.append(f"Missing required field: {e}")
        except Exception as e:
            errors.append(f"Error processing grade: {str(e)}")
    
    return {
        "message": f"Processed {len(submitted_grades)} grades",
        "submitted_grades": len(submitted_grades),
        "errors": errors
    }

@app.put("/grades/{grade_id}/submit")
async def finalize_grade(grade_id: str):
    """Finalize a grade (change from pending to submitted)"""
    grade = db.grades.get(grade_id)
    if not grade:
        raise HTTPException(status_code=404, detail="Grade not found")
    
    grade.status = "submitted"
    db._save_grade(grade)
    return {"message": "Grade finalized successfully"}

@app.get("/courses/{course_id}/grades", response_model=List[Grade])
async def get_course_grades(course_id: str):
    """Get all grades for a course"""
    course_grades = [g for g in db.grades.values() if g.course_id == course_id]
    return course_grades

@app.put("/courses/{course_id}/update")
async def request_course_update(course_id: str, updates: dict):
    """Request course information updates (requires admin approval)"""
    course = db.refresh_course_from_db(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # In a real system, this would create a request for admin approval
    # For this demo, we'll directly update allowed fields
    allowed_updates = ["description", "capacity"]
    
    updated_fields = []
    for field, value in updates.items():
        if field in allowed_updates:
            setattr(course, field, value)
            updated_fields.append(field)
    
    if updated_fields:
        db._save_course(course)
    
    return {
        "message": "Course update request submitted",
        "updated_fields": updated_fields,
        "note": "In production, this would require admin approval"
    }

@app.get("/faculty/{faculty_id}/workload")
async def get_faculty_workload(faculty_id: str):
    """Get faculty workload statistics"""
    faculty_courses = [c for c in db.courses.values() if c.instructor_id == faculty_id]
    
    total_students = sum(c.enrolled_count for c in faculty_courses)
    total_courses = len(faculty_courses)
    
    return {
        "faculty_id": faculty_id,
        "total_courses": total_courses,
        "total_students": total_students,
        "courses": faculty_courses
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "faculty"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8003)
