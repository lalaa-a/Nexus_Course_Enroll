import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from shared.models import Course, Enrollment, EnrollmentRequest, Schedule, Grade
from shared.database import db
from typing import List, Optional
from datetime import datetime
import uuid
import uvicorn

app = FastAPI(title="Student Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/courses", response_model=List[Course])
async def browse_courses(
    department: Optional[str] = None,
    instructor: Optional[str] = None,
    keyword: Optional[str] = None
):
    """Browse course catalogue with filters"""
    courses = list(db.get_all_courses_refreshed().values())
    
    if department:
        courses = [c for c in courses if c.department.lower() == department.lower()]
    
    if instructor:
        courses = [c for c in courses if instructor.lower() in c.instructor_name.lower()]
    
    if keyword:
        courses = [c for c in courses if 
                  keyword.lower() in c.name.lower() or 
                  keyword.lower() in c.description.lower() or
                  keyword.lower() in c.course_code.lower()]
    
    return courses

@app.get("/courses/{course_id}", response_model=Course)
async def get_course_details(course_id: str):
    """Get detailed course information"""
    course = db.refresh_course_from_db(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course

@app.post("/enroll")
async def enroll_in_course(request: EnrollmentRequest):
    """Enroll student in a course with validation"""
    course = db.refresh_course_from_db(request.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    print(request.student_id)
    student = db.get_user_by_id(request.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Check if already enrolled
    existing_enrollment = None
    for enrollment in db.enrollments.values():
        if (enrollment.student_id == request.student_id and 
            enrollment.course_id == request.course_id and 
            enrollment.semester == request.semester and
            enrollment.status == "enrolled"):
            existing_enrollment = enrollment
            break
    
    if existing_enrollment:
        raise HTTPException(status_code=400, detail="Already enrolled in this course")
    
    # Check capacity
    if course.enrolled_count >= course.capacity:
        raise HTTPException(status_code=400, detail="Course is full")
    
    # Check prerequisites
    student_completed_courses = []
    for grade in db.grades.values():
        if (grade.student_id == request.student_id and 
            grade.status == "submitted" and 
            grade.grade in ["A", "B", "C", "D"]):
            student_completed_courses.append(grade.course_id)
    
    for prereq in course.prerequisites:
        if prereq not in student_completed_courses:
            prereq_course = db.refresh_course_from_db(prereq)
            prereq_name = prereq_course.name if prereq_course else prereq
            raise HTTPException(
                status_code=400, 
                detail=f"Prerequisite not met: {prereq_name}"
            )
    
    # Check time conflicts
    student_enrollments = [e for e in db.enrollments.values() 
                          if e.student_id == request.student_id and 
                          e.semester == request.semester and 
                          e.status == "enrolled"]
    
    for enrollment in student_enrollments:
        enrolled_course = db.refresh_course_from_db(enrollment.course_id)
        if enrolled_course and has_time_conflict(course.schedule, enrolled_course.schedule):
            raise HTTPException(
                status_code=400, 
                detail=f"Time conflict with {enrolled_course.name}"
            )
    
    # Create enrollment
    enrollment_id = str(uuid.uuid4())
    new_enrollment = Enrollment(
        id=enrollment_id,
        student_id=request.student_id,
        course_id=request.course_id,
        semester=request.semester,
        enrollment_date=datetime.now()
    )
    
    # Transaction: Update both enrollment and course capacity
    db.enrollments[enrollment_id] = new_enrollment
    course.enrolled_count += 1
    
    # Sync changes to SQLite database
    db.add_enrollment(new_enrollment)
    db._save_course(course)
    
    return {"message": "Successfully enrolled", "enrollment_id": enrollment_id}

@app.delete("/enroll/{enrollment_id}")
async def drop_course(enrollment_id: str):
    """Drop a course"""
    enrollment = db.enrollments.get(enrollment_id)
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    course = db.courses.get(enrollment.course_id)
    if course:
        course.enrolled_count = max(0, course.enrolled_count - 1)
        db._save_course(course)
    
    enrollment.status = "dropped"
    db._save_enrollment(enrollment)
    
    return {"message": "Successfully dropped course"}

@app.get("/students/{student_id}/schedule", response_model=Schedule)
async def get_student_schedule(student_id: str, semester: str):
    """Get student's current schedule"""
    student_enrollments = [e for e in db.enrollments.values() 
                          if e.student_id == student_id and 
                          e.semester == semester and 
                          e.status == "enrolled"]
    
    courses = []
    for enrollment in student_enrollments:
        course = db.refresh_course_from_db(enrollment.course_id)
        if course:
            courses.append(course)
    
    return Schedule(student_id=student_id, semester=semester, courses=courses)

@app.get("/students/{student_id}/grades", response_model=List[Grade])
async def get_student_grades(student_id: str):
    """Get student's academic progress"""
    student_grades = [g for g in db.grades.values() if g.student_id == student_id]
    return student_grades

@app.get("/students/{student_id}/enrollments", response_model=List[Enrollment])
async def get_student_enrollments(student_id: str):
    """Get all student enrollments"""
    return [e for e in db.enrollments.values() if e.student_id == student_id]

def has_time_conflict(schedule1: str, schedule2: str) -> bool:
    """Simple time conflict check - in production, use proper time parsing"""
    # This is a simplified implementation
    # Extract days from schedule (e.g., "MWF 9:00-10:00" -> "MWF")
    days1 = schedule1.split()[0] if schedule1.split() else ""
    days2 = schedule2.split()[0] if schedule2.split() else ""
    
    # Check if any days overlap
    for day in days1:
        if day in days2:
            # In a real implementation, also check time overlap
            return True
    
    return False

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "student"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8002)
