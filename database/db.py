"""
Database Setup & Session Management for Hotel Mitraya
=====================================================
Supports SQLite for development / local runs and PostgreSQL for production.
Includes automatic table creation and initial seed data.
"""

import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from werkzeug.security import generate_password_hash
from database.models import Base, User, Category, MenuItem, PosBill, PosBillItem

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Database URL configuration (PostgreSQL in production, SQLite locally)
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    # In serverless environments, check if /tmp is preferred
    if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        import tempfile
        db_path = os.path.join(tempfile.gettempdir(), "mitraya_pos.db")
    else:
        db_path = os.path.join(BASE_DIR, "mitraya_pos.db")
    DATABASE_URL = f"sqlite:///{db_path}"

# Fix postgres:// URL prefix if provided by older Heroku/Render configs
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))


@contextmanager
def get_db():
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def seed_default_data(session):
    """Seed initial Admin/Cashier users and standard Hotel Mitraya menu categories & items."""
    
    # 1. Seed Users if not present
    admin_user = session.query(User).filter_by(username="admin").first()
    if not admin_user:
        # Default Admin PIN: 2005 (matches existing legacy APP_PIN)
        admin_pin = os.environ.get("ADMIN_PIN", "2005").strip()
        admin_user = User(
            username="admin",
            role="admin",
            name="Hotel Admin",
            pin_hash=generate_password_hash(admin_pin)
        )
        session.add(admin_user)

    cashier_user = session.query(User).filter_by(username="cashier").first()
    if not cashier_user:
        # Default Cashier PIN: 1234
        cashier_pin = os.environ.get("CASHIER_PIN", "1234").strip()
        cashier_user = User(
            username="cashier",
            role="cashier",
            name="POS Cashier",
            pin_hash=generate_password_hash(cashier_pin)
        )
        session.add(cashier_user)

    session.flush()

    # 2. Seed Initial Categories and Menu Items if database is empty
    if session.query(Category).count() == 0:
        default_catalog = [
            {
                "category": "Special Dishes",
                "order": 1,
                "items": [
                    {"name": "Dahi Dhapata & Biryani Plate", "price": 130.0, "code": "SP01", "order": 1},
                    {"name": "Special Veg Thali", "price": 160.0, "code": "SP02", "order": 2},
                    {"name": "Deluxe Thali (Sweet + Papad)", "price": 200.0, "code": "SP03", "order": 3},
                    {"name": "Special Dahi Dhapata (2 Pcs)", "price": 110.0, "code": "SP04", "order": 4},
                ]
            },
            {
                "category": "Main Course & Rice",
                "order": 2,
                "items": [
                    {"name": "Veg Dum Biryani", "price": 140.0, "code": "RC01", "order": 1},
                    {"name": "Jeera Rice & Dal Tadka Combo", "price": 130.0, "code": "RC02", "order": 2},
                    {"name": "Paneer Butter Masala", "price": 150.0, "code": "RC03", "order": 3},
                    {"name": "Kaju Curry", "price": 180.0, "code": "RC04", "order": 4},
                    {"name": "Butter Roti / Chapati (2 Pcs)", "price": 30.0, "code": "RC05", "order": 5},
                ]
            },
            {
                "category": "Breakfast & Snacks",
                "order": 3,
                "items": [
                    {"name": "Special Misal Pav", "price": 80.0, "code": "SN01", "order": 1},
                    {"name": "Poha with Sev & Lime", "price": 40.0, "code": "SN02", "order": 2},
                    {"name": "Upma / Sheera", "price": 45.0, "code": "SN03", "order": 3},
                    {"name": "Batata Vada Sambar (2 Pcs)", "price": 50.0, "code": "SN04", "order": 4},
                    {"name": "Idli Sambar (2 Pcs)", "price": 50.0, "code": "SN05", "order": 5},
                    {"name": "Medu Vada (2 Pcs)", "price": 60.0, "code": "SN06", "order": 6},
                    {"name": "Masala Dosa", "price": 75.0, "code": "SN07", "order": 7},
                ]
            },
            {
                "category": "Beverages & Drinks",
                "order": 4,
                "items": [
                    {"name": "Special Masala Chai", "price": 20.0, "code": "BV01", "order": 1},
                    {"name": "South Indian Filter Coffee", "price": 30.0, "code": "BV02", "order": 2},
                    {"name": "Fresh Sweet Lassi", "price": 50.0, "code": "BV03", "order": 3},
                    {"name": "Taak / Spiced Buttermilk", "price": 25.0, "code": "BV04", "order": 4},
                    {"name": "Mineral Water Bottle (1L)", "price": 20.0, "code": "BV05", "order": 5},
                ]
            },
            {
                "category": "Desserts & Sweets",
                "order": 5,
                "items": [
                    {"name": "Gulab Jamun (2 Pcs)", "price": 50.0, "code": "DS01", "order": 1},
                    {"name": "Shrikhand Bowl", "price": 60.0, "code": "DS02", "order": 2},
                    {"name": "Ice Cream Scoop", "price": 40.0, "code": "DS03", "order": 3},
                ]
            }
        ]

        for cat_data in default_catalog:
            cat = Category(
                name=cat_data["category"],
                display_order=cat_data["order"],
                is_active=True
            )
            session.add(cat)
            session.flush()

            for item_data in cat_data["items"]:
                item = MenuItem(
                    category_id=cat.id,
                    name=item_data["name"],
                    price=item_data["price"],
                    code=item_data["code"],
                    display_order=item_data["order"],
                    is_available=True
                )
                session.add(item)


def init_db():
    """Create tables if they don't exist and seed defaults."""
    Base.metadata.create_all(bind=engine)
    with get_db() as session:
        seed_default_data(session)
