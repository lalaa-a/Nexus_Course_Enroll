import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from shared.models import LoginRequest, LoginResponse, User, SignupRequest, SignupResponse, UserRole
from shared.database import db
import uuid
import uvicorn

app = FastAPI(title="Authentication Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple authentication - in production, use proper password hashing
SIMPLE_PASSWORDS = {
    "admin": "admin123",
    "prof_smith": "prof123",
    "prof_jones": "prof123",
    "john_doe": "student123",
    "jane_smith": "student123"
}

@app.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    
    '''
    # Simple authentication check
    if request.username not in SIMPLE_PASSWORDS:
        raise HTTPException(status_code=401, detail="Invalid username")
    
    if SIMPLE_PASSWORDS[request.username] != request.password:
        raise HTTPException(status_code=401, detail="Invalid password")
    '''

    # Find user in database (refresh from SQLite to get newly created users)
    user = None
    for u in db.get_all_users_refreshed().values():
        if u.username == request.username:
            user = u
            break
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Generate simple token (in production, use JWT)
    token = f"token_{user.id}_{user.role.value}"
    
    return LoginResponse(access_token=token, user=user)

@app.get("/verify/{token}")
async def verify_token(token: str):
    # Simple token verification
    if not token.startswith("token_"):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    parts = token.split("_")
    if len(parts) != 3:
        raise HTTPException(status_code=401, detail="Invalid token format")
    
    user_id = parts[1]
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return {"user": user}

@app.post("/signup", response_model=SignupResponse)
async def signup(request: SignupRequest):
    # Check if username already exists
    for user in db.users.values():
        if user.username == request.username:
            raise HTTPException(status_code=400, detail="Username already exists")
    
    # Check if email already exists
    for user in db.users.values():
        if user.email == request.email:
            raise HTTPException(status_code=400, detail="Email already exists")
    
    # Validate input
    if len(request.username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters long")
    
    if len(request.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")
    
    if "@" not in request.email:
        raise HTTPException(status_code=400, detail="Invalid email format")
    
    if len(request.full_name.strip()) < 2:
        raise HTTPException(status_code=400, detail="Full name must be at least 2 characters long")
    
    # Generate unique user ID
    user_id = f"student_{uuid.uuid4().hex[:8]}"
    
    # Create new student user
    new_user = User(
        id=user_id,
        username=request.username,
        email=request.email,
        role=UserRole.STUDENT,
        full_name=request.full_name.strip(),
        is_active=True
    )
    
    # Add user to database
    db.add_user(new_user)
    
    # Add password to simple passwords dict (for demo purposes)
    SIMPLE_PASSWORDS[request.username] = request.password
    
    return SignupResponse(
        message="Student account created successfully! You can now login with your credentials.",
        user=new_user
    )

@app.post("/admin/add-password")
async def add_password_for_user(request: dict):
    """Add password for admin-created users"""
    username = request.get("username")
    password = request.get("password")
    
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required")
    
    # Add password to simple passwords dict
    SIMPLE_PASSWORDS[username] = password
    
    return {"message": "Password added successfully"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "auth"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
