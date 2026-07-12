"""Database seed script — creates default roles and admin user on first run."""
import uuid
from sqlalchemy.orm import Session
from models.organization import Organization
from models.role import Role
from models.user import User
from models.role import user_roles
from core.security import hash_password


DEFAULT_ROLES = [
    {"name": "Admin", "description": "Full system access"},
    {"name": "Legal Officer", "description": "Manages legal documents and reviews"},
    {"name": "Compliance Officer", "description": "Monitors compliance and policies"},
    {"name": "Reviewer", "description": "Reviews documents and entities"},
    {"name": "Viewer", "description": "Read-only access"},
]


def seed_database(db: Session) -> None:
    """Seed roles, default organization, and admin user if they do not exist."""
    # --- Roles ---
    existing_roles = db.query(Role).count()
    if existing_roles == 0:
        for role_data in DEFAULT_ROLES:
            db.add(Role(id=uuid.uuid4(), **role_data))
        db.commit()
        print("[SEED] Roles created.")

    # --- Default Organization ---
    org = db.query(Organization).filter(Organization.name == "Admin Org").first()
    if not org:
        org = Organization(
            id=uuid.uuid4(),
            name="Admin Org",
            email="admin@redactai.in",
            address="Mumbai, India",
        )
        db.add(org)
        db.commit()
        db.refresh(org)
        print("[SEED] Default organization created.")

    # --- Default Admin User ---
    admin = db.query(User).filter(User.email == "admin@redactai.in").first()
    if not admin:
        admin_role = db.query(Role).filter(Role.name == "Admin").first()
        admin = User(
            id=uuid.uuid4(),
            email="admin@redactai.in",
            hashed_password=hash_password("Admin@123456"),
            full_name="System Admin",
            organization_id=org.id,
            is_active=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        if admin_role:
            db.execute(user_roles.insert().values(user_id=admin.id, role_id=admin_role.id))
            db.commit()
        print("[SEED] Admin user created (admin@redactai.in / Admin@123456).")
