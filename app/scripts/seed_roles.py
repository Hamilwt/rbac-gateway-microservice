import sys
import os
from sqlalchemy.orm import Session

# Add the project root to the Python path so we can run this script directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.db.session import SessionLocal
from app.models.role import Role
from app.models.permission import Permission
from app.models.user import User
import bcrypt

def seed_db():
    db: Session = SessionLocal()
    try:
        # 1. Create default permissions
        perms = ["users:read", "users:write", "roles:read", "roles:write", "roles:assign", "inventory:read", "inventory:write"]
        db_perms = []
        for p in perms:
            # Check if it already exists so we can run this script safely multiple times
            perm = db.query(Permission).filter(Permission.name == p).first()
            if not perm:
                perm = Permission(name=p)
                db.add(perm)
            db_perms.append(perm)
        db.commit()

        # 2. Create the Admin role (gets all permissions)
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if not admin_role:
            admin_role = Role(name="admin")
            db.add(admin_role)
            db.commit()
            
            # Fetch the fresh permissions from DB and assign them
            all_perms = db.query(Permission).all()
            admin_role.permissions = all_perms
            db.commit()

        # 3. Create the Viewer role (gets only read permissions)
        viewer_role = db.query(Role).filter(Role.name == "viewer").first()
        if not viewer_role:
            viewer_role = Role(name="viewer")
            db.add(viewer_role)
            db.commit()
            
            read_perms = db.query(Permission).filter(Permission.name.like("%:read")).all()
            viewer_role.permissions = read_perms
            db.commit()

        # 4. Create a default admin user
        admin_email = "admin@example.com"
        admin_user = db.query(User).filter(User.email == admin_email).first()
        if not admin_user:
            # Hash a default password
            salt = bcrypt.gensalt()
            hashed_pw = bcrypt.hashpw(b"admin123", salt).decode('utf-8')
            
            admin_user = User(email=admin_email, hashed_password=hashed_pw)
            db.add(admin_user)
            db.commit()
            
            # Assign the admin role
            admin_user.roles = [admin_role]
            db.commit()

        print("Database seeding completed successfully!")
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()