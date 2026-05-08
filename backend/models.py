import enum
import datetime
import hashlib
import os
from sqlalchemy import Column, String, Integer, DateTime, Enum as SAEnum, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from backend.database import Base


class PriorityEnum(str, enum.Enum):
    URGENT = "urgent"    # Morado - < 3 horas hábiles
    HIGH = "high"        # Rojo - mismo día
    MEDIUM = "medium"    # Amarillo - 3 días hábiles
    NORMAL = "normal"    # Verde - 5 días hábiles


class StatusEnum(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    NEEDS_REVIEW = "needs_review"
    AI_SUGGESTED = "ai_suggested"


PRIORITY_CONFIG = {
    PriorityEnum.URGENT: {"color": "#7C3AED", "label": "Urgente", "hours": 3},
    PriorityEnum.HIGH: {"color": "#DC2626", "label": "Alta - Mismo Día", "hours": 8},
    PriorityEnum.MEDIUM: {"color": "#D97706", "label": "Media - 3 días", "days": 3},
    PriorityEnum.NORMAL: {"color": "#16A34A", "label": "Normal - 5 días", "days": 5},
}

STATUS_LABELS = {
    StatusEnum.PENDING: "Pendiente",
    StatusEnum.IN_PROGRESS: "Gestionando",
    StatusEnum.COMPLETED: "Realizado",
    StatusEnum.OVERDUE: "Atrasado",
    StatusEnum.NEEDS_REVIEW: "Requiere Revisión",
    StatusEnum.AI_SUGGESTED: "Sugerida por IA",
}


class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    email = Column(String(150), nullable=False)
    agent_role = Column(String(100))
    icon = Column(String(50), default="briefcase")
    tasks = relationship("Task", back_populates="department")
    users = relationship("User", back_populates="department")


class Brand(Base):
    __tablename__ = "brands"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    color = Column(String(10), default="#1E40AF")
    logo_emoji = Column(String(10), default="🏢")
    tasks = relationship("Task", back_populates="brand")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    role = Column(String(20), default="area")  # admin | area | readonly
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    department = relationship("Department", back_populates="users")


class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(250), nullable=False)
    description = Column(Text)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    priority = Column(SAEnum(PriorityEnum), nullable=False)
    status = Column(SAEnum(StatusEnum), default=StatusEnum.PENDING)
    deadline = Column(DateTime, nullable=True)
    created_by = Column(String(100), default="admin")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    action_token = Column(String(64), unique=True)
    email_sent = Column(Boolean, default=False)
    last_reminder_sent = Column(DateTime, nullable=True)
    ai_reasoning = Column(Text, nullable=True)
    ticket_number = Column(String(20), nullable=True)

    department = relationship("Department", back_populates="tasks")
    brand = relationship("Brand", back_populates="tasks")
    history = relationship("TaskHistory", back_populates="task", cascade="all, delete-orphan")

    def generate_token(self):
        self.action_token = hashlib.sha256(
            f"{self.id}-{self.title}-{os.urandom(16).hex()}".encode()
        ).hexdigest()[:32]


class TaskHistory(Base):
    __tablename__ = "task_history"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    action = Column(String(100), nullable=False)
    changed_by = Column(String(100), default="system")
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    notes = Column(Text, nullable=True)
    task = relationship("Task", back_populates="history")


class AISuggestion(Base):
    __tablename__ = "ai_suggestions"
    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    title = Column(String(250), nullable=False)
    description = Column(Text)
    priority = Column(SAEnum(PriorityEnum), default=PriorityEnum.MEDIUM)
    reasoning = Column(Text)
    status = Column(String(30), default="pending_approval")  # pending_approval | approved | rejected
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String(100), nullable=True)
    agent_name = Column(String(100), nullable=True)

    department = relationship("Department")
    brand = relationship("Brand")


class Attachment(Base):
    __tablename__ = "attachments"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    file_size = Column(Integer, default=0)
    content_type = Column(String(100))
    uploaded_by = Column(String(100), default="system")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    task = relationship("Task")


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(200), nullable=False)
    entity_type = Column(String(50))
    entity_id = Column(Integer, nullable=True)
    performed_by = Column(String(100), default="system")
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
