"""
Database Setup & Session Management for Hotel Mitraya
=====================================================
Supports SQLite for development / local restaurant runs and PostgreSQL for production.
Includes non-destructive automatic schema migration, initial seed data, and audit logging.
"""

import os
from contextlib import contextmanager
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from werkzeug.security import generate_password_hash
from database.models import (
    Base, User, Category, MenuItem, Order, OrderItem, PosBill, PosBillItem,
    PrintJob, PrinterConfigModel, AuditLog, PrintEvent, DiningTable
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

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

# Fix postgres:// URL prefix and query params for compatibility
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if "channel_binding=" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("&channel_binding=require", "").replace("?channel_binding=require", "?").replace("channel_binding=require", "")
    if DATABASE_URL.endswith("?"):
        DATABASE_URL = DATABASE_URL[:-1]

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


def record_audit_log(db_session, action: str, entity: str = None, entity_id: str = None, details: str = None,
                     user_id: int = None, username: str = None, role: str = None, ip_address: str = None, **kwargs):
    """
    Safely record an action in the audit trail without disrupting business operations.
    """
    try:
        log = AuditLog(
            user_id=user_id,
            username=username or "System",
            role=role or "system",
            action=action,
            entity=entity,
            entity_id=str(entity_id) if entity_id is not None else None,
            details=details,
            ip_address=ip_address
        )
        db_session.add(log)
    except Exception as e:
        print(f"[WARN] Failed to record audit log: {e}")


def seed_default_data(session):
    """Seed initial Admin, Cashier, and Waiter users, default printer config, and standard menu."""
    
    # 1. Seed Users if not present
    admin_user = session.query(User).filter_by(username="admin").first()
    if not admin_user:
        admin_pin = os.environ.get("ADMIN_PIN", "2005").strip()
        admin_user = User(
            username="admin",
            role="admin",
            name="Hotel Admin",
            pin_hash=generate_password_hash(admin_pin)
        )
        session.add(admin_user)
    else:
        # Keep PIN synchronized with requested credentials
        admin_pin = os.environ.get("ADMIN_PIN", "2005").strip()
        admin_user.pin_hash = generate_password_hash(admin_pin)

    cashier_user = session.query(User).filter_by(username="cashier").first()
    if not cashier_user:
        cashier_pin = os.environ.get("CASHIER_PIN", "5678").strip()
        cashier_user = User(
            username="cashier",
            role="cashier",
            name="Counter Cashier",
            pin_hash=generate_password_hash(cashier_pin)
        )
        session.add(cashier_user)
    else:
        cashier_pin = os.environ.get("CASHIER_PIN", "5678").strip()
        cashier_user.pin_hash = generate_password_hash(cashier_pin)

    waiter_user = session.query(User).filter_by(username="waiter").first()
    if not waiter_user:
        waiter_pin = os.environ.get("WAITER_PIN", "1234").strip()
        waiter_user = User(
            username="waiter",
            role="waiter",
            name="Floor Waiter",
            pin_hash=generate_password_hash(waiter_pin)
        )
        session.add(waiter_user)
    else:
        waiter_pin = os.environ.get("WAITER_PIN", "1234").strip()
        waiter_user.pin_hash = generate_password_hash(waiter_pin)

    session.flush()

    # 2. Seed Default Printer Configuration if not present
    default_printer = session.query(PrinterConfigModel).filter_by(is_default=True).first()
    if not default_printer:
        default_printer = PrinterConfigModel(
            name="Main Counter Thermal Printer",
            connection_type="WINDOWS_DRIVER",
            paper_width=80,
            printer_name="",
            is_default=True,
            cut_enabled=True,
            header_title="HOTEL MITRAYA",
            footer_text="Thank You! Visit Again."
        )
        session.add(default_printer)
        session.flush()

    # 3. Seed Initial Categories and Menu Items if database is empty
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

    # 4. Seed Dining Tables (1 to 12) if not present
    if session.query(DiningTable).count() == 0:
        for t_num in range(1, 13):
            tbl = DiningTable(
                table_number=t_num,
                capacity=4,
                status="VACANT"
            )
            session.add(tbl)
        session.flush()


def auto_migrate_columns():
    """Ensure newly added columns exist in SQLite/Postgres without manual drop table or data loss."""
    try:
        with engine.begin() as conn:
            # Check SQLite table info
            if engine.dialect.name == "sqlite":
                # PosBills columns check
                res = conn.execute(text("PRAGMA table_info(pos_bills)")).fetchall()
                existing_cols = [r[1] for r in res]
                if existing_cols:
                    if "order_type" not in existing_cols:
                        conn.execute(text("ALTER TABLE pos_bills ADD COLUMN order_type VARCHAR(20) DEFAULT 'WALK_IN'"))
                    if "table_number" not in existing_cols:
                        conn.execute(text("ALTER TABLE pos_bills ADD COLUMN table_number INTEGER"))
                    if "customer_name" not in existing_cols:
                        conn.execute(text("ALTER TABLE pos_bills ADD COLUMN customer_name VARCHAR(100)"))
                    if "notes" not in existing_cols:
                        conn.execute(text("ALTER TABLE pos_bills ADD COLUMN notes VARCHAR(255)"))
                    if "updated_at" not in existing_cols:
                        conn.execute(text("ALTER TABLE pos_bills ADD COLUMN updated_at DATETIME"))
                
                # Users columns check
                user_cols_res = conn.execute(text("PRAGMA table_info(users)")).fetchall()
                user_cols = [r[1] for r in user_cols_res]
                if user_cols:
                    if "is_active" not in user_cols:
                        conn.execute(text("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1"))
                    if "updated_at" not in user_cols:
                        conn.execute(text("ALTER TABLE users ADD COLUMN updated_at DATETIME"))
            else:
                # PostgreSQL / MySQL
                for col_sql in [
                    "ALTER TABLE pos_bills ADD COLUMN IF NOT EXISTS order_type VARCHAR(20) DEFAULT 'WALK_IN'",
                    "ALTER TABLE pos_bills ADD COLUMN IF NOT EXISTS table_number INTEGER",
                    "ALTER TABLE pos_bills ADD COLUMN IF NOT EXISTS customer_name VARCHAR(100)",
                    "ALTER TABLE pos_bills ADD COLUMN IF NOT EXISTS notes VARCHAR(255)",
                    "ALTER TABLE pos_bills ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE",
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
                ]:
                    try:
                        conn.execute(text(col_sql))
                    except Exception:
                        pass
    except Exception as e:
        print(f"[WARN] Auto-migration check: {e}")


def init_db():
    """Create tables if they don't exist and seed defaults."""
    Base.metadata.create_all(bind=engine)
    auto_migrate_columns()
    with get_db() as session:
        seed_default_data(session)
