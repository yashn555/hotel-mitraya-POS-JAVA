"""
Database Models for Hotel Mitraya Restaurant POS & Ordering System
===================================================================
Provides relational database schemas for:
- Users (Admin, Cashier, Waiter)
- Categories & Menu Items
- Restaurant Orders & Order Items (Unified Lifecycle)
- POS Bills & Historical Price Snapshots
- Thermal Print Jobs & Hardware Configuration (58mm & 80mm)
- System Audit Logs
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    role = Column(String(20), nullable=False, default="cashier")  # 'admin', 'cashier', 'waiter'
    pin_hash = Column(String(255), nullable=False)
    name = Column(String(100), default="Staff")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "name": self.name,
            "is_active": self.is_active if self.is_active is not None else True,
            "created_at": self.created_at.strftime("%d/%m/%Y %I:%M %p") if self.created_at else None
        }


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

    items = relationship("MenuItem", back_populates="category", cascade="all, delete-orphan", order_by="MenuItem.display_order")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "display_order": self.display_order,
            "is_active": self.is_active,
            "items_count": len([i for i in self.items if i.is_available]) if self.items else 0
        }


class MenuItem(Base):
    __tablename__ = "menu_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(150), nullable=False, index=True)
    price = Column(Float, nullable=False, default=0.0)
    is_available = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)
    code = Column(String(30), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    category = relationship("Category", back_populates="items")

    def to_dict(self):
        return {
            "id": self.id,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else "Uncategorized",
            "name": self.name,
            "price": float(self.price),
            "is_available": self.is_available,
            "display_order": self.display_order,
            "code": self.code or ""
        }


class DiningTable(Base):
    """
    Physical Restaurant Dining Tables (Tables 1 to 12):
    Tracks real-time occupancy, active table order reference, and capacity.
    """
    __tablename__ = "dining_tables"

    id = Column(Integer, primary_key=True, autoincrement=True)
    table_number = Column(Integer, unique=True, nullable=False, index=True)
    capacity = Column(Integer, default=4)
    status = Column(String(20), default="VACANT")  # 'VACANT', 'OCCUPIED', 'RESERVED'
    current_order_id = Column(Integer, nullable=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "table_number": self.table_number,
            "capacity": self.capacity,
            "status": self.status or "VACANT",
            "is_occupied": self.status == "OCCUPIED",
            "current_order_id": self.current_order_id,
            "updated_at": self.updated_at.strftime("%d/%m/%Y %I:%M %p") if self.updated_at else None
        }


class Order(Base):
    """
    Unified Restaurant Order Lifecycle:
    States: DRAFT -> PLACED -> CONFIRMED -> PREPARING -> READY -> COMPLETED / CANCELLED
    """
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_number = Column(String(50), unique=True, nullable=False, index=True)  # ORD-20260905-001 or ORD-000001
    source = Column(String(20), nullable=False, default="WAITER")  # 'WAITER', 'COUNTER', 'WALK_IN'
    order_type = Column(String(20), nullable=False, default="DINING")  # 'DINING', 'WALK_IN', 'TAKEAWAY'
    table_number = Column(Integer, nullable=True, index=True)  # 1 to 12
    customer_name = Column(String(100), nullable=True)
    notes = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default="PLACED", index=True)
    subtotal = Column(Float, nullable=False, default=0.0)
    total_amount = Column(Float, nullable=False, default=0.0)
    
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by_role = Column(String(30), default="waiter")
    created_by_name = Column(String(100), default="Staff")
    
    bill_id = Column(Integer, ForeignKey("pos_bills.id", ondelete="SET NULL"), nullable=True, index=True)
    
    created_at = Column(DateTime, default=datetime.now, index=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    bill = relationship("PosBill")

    @property
    def table_label(self):
        return f"Table {self.table_number}" if self.table_number else "Walk-in / Takeaway"

    def to_dict(self):
        return {
            "id": self.id,
            "order_number": self.order_number,
            "source": self.source,
            "order_type": self.order_type,
            "table_number": self.table_number,
            "table_label": f"Table {self.table_number}" if self.table_number else "Walk-in / Takeaway",
            "customer_name": self.customer_name or "",
            "notes": self.notes or "",
            "status": self.status,
            "subtotal": float(self.subtotal),
            "total_amount": float(self.total_amount),
            "created_by_user_id": self.created_by_user_id,
            "created_by_role": self.created_by_role,
            "created_by_name": self.created_by_name,
            "bill_id": self.bill_id,
            "bill_number": self.bill.bill_number if self.bill else None,
            "created_at": self.created_at.strftime("%d/%m/%Y %I:%M %p") if self.created_at else None,
            "created_at_time": self.created_at.strftime("%I:%M %p") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%d/%m/%Y %I:%M %p") if self.updated_at else None,
            "date_iso": self.created_at.isoformat() if self.created_at else None,
            "items_count": len(self.items) if self.items else 0,
            "items": [item.to_dict() for item in self.items] if self.items else []
        }


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    menu_item_id = Column(Integer, nullable=True)
    item_name = Column(String(150), nullable=False)
    unit_price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False, default=1.0)
    item_notes = Column(String(255), nullable=True)  # e.g., "Less spicy", "No onion"
    total_price = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "menu_item_id": self.menu_item_id,
            "item_name": self.item_name,
            "unit_price": float(self.unit_price),
            "quantity": float(self.quantity),
            "item_notes": self.item_notes or "",
            "total_price": float(self.total_price)
        }


class PosBill(Base):
    __tablename__ = "pos_bills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bill_number = Column(String(50), unique=True, nullable=False, index=True)  # POS-000001
    subtotal = Column(Float, nullable=False, default=0.0)
    discount = Column(Float, nullable=False, default=0.0)
    total_amount = Column(Float, nullable=False, default=0.0)
    payment_mode = Column(String(20), nullable=False, default="CASH")  # CASH, UPI, CARD
    received_amount = Column(Float, nullable=True)
    change_amount = Column(Float, nullable=True)
    order_type = Column(String(20), nullable=False, default="WALK_IN")  # 'WALK_IN' or 'DINING'
    table_number = Column(Integer, nullable=True, index=True)  # Table 1 to 12
    customer_name = Column(String(100), nullable=True)
    notes = Column(String(255), nullable=True)
    cashier_role = Column(String(50), default="cashier")
    status = Column(String(20), default="COMPLETED", index=True)  # 'COMPLETED', 'OPEN', 'CANCELLED'
    created_at = Column(DateTime, default=datetime.now, index=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    items = relationship("PosBillItem", back_populates="pos_bill", cascade="all, delete-orphan")
    print_jobs = relationship("PrintJob", back_populates="pos_bill", cascade="all, delete-orphan")

    @property
    def table_label(self):
        return f"Table {self.table_number}" if self.table_number else "Walk-in"

    def to_dict(self):
        return {
            "id": self.id,
            "bill_number": self.bill_number,
            "order_type": self.order_type or "WALK_IN",
            "table_number": self.table_number,
            "table_label": f"Table {self.table_number}" if self.table_number else "Walk-in",
            "customer_name": self.customer_name or "",
            "notes": self.notes or "",
            "subtotal": float(self.subtotal),
            "discount": float(self.discount),
            "total_amount": float(self.total_amount),
            "payment_mode": self.payment_mode,
            "received_amount": float(self.received_amount) if self.received_amount is not None else None,
            "change_amount": float(self.change_amount) if self.change_amount is not None else None,
            "cashier_role": self.cashier_role,
            "status": self.status,
            "created_at": self.created_at.strftime("%d/%m/%Y %I:%M %p") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%d/%m/%Y %I:%M %p") if self.updated_at else None,
            "date_iso": self.created_at.isoformat() if self.created_at else None,
            "items_count": len(self.items) if self.items else 0,
            "items": [item.to_dict() for item in self.items] if self.items else []
        }


class PosBillItem(Base):
    __tablename__ = "pos_bill_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pos_bill_id = Column(Integer, ForeignKey("pos_bills.id", ondelete="CASCADE"), nullable=False, index=True)
    menu_item_id = Column(Integer, nullable=True)
    item_name = Column(String(150), nullable=False)   # Historical Snapshot
    unit_price = Column(Float, nullable=False)        # Historical Snapshot
    quantity = Column(Float, nullable=False, default=1.0)
    total_price = Column(Float, nullable=False)

    pos_bill = relationship("PosBill", back_populates="items")

    def to_dict(self):
        return {
            "id": self.id,
            "pos_bill_id": self.pos_bill_id,
            "menu_item_id": self.menu_item_id,
            "item_name": self.item_name,
            "unit_price": float(self.unit_price),
            "quantity": float(self.quantity),
            "total_price": float(self.total_price)
        }


class PrintJob(Base):
    """
    Decoupled Print Job Management:
    Status: PRINT_PENDING, PRINTING, PRINTED, FAILED
    """
    __tablename__ = "print_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pos_bill_id = Column(Integer, ForeignKey("pos_bills.id", ondelete="SET NULL"), nullable=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True)
    job_type = Column(String(30), default="FINAL_BILL")  # 'FINAL_BILL', 'KOT', 'TEST_SLIP'
    printer_name = Column(String(100), nullable=True)
    paper_width = Column(Integer, default=80)  # 58 or 80
    status = Column(String(30), default="PRINT_PENDING", index=True)  # 'PRINT_PENDING', 'PRINTING', 'PRINTED', 'FAILED'
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now, index=True)
    printed_at = Column(DateTime, nullable=True)

    pos_bill = relationship("PosBill", back_populates="print_jobs")

    def to_dict(self):
        return {
            "id": self.id,
            "pos_bill_id": self.pos_bill_id,
            "order_id": self.order_id,
            "job_type": self.job_type,
            "printer_name": self.printer_name or "Default Thermal Printer",
            "paper_width": self.paper_width,
            "status": self.status,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "created_at": self.created_at.strftime("%d/%m/%Y %I:%M:%S %p") if self.created_at else None,
            "printed_at": self.printed_at.strftime("%d/%m/%Y %I:%M:%S %p") if self.printed_at else None,
            "bill_number": self.pos_bill.bill_number if self.pos_bill else None
        }


class PrinterConfigModel(Base):
    """
    Persistent Thermal Printer Configuration:
    Supports 58mm & 80mm, Windows installed driver, ESC/POS Raw, Network/IP Socket.
    """
    __tablename__ = "printer_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, default="Counter Thermal Printer")
    connection_type = Column(String(30), default="WINDOWS_DRIVER")  # 'WINDOWS_DRIVER', 'ESC_POS_RAW', 'NETWORK_RAW', 'BROWSER_PRINT'
    paper_width = Column(Integer, default=80)  # 58 or 80
    printer_name = Column(String(150), nullable=True)  # Installed OS printer name
    ip_address = Column(String(50), nullable=True)     # For Network/IP thermal printer
    port = Column(Integer, default=9100)
    is_default = Column(Boolean, default=True)
    cut_enabled = Column(Boolean, default=True)
    header_title = Column(String(100), default="HOTEL MITRAYA")
    footer_text = Column(String(255), default="Thank You! Visit Again.")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "connection_type": self.connection_type,
            "paper_width": self.paper_width,
            "printer_name": self.printer_name or "",
            "ip_address": self.ip_address or "",
            "port": self.port,
            "is_default": self.is_default,
            "cut_enabled": self.cut_enabled,
            "header_title": self.header_title,
            "footer_text": self.footer_text
        }


class PrintEvent(Base):
    __tablename__ = "print_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pos_bill_id = Column(Integer, ForeignKey("pos_bills.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(30), default="FINAL_BILL")  # 'FINAL_BILL'
    created_at = Column(DateTime, default=datetime.now, index=True)

    bill = relationship("PosBill")

    def to_dict(self):
        return {
            "event_id": self.id,
            "event_type": self.event_type,
            "created_at": self.created_at.strftime("%d/%m/%Y %I:%M %p") if self.created_at else None,
            "bill": self.bill.to_dict() if self.bill else None
        }


class AuditLog(Base):
    """
    Production Audit Logging for Hotel Mitraya:
    Tracks auth logins, order creates/modifications/cancels, bill creates/settles/reprints,
    menu price changes, staff PIN updates, and printer settings changes.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True, index=True)
    username = Column(String(50), nullable=True)
    role = Column(String(30), nullable=True)
    action = Column(String(50), nullable=False, index=True)  # LOGIN, CREATE_ORDER, SETTLE_BILL, REPRINT, UPDATE_PRICE, etc.
    entity = Column(String(50), nullable=True)              # 'ORDER', 'BILL', 'MENU_ITEM', 'USER', 'PRINTER'
    entity_id = Column(String(50), nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.now, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.username or "System",
            "role": self.role or "staff",
            "action": self.action,
            "entity": self.entity or "",
            "entity_id": self.entity_id or "",
            "details": self.details or "",
            "ip_address": self.ip_address or "",
            "created_at": self.created_at.strftime("%d/%m/%Y %I:%M:%S %p") if self.created_at else None,
            "date_iso": self.created_at.isoformat() if self.created_at else None
        }
