"""
Database Models for Hotel Mitraya Quick POS System
===================================================
Provides relational database schemas for Users (Admin/Cashier), Categories,
Menu Items, and POS Bills with historical price snapshotting.
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
    role = Column(String(20), nullable=False, default="cashier")  # 'admin' or 'cashier'
    pin_hash = Column(String(255), nullable=False)
    name = Column(String(100), default="Staff")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "name": self.name,
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
    status = Column(String(20), default="COMPLETED")  # 'COMPLETED', 'OPEN', 'CANCELLED'
    created_at = Column(DateTime, default=datetime.now, index=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    items = relationship("PosBillItem", back_populates="pos_bill", cascade="all, delete-orphan")

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

