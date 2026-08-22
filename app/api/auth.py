from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.models.role import Role
from app.schemas.user import UserCreate, UserResponse
from app.schemas.auth import Token
from app.core.security import (
    get_password_hash, 
    verify_password, 
    create_access_token, 
    create_refresh_token
)

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    # 1. Check if user exists
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # 2. Hash password and create user
    hashed_pw = get_password_hash(user_in.password)
    new_user = User(email=user_in.email, hashed_password=hashed_pw)
    
    # 3. Assign the default 'viewer' role automatically
    viewer_role = db.query(Role).filter(Role.name == "viewer").first()
    if viewer_role:
        new_user.roles.append(viewer_role)
        
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Notice we return the UserResponse model, which strips out the password automatically!
    return new_user

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2PasswordRequestForm automatically looks for 'username' and 'password' in the request body
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
        
    # Extract all unique permissions from all roles the user holds
    permissions = []
    for role in user.roles:
        for perm in role.permissions:
            if perm.name not in permissions:
                permissions.append(perm.name)
                
    # Generate tokens
    access_token = create_access_token(subject=user.id, permissions=permissions)
    refresh_token = create_refresh_token(subject=user.id)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }