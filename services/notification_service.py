import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from shared.models import Notification
from shared.database import db
from typing import List
from datetime import datetime
import uuid
import uvicorn

app = FastAPI(title="Notification Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/notifications")
async def create_notification(notification_data: dict):
    """Create a new notification"""
    notification_id = str(uuid.uuid4())
    
    notification = Notification(
        id=notification_id,
        user_id=notification_data["user_id"],
        message=notification_data["message"],
        type=notification_data["type"],
        created_at=datetime.now()
    )
    
    db.notifications[notification_id] = notification
    db.add_notification(notification)
    return {"message": "Notification created", "notification_id": notification_id}

@app.get("/users/{user_id}/notifications", response_model=List[Notification])
async def get_user_notifications(user_id: str, unread_only: bool = False):
    """Get notifications for a user"""
    user_notifications = [n for n in db.notifications.values() if n.user_id == user_id]
    
    if unread_only:
        user_notifications = [n for n in user_notifications if not n.is_read]
    
    # Sort by creation date (newest first)
    user_notifications.sort(key=lambda x: x.created_at, reverse=True)
    
    return user_notifications

@app.put("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str):
    """Mark a notification as read"""
    notification = db.notifications.get(notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.is_read = True
    db._save_notification(notification)
    return {"message": "Notification marked as read"}

@app.post("/notifications/broadcast")
async def broadcast_notification(notification_data: dict):
    """Send notification to multiple users"""
    user_ids = notification_data["user_ids"]
    message = notification_data["message"]
    notification_type = notification_data["type"]
    
    created_notifications = []
    
    for user_id in user_ids:
        notification_id = str(uuid.uuid4())
        notification = Notification(
            id=notification_id,
            user_id=user_id,
            message=message,
            type=notification_type,
            created_at=datetime.now()
        )
        
        db.notifications[notification_id] = notification
        db.add_notification(notification)
        created_notifications.append(notification_id)
    
    return {
        "message": f"Broadcast sent to {len(user_ids)} users",
        "notification_ids": created_notifications
    }

@app.post("/notifications/course-available")
async def notify_course_available(course_id: str):
    """Notify waitlisted students when a course becomes available"""
    # Find waitlisted students for this course
    waitlisted_enrollments = [e for e in db.enrollments.values() 
                             if e.course_id == course_id and e.status == "waitlisted"]
    
    course = db.courses.get(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    notifications_sent = []
    
    for enrollment in waitlisted_enrollments:
        notification_id = str(uuid.uuid4())
        notification = Notification(
            id=notification_id,
            user_id=enrollment.student_id,
            message=f"A spot has opened up in {course.name} ({course.course_code}). You can now enroll!",
            type="enrollment",
            created_at=datetime.now()
        )
        
        db.notifications[notification_id] = notification
        db.add_notification(notification)
        notifications_sent.append(notification_id)
    
    return {
        "message": f"Notified {len(notifications_sent)} waitlisted students",
        "notifications_sent": len(notifications_sent)
    }

@app.post("/notifications/grade-submitted")
async def notify_grade_submitted(student_id: str, course_id: str):
    """Notify student when grade is submitted"""
    course = db.courses.get(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    notification_id = str(uuid.uuid4())
    notification = Notification(
        id=notification_id,
        user_id=student_id,
        message=f"Your grade for {course.name} ({course.course_code}) has been submitted.",
        type="grade",
        created_at=datetime.now()
    )
    
    db.notifications[notification_id] = notification
    db.add_notification(notification)
    
    return {"message": "Grade notification sent", "notification_id": notification_id}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "notification"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8005)
