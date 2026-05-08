"""Hiram Group – AI Enterprise Agent Platform."""
import datetime
import os
from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel
import warnings
warnings.filterwarnings("ignore", ".*bcrypt.*")

from backend.database import get_db, init_db
from backend.models import (
    Task, Department, Brand, User, TaskHistory, AISuggestion,
    Attachment, AuditLog, PriorityEnum, StatusEnum, PRIORITY_CONFIG, STATUS_LABELS
)
from backend.date_utils import calculate_deadline, format_deadline, is_overdue
from backend.email_service import send_task_email, send_reminder_email
from backend.ai_service import generate_suggestions, chat_with_agent
from backend.config import SECRET_KEY, ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_EMAIL, ENVIRONMENT

# ── App Setup ──────────────────────────────────────────────────────────────────
app = FastAPI(title="Hiram Group AI Platform", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

pwd_ctx = CryptContext(schemes=["sha256_crypt"], deprecated="auto")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")


# ── Auth Helpers ───────────────────────────────────────────────────────────────
def create_token(data: dict):
    payload = data.copy()
    payload["exp"] = datetime.datetime.utcnow() + datetime.timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token") or request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="No autenticado")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Token inválido")
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=401, detail="Usuario no encontrado")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")


def require_admin(user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Acceso denegado: se requiere rol administrador")
    return user


def audit(db: Session, action: str, entity_type: str = None, entity_id: int = None,
          performed_by: str = "sistema", details: str = None):
    log = AuditLog(action=action, entity_type=entity_type, entity_id=entity_id,
                   performed_by=performed_by, details=details)
    db.add(log)


# ── Pydantic Schemas ────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    department_id: int
    brand_id: int
    priority: PriorityEnum
    created_by: Optional[str] = "admin"


class TaskUpdate(BaseModel):
    status: Optional[StatusEnum] = None
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[PriorityEnum] = None


class SuggestionAction(BaseModel):
    action: str  # "approve" | "reject"
    notes: Optional[str] = None


class ChatMessage(BaseModel):
    message: str
    department_name: str
    history: Optional[List[dict]] = []


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: str = "area"
    department_id: Optional[int] = None


class DepartmentCreate(BaseModel):
    name: str
    email: str
    agent_role: Optional[str] = None
    icon: Optional[str] = "briefcase"


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    agent_role: Optional[str] = None
    icon: Optional[str] = None


# ── Upload directory ────────────────────────────────────────────────────────────
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ── Startup ────────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    init_db()
    _seed_data()
    from backend.scheduler import start_scheduler
    start_scheduler()
    print("✅ Hiram Group AI Platform iniciado correctamente")


def _seed_data():
    from backend.database import SessionLocal
    db = SessionLocal()
    try:
        # Departments
        departments_data = [
            {"name": "Gerencia General", "email": "tomashiram@poffice.cl", "agent_role": "CEO", "icon": "crown"},
            {"name": "RRHH", "email": "rrhh@poffice.cl", "agent_role": "HR Manager", "icon": "users"},
            {"name": "Asistente RRHH", "email": "asistenterrhh@poffice.cl", "agent_role": "HR Assistant", "icon": "user-check"},
            {"name": "Finanzas", "email": "finanzas@poffice.cl", "agent_role": "CFO", "icon": "dollar-sign"},
            {"name": "Ventas", "email": "ventas@poffice.cl", "agent_role": "Sales Manager", "icon": "trending-up"},
            {"name": "Administración de Contratos", "email": "supervisiongeneral@poffice.cl", "agent_role": "Contracts Admin", "icon": "file-text"},
            {"name": "Administración General", "email": "administracion@poffice.cl", "agent_role": "Admin", "icon": "settings"},
            {"name": "Marketing", "email": "marketing@poffice.cl", "agent_role": "CMO", "icon": "megaphone"},
            {"name": "Atención al Cliente", "email": "atencionalcliente@poffice.cl", "agent_role": "CX Manager", "icon": "headphones"},
        {"name": "Logística", "email": "logistica@poffice.cl", "agent_role": "Logistics Manager", "icon": "truck"},
        ]

        for d in departments_data:
            if not db.query(Department).filter(Department.name == d["name"]).first():
                dept = Department(**d)
                db.add(dept)

        # Brands
        brands_data = [
            {"name": "ProClean Facilities", "description": "Servicios profesionales de limpieza y facility management", "color": "#1E40AF", "logo_emoji": "🏢"},
            {"name": "Paper Office", "description": "Soluciones de insumos y administración para oficinas", "color": "#0F766E", "logo_emoji": "📋"},
            {"name": "Aromas Premium", "description": "Aromatización de espacios y marketing olfativo", "color": "#7C3AED", "logo_emoji": "✨"},
            {"name": "BearClean", "description": "Productos de limpieza para el hogar", "color": "#EA580C", "logo_emoji": "🐻"},
        ]

        for b in brands_data:
            if not db.query(Brand).filter(Brand.name == b["name"]).first():
                brand = Brand(**b)
                db.add(brand)

        db.commit()

        # Admin user
        if not db.query(User).filter(User.username == ADMIN_USERNAME).first():
            admin = User(
                username=ADMIN_USERNAME,
                email=ADMIN_EMAIL,
                password_hash=pwd_ctx.hash(ADMIN_PASSWORD),
                role="admin",
            )
            db.add(admin)
            db.commit()

        print("✅ Datos iniciales cargados")
    except Exception as e:
        print(f"[SEED ERROR] {e}")
        db.rollback()
    finally:
        db.close()


# ── Static Files & Frontend ────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


# ── Auth Routes ────────────────────────────────────────────────────────────────
@app.post("/api/auth/login")
async def login(req: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not pwd_ctx.verify(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    token = create_token({"sub": user.username, "role": user.role})
    response.set_cookie("access_token", token, httponly=True, max_age=86400)
    audit(db, f"Login exitoso: {user.username}", "user", user.id, user.username)
    db.commit()

    return {
        "access_token": token,
        "username": user.username,
        "role": user.role,
        "department_id": user.department_id,
    }


@app.post("/api/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Sesión cerrada"}


@app.get("/api/auth/me")
async def get_me(user: User = Depends(get_current_user)):
    return {"username": user.username, "role": user.role, "email": user.email, "department_id": user.department_id}


# ── Department Routes ──────────────────────────────────────────────────────────
@app.get("/api/departments")
async def get_departments(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    depts = db.query(Department).all()
    result = []
    for d in depts:
        tasks = db.query(Task).filter(Task.department_id == d.id).all()
        pending = sum(1 for t in tasks if t.status in (StatusEnum.PENDING, StatusEnum.IN_PROGRESS))
        overdue_count = sum(1 for t in tasks if t.status == StatusEnum.OVERDUE or (
            t.status != StatusEnum.COMPLETED and is_overdue(t.deadline)))
        completed = sum(1 for t in tasks if t.status == StatusEnum.COMPLETED)
        ai_suggestions = db.query(AISuggestion).filter(
            AISuggestion.department_id == d.id,
            AISuggestion.status == "pending_approval"
        ).count()

        result.append({
            "id": d.id,
            "name": d.name,
            "email": d.email,
            "agent_role": d.agent_role,
            "icon": d.icon,
            "stats": {
                "total": len(tasks),
                "pending": pending,
                "overdue": overdue_count,
                "completed": completed,
                "ai_suggestions": ai_suggestions,
            }
        })
    return result


# ── Brand Routes ───────────────────────────────────────────────────────────────
@app.get("/api/brands")
async def get_brands(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    brands = db.query(Brand).all()
    return [{"id": b.id, "name": b.name, "description": b.description,
             "color": b.color, "logo_emoji": b.logo_emoji} for b in brands]


# ── Task Routes ────────────────────────────────────────────────────────────────
@app.get("/api/tasks")
async def get_tasks(
    department_id: Optional[int] = None,
    brand_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    q = db.query(Task)
    if user.role == "area" and user.department_id:
        q = q.filter(Task.department_id == user.department_id)
    if department_id:
        q = q.filter(Task.department_id == department_id)
    if brand_id:
        q = q.filter(Task.brand_id == brand_id)
    if status:
        q = q.filter(Task.status == status)

    tasks = q.order_by(Task.created_at.desc()).limit(200).all()

    result = []
    for t in tasks:
        overdue_flag = is_overdue(t.deadline) and t.status != StatusEnum.COMPLETED
        result.append({
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "department_id": t.department_id,
            "department_name": t.department.name if t.department else "N/A",
            "brand_id": t.brand_id,
            "brand_name": t.brand.name if t.brand else "N/A",
            "brand_color": t.brand.color if t.brand else "#1E40AF",
            "priority": t.priority.value,
            "priority_label": PRIORITY_CONFIG[t.priority]["label"],
            "priority_color": PRIORITY_CONFIG[t.priority]["color"],
            "status": t.status.value,
            "status_label": STATUS_LABELS.get(t.status, t.status.value),
            "deadline": format_deadline(t.deadline),
            "deadline_raw": t.deadline.isoformat() if t.deadline else None,
            "created_by": t.created_by,
            "created_at": t.created_at.strftime("%d/%m/%Y %H:%M") if t.created_at else None,
            "updated_at": t.updated_at.strftime("%d/%m/%Y %H:%M") if t.updated_at else None,
            "is_overdue": overdue_flag,
            "ticket_number": t.ticket_number,
            "ai_reasoning": t.ai_reasoning,
            "email_sent": t.email_sent,
        })
    return result


@app.post("/api/tasks")
async def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    dept = db.query(Department).filter(Department.id == task_data.department_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")
    brand = db.query(Brand).filter(Brand.id == task_data.brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Marca no encontrada")

    deadline = calculate_deadline(task_data.priority)

    # Generate ticket number for customer service
    ticket_number = None
    if dept.name == "Atención al Cliente":
        count = db.query(Task).count()
        ticket_number = f"TKT-{datetime.datetime.now().strftime('%Y%m')}-{count+1:04d}"

    task = Task(
        title=task_data.title,
        description=task_data.description,
        department_id=task_data.department_id,
        brand_id=task_data.brand_id,
        priority=task_data.priority,
        status=StatusEnum.PENDING,
        deadline=deadline.replace(tzinfo=None) if hasattr(deadline, 'tzinfo') else deadline,
        created_by=user.username,
        ticket_number=ticket_number,
    )
    task.generate_token()
    db.add(task)
    db.flush()

    history = TaskHistory(
        task_id=task.id,
        action=f"Tarea creada con prioridad {PRIORITY_CONFIG[task.priority]['label']}",
        changed_by=user.username,
    )
    db.add(history)

    audit(db, f"Tarea creada: {task.title}", "task", task.id, user.username,
          f"Área: {dept.name} | Marca: {brand.name} | Prioridad: {task.priority.value}")
    db.commit()
    db.refresh(task)

    # Send email
    sent = send_task_email(task, dept, brand)
    if sent:
        task.email_sent = True
        history2 = TaskHistory(task_id=task.id, action="Correo enviado al área", changed_by="sistema")
        db.add(history2)
        db.commit()

    return {
        "id": task.id,
        "title": task.title,
        "ticket_number": ticket_number,
        "deadline": format_deadline(task.deadline),
        "message": "Tarea creada y enviada correctamente",
        "email_sent": sent,
    }


@app.put("/api/tasks/{task_id}")
async def update_task(
    task_id: int,
    update: TaskUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    changes = []
    if update.status:
        old_status = task.status
        task.status = update.status
        changes.append(f"Estado: {STATUS_LABELS.get(old_status)} → {STATUS_LABELS.get(update.status)}")
    if update.title:
        task.title = update.title
        changes.append("Título actualizado")
    if update.description:
        task.description = update.description
        changes.append("Descripción actualizada")
    if update.priority:
        task.priority = update.priority
        task.deadline = calculate_deadline(update.priority)
        if task.deadline and hasattr(task.deadline, 'tzinfo'):
            task.deadline = task.deadline.replace(tzinfo=None)
        changes.append(f"Prioridad actualizada a {PRIORITY_CONFIG[update.priority]['label']}")

    task.updated_at = datetime.datetime.utcnow()

    if changes:
        history = TaskHistory(
            task_id=task.id,
            action=" | ".join(changes),
            changed_by=user.username,
        )
        db.add(history)
        audit(db, f"Tarea #{task_id} actualizada", "task", task_id, user.username, " | ".join(changes))

    db.commit()
    return {"message": "Tarea actualizada", "changes": changes}


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: int, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    title = task.title
    db.delete(task)
    audit(db, f"Tarea eliminada: {title}", "task", task_id, user.username)
    db.commit()
    return {"message": "Tarea eliminada"}


@app.post("/api/tasks/{task_id}/reminder")
async def send_reminder(task_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    sent = send_reminder_email(task, task.department, task.brand)
    if sent:
        task.last_reminder_sent = datetime.datetime.utcnow()
        history = TaskHistory(task_id=task.id, action="Recordatorio manual enviado", changed_by=user.username)
        db.add(history)
        audit(db, f"Recordatorio manual enviado tarea #{task_id}", "task", task_id, user.username)
        db.commit()
    return {"sent": sent}


# ── Email Action (no auth required – token based) ──────────────────────────────
@app.get("/api/tasks/action/{token}/{action}", response_class=HTMLResponse)
async def email_action(token: str, action: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.action_token == token).first()
    if not task:
        return HTMLResponse("""<html><body style="font-family:Arial;text-align:center;padding:60px;">
            <h2 style="color:#DC2626;">❌ Enlace inválido o expirado</h2>
            <p>Este enlace no es válido. Por favor contacta a administración.</p>
        </body></html>""")

    status_map = {
        "in_progress": StatusEnum.IN_PROGRESS,
        "completed": StatusEnum.COMPLETED,
        "needs_review": StatusEnum.NEEDS_REVIEW,
    }
    new_status = status_map.get(action)
    if not new_status:
        raise HTTPException(status_code=400, detail="Acción inválida")

    old_status = task.status
    task.status = new_status
    task.updated_at = datetime.datetime.utcnow()

    action_labels = {
        "in_progress": "Estoy gestionándolo",
        "completed": "Realizado",
        "needs_review": "Requiere revisión",
    }

    history = TaskHistory(
        task_id=task.id,
        action=f"Estado actualizado desde correo: {action_labels.get(action, action)}",
        changed_by=f"Email: {task.department.email if task.department else 'area'}",
    )
    db.add(history)
    audit(db, f"Acción desde email en tarea #{task.id}: {action}", "task", task.id,
          f"email:{task.department.email if task.department else 'N/A'}")
    db.commit()

    icon = {"in_progress": "⚙️", "completed": "✅", "needs_review": "🔍"}.get(action, "✓")
    color = {"in_progress": "#2563EB", "completed": "#16A34A", "needs_review": "#D97706"}.get(action, "#1E3A5F")
    label = action_labels.get(action, action)

    return HTMLResponse(f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hiram Group – Estado Actualizado</title></head>
<body style="font-family:Arial,sans-serif;background:#F0F4FF;min-height:100vh;display:flex;align-items:center;justify-content:center;margin:0;">
<div style="background:white;border-radius:16px;padding:48px;max-width:480px;text-align:center;box-shadow:0 8px 32px rgba(0,0,0,0.1);">
  <div style="font-size:56px;margin-bottom:16px;">{icon}</div>
  <h2 style="color:{color};margin:0 0 8px;">Estado Actualizado</h2>
  <p style="color:#374151;font-size:16px;margin-bottom:4px;"><strong>{task.title}</strong></p>
  <p style="color:#6B7280;margin-bottom:24px;">Nuevo estado: <strong style="color:{color};">{label}</strong></p>
  <div style="background:#F8FAFC;border-radius:8px;padding:16px;font-size:13px;color:#6B7280;">
    ✅ El sistema ha registrado tu respuesta correctamente.<br>
    La administración ha sido notificada.
  </div>
  <p style="margin-top:24px;color:#9CA3AF;font-size:12px;">Hiram Group – Sistema Interno de Gestión</p>
</div>
</body></html>""")


# ── Task History ───────────────────────────────────────────────────────────────
@app.get("/api/tasks/{task_id}/history")
async def get_task_history(task_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    history = db.query(TaskHistory).filter(TaskHistory.task_id == task_id).order_by(TaskHistory.timestamp.desc()).all()
    return [{"action": h.action, "changed_by": h.changed_by,
             "timestamp": h.timestamp.strftime("%d/%m/%Y %H:%M") if h.timestamp else None,
             "notes": h.notes} for h in history]


# ── AI Suggestions Routes ──────────────────────────────────────────────────────
@app.get("/api/suggestions")
async def get_suggestions(
    status: Optional[str] = "pending_approval",
    department_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    q = db.query(AISuggestion)
    if status:
        q = q.filter(AISuggestion.status == status)
    if department_id:
        q = q.filter(AISuggestion.department_id == department_id)

    suggestions = q.order_by(AISuggestion.created_at.desc()).limit(100).all()
    return [{
        "id": s.id,
        "department_id": s.department_id,
        "department_name": s.department.name if s.department else "N/A",
        "brand_id": s.brand_id,
        "brand_name": s.brand.name if s.brand else "N/A",
        "title": s.title,
        "description": s.description,
        "priority": s.priority.value,
        "priority_label": PRIORITY_CONFIG[s.priority]["label"],
        "priority_color": PRIORITY_CONFIG[s.priority]["color"],
        "reasoning": s.reasoning,
        "status": s.status,
        "agent_name": s.agent_name,
        "created_at": s.created_at.strftime("%d/%m/%Y %H:%M") if s.created_at else None,
        "reviewed_by": s.reviewed_by,
        "reviewed_at": s.reviewed_at.strftime("%d/%m/%Y %H:%M") if s.reviewed_at else None,
    } for s in suggestions]


@app.post("/api/suggestions/generate")
async def generate_ai_suggestions(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    body = await request.json()
    department_id = body.get("department_id")
    brand_id = body.get("brand_id")
    count = body.get("count", 3)

    dept = db.query(Department).filter(Department.id == department_id).first()
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not dept or not brand:
        raise HTTPException(status_code=404, detail="Departamento o marca no encontrados")

    tasks = db.query(Task).filter(Task.department_id == department_id).order_by(Task.created_at.desc()).limit(10).all()
    tasks_data = [{"title": t.title, "status": t.status.value, "priority": t.priority.value,
                   "department": dept.name} for t in tasks]

    raw_suggestions = generate_suggestions(dept.name, brand.name, tasks_data, count=count)

    created = []
    priority_map = {"urgent": PriorityEnum.URGENT, "high": PriorityEnum.HIGH,
                    "medium": PriorityEnum.MEDIUM, "normal": PriorityEnum.NORMAL}

    for s in raw_suggestions:
        suggestion = AISuggestion(
            department_id=department_id,
            brand_id=brand_id,
            title=s.get("title", "Sugerencia"),
            description=s.get("description", ""),
            priority=priority_map.get(s.get("priority", "medium"), PriorityEnum.MEDIUM),
            reasoning=s.get("reasoning", ""),
            agent_name=f"Agente {dept.name}",
            status="pending_approval",
        )
        db.add(suggestion)
        db.flush()
        created.append({"id": suggestion.id, "title": suggestion.title})

    audit(db, f"Sugerencias IA generadas para {dept.name}", "suggestion", None, user.username,
          f"{len(created)} sugerencias generadas")
    db.commit()
    return {"created": len(created), "suggestions": created}


@app.post("/api/suggestions/{suggestion_id}/action")
async def action_on_suggestion(
    suggestion_id: int,
    action_data: SuggestionAction,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    suggestion = db.query(AISuggestion).filter(AISuggestion.id == suggestion_id).first()
    if not suggestion:
        raise HTTPException(status_code=404, detail="Sugerencia no encontrada")

    if action_data.action == "approve":
        deadline = calculate_deadline(suggestion.priority)
        task = Task(
            title=suggestion.title,
            description=suggestion.description,
            department_id=suggestion.department_id,
            brand_id=suggestion.brand_id,
            priority=suggestion.priority,
            status=StatusEnum.PENDING,
            deadline=deadline.replace(tzinfo=None) if hasattr(deadline, 'tzinfo') else deadline,
            created_by=f"IA (aprobada por {user.username})",
            ai_reasoning=suggestion.reasoning,
        )
        task.generate_token()
        db.add(task)
        db.flush()

        history = TaskHistory(task_id=task.id, action="Tarea creada desde sugerencia IA aprobada", changed_by=user.username)
        db.add(history)

        suggestion.status = "approved"
        suggestion.reviewed_by = user.username
        suggestion.reviewed_at = datetime.datetime.utcnow()

        dept = db.query(Department).filter(Department.id == suggestion.department_id).first()
        brand = db.query(Brand).filter(Brand.id == suggestion.brand_id).first()
        if dept and brand:
            task.email_sent = send_task_email(task, dept, brand)

        audit(db, f"Sugerencia IA #{suggestion_id} aprobada y convertida a tarea #{task.id}",
              "suggestion", suggestion_id, user.username)
        db.commit()
        return {"message": "Sugerencia aprobada y tarea creada", "task_id": task.id}

    elif action_data.action == "reject":
        suggestion.status = "rejected"
        suggestion.reviewed_by = user.username
        suggestion.reviewed_at = datetime.datetime.utcnow()
        audit(db, f"Sugerencia IA #{suggestion_id} rechazada", "suggestion", suggestion_id, user.username,
              action_data.notes)
        db.commit()
        return {"message": "Sugerencia rechazada"}

    raise HTTPException(status_code=400, detail="Acción inválida")


# ── AI Chat ────────────────────────────────────────────────────────────────────
@app.post("/api/chat")
async def ai_chat(msg: ChatMessage, user: User = Depends(get_current_user)):
    response = chat_with_agent(msg.department_name, msg.message, msg.history)
    return {"response": response, "agent": msg.department_name}


# ── Audit Log ──────────────────────────────────────────────────────────────────
@app.get("/api/audit")
async def get_audit_log(
    limit: int = 100,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return [{
        "id": l.id,
        "action": l.action,
        "entity_type": l.entity_type,
        "entity_id": l.entity_id,
        "performed_by": l.performed_by,
        "details": l.details,
        "timestamp": l.timestamp.strftime("%d/%m/%Y %H:%M:%S") if l.timestamp else None,
    } for l in logs]


# ── Dashboard Stats ────────────────────────────────────────────────────────────
@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    total = db.query(Task).count()
    pending = db.query(Task).filter(Task.status == StatusEnum.PENDING).count()
    in_progress = db.query(Task).filter(Task.status == StatusEnum.IN_PROGRESS).count()
    completed = db.query(Task).filter(Task.status == StatusEnum.COMPLETED).count()
    overdue = db.query(Task).filter(Task.status == StatusEnum.OVERDUE).count()
    ai_pending = db.query(AISuggestion).filter(AISuggestion.status == "pending_approval").count()

    by_brand = []
    brands = db.query(Brand).all()
    for b in brands:
        count = db.query(Task).filter(Task.brand_id == b.id).count()
        done = db.query(Task).filter(Task.brand_id == b.id, Task.status == StatusEnum.COMPLETED).count()
        by_brand.append({"name": b.name, "color": b.color, "emoji": b.logo_emoji,
                         "total": count, "completed": done})

    return {
        "total": total,
        "pending": pending,
        "in_progress": in_progress,
        "completed": completed,
        "overdue": overdue,
        "ai_pending": ai_pending,
        "by_brand": by_brand,
    }


# ── User Management ────────────────────────────────────────────────────────────
@app.get("/api/users")
async def get_users(db: Session = Depends(get_db), user: User = Depends(require_admin)):
    users = db.query(User).filter(User.is_active == True).all()
    return [{"id": u.id, "username": u.username, "email": u.email,
             "role": u.role, "department_id": u.department_id,
             "created_at": u.created_at.strftime("%d/%m/%Y") if u.created_at else None}
            for u in users]


@app.post("/api/users")
async def create_user(data: UserCreate, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="El usuario ya existe")
    new_user = User(
        username=data.username,
        email=data.email,
        password_hash=pwd_ctx.hash(data.password),
        role=data.role,
        department_id=data.department_id,
    )
    db.add(new_user)
    audit(db, f"Usuario creado: {data.username}", "user", None, user.username)
    db.commit()
    return {"message": "Usuario creado", "username": data.username}


# ── Serve uploaded files ─────────────────────────────────────────────────────────
@app.get("/api/uploads/{filename}")
async def serve_upload(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(file_path)


# ── Task Attachments ─────────────────────────────────────────────────────────────
@app.post("/api/tasks/{task_id}/attachments")
async def upload_attachment(
    task_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    form = await request.form()
    file = form.get("file")
    if not file:
        raise HTTPException(status_code=400, detail="No se envió ningún archivo")

    content = await file.read()
    ext = os.path.splitext(file.filename)[1] if "." in file.filename else ""
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = f"task_{task_id}_{ts}_{os.urandom(4).hex()}{ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)

    with open(file_path, "wb") as f:
        f.write(content)

    attachment = Attachment(
        task_id=task_id,
        filename=safe_name,
        original_name=file.filename or "sin_nombre",
        file_size=len(content),
        content_type=file.content_type or "application/octet-stream",
        uploaded_by=user.username,
    )
    db.add(attachment)
    history = TaskHistory(
        task_id=task_id,
        action=f"Archivo adjuntado: {file.filename or 'sin_nombre'}",
        changed_by=user.username,
    )
    db.add(history)
    audit(db, f"Archivo adjuntado a tarea #{task_id}", "task", task_id, user.username, file.filename)
    db.commit()
    db.refresh(attachment)

    return {
        "id": attachment.id,
        "filename": safe_name,
        "original_name": attachment.original_name,
        "file_size": len(content),
        "url": f"/api/uploads/{safe_name}",
    }


@app.get("/api/tasks/{task_id}/attachments")
async def list_attachments(
    task_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    attachments = db.query(Attachment).filter(Attachment.task_id == task_id).order_by(Attachment.created_at.desc()).all()
    return [{
        "id": a.id,
        "filename": a.filename,
        "original_name": a.original_name,
        "file_size": a.file_size,
        "content_type": a.content_type,
        "uploaded_by": a.uploaded_by,
        "created_at": a.created_at.strftime("%d/%m/%Y %H:%M") if a.created_at else None,
        "url": f"/api/uploads/{a.filename}",
    } for a in attachments]


@app.delete("/api/tasks/{task_id}/attachments/{attachment_id}")
async def delete_attachment(
    task_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    attachment = db.query(Attachment).filter(
        Attachment.id == attachment_id,
        Attachment.task_id == task_id
    ).first()
    if not attachment:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    file_path = os.path.join(UPLOAD_DIR, attachment.filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    db.delete(attachment)
    db.commit()
    return {"message": "Archivo eliminado"}


# ── Department (Area) Management ─────────────────────────────────────────────────
@app.get("/api/areas")
async def list_areas(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    depts = db.query(Department).all()
    return [{"id": d.id, "name": d.name, "email": d.email,
             "agent_role": d.agent_role, "icon": d.icon} for d in depts]


@app.post("/api/areas")
async def create_area(
    data: DepartmentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    existing = db.query(Department).filter(Department.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="El área ya existe")
    dept = Department(
        name=data.name,
        email=data.email,
        agent_role=data.agent_role,
        icon=data.icon or "briefcase",
    )
    db.add(dept)
    audit(db, f"Área creada: {data.name}", "department", None, user.username)
    db.commit()
    db.refresh(dept)
    return {"id": dept.id, "name": dept.name, "message": "Área creada correctamente"}


@app.put("/api/areas/{area_id}")
async def update_area(
    area_id: int,
    data: DepartmentUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    dept = db.query(Department).filter(Department.id == area_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Área no encontrada")
    if data.name is not None:
        dept.name = data.name
    if data.email is not None:
        dept.email = data.email
    if data.agent_role is not None:
        dept.agent_role = data.agent_role
    if data.icon is not None:
        dept.icon = data.icon
    audit(db, f"Área actualizada: {dept.name}", "department", area_id, user.username)
    db.commit()
    return {"message": "Área actualizada correctamente"}


@app.delete("/api/areas/{area_id}")
async def delete_area(
    area_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    dept = db.query(Department).filter(Department.id == area_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Área no encontrada")
    tasks_count = db.query(Task).filter(Task.department_id == area_id).count()
    if tasks_count > 0:
        raise HTTPException(status_code=400, detail=f"No se puede eliminar: {tasks_count} tareas asociadas")
    db.delete(dept)
    audit(db, f"Área eliminada: {dept.name}", "department", area_id, user.username)
    db.commit()
    return {"message": "Área eliminada correctamente"}


# ── Health Check ───────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {"status": "ok", "app": "Hiram Group AI Platform", "version": "1.0.0"}
