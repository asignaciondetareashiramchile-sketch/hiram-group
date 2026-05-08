"""Background scheduler: reminders + AI auto-suggestions."""
import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger


def check_and_send_reminders():
    from backend.database import SessionLocal
    from backend.models import Task, StatusEnum, AuditLog, TaskHistory
    from backend.email_service import send_reminder_email
    from backend.date_utils import is_overdue, now_chile

    db = SessionLocal()
    try:
        active_tasks = db.query(Task).filter(
            Task.status.in_([StatusEnum.PENDING, StatusEnum.IN_PROGRESS])
        ).all()

        for task in active_tasks:
            overdue = is_overdue(task.deadline)

            if overdue and task.status != StatusEnum.OVERDUE:
                task.status = StatusEnum.OVERDUE
                task.updated_at = datetime.datetime.utcnow()
                history = TaskHistory(
                    task_id=task.id,
                    action="Estado cambiado a Atrasado automáticamente",
                    changed_by="Sistema"
                )
                db.add(history)

            now = now_chile()
            last_reminder = task.last_reminder_sent
            should_remind = False

            if last_reminder is None:
                if task.created_at:
                    created_aware = task.created_at
                    if hasattr(created_aware, 'tzinfo') and created_aware.tzinfo is None:
                        import pytz
                        created_aware = pytz.UTC.localize(created_aware)
                    diff = now - created_aware.astimezone(pytz.UTC).replace(tzinfo=None)
                    if diff.total_seconds() > 3600:  # 1 hour after creation
                        should_remind = True
            else:
                last_aware = last_reminder
                if hasattr(last_aware, 'tzinfo') and last_aware.tzinfo is None:
                    import pytz
                    last_aware = pytz.UTC.localize(last_aware)
                diff = now - last_aware.astimezone(pytz.UTC).replace(tzinfo=None)
                if diff.total_seconds() > 86400:  # 24 hours
                    should_remind = True

            if should_remind and task.department and task.brand:
                sent = send_reminder_email(task, task.department, task.brand)
                if sent:
                    task.last_reminder_sent = datetime.datetime.utcnow()
                    log = AuditLog(
                        action=f"Recordatorio enviado para tarea #{task.id}",
                        entity_type="task",
                        entity_id=task.id,
                        performed_by="Sistema Scheduler",
                    )
                    db.add(log)

        db.commit()
        print(f"[SCHEDULER] Revisión de recordatorios completada: {len(active_tasks)} tareas activas")
    except Exception as e:
        print(f"[SCHEDULER ERROR] {e}")
        db.rollback()
    finally:
        db.close()


def run_ai_suggestions():
    """Auto-generate AI suggestions for all departments."""
    from backend.database import SessionLocal
    from backend.models import Task, Department, Brand, AISuggestion, AuditLog, StatusEnum
    from backend.ai_service import generate_suggestions
    from backend.config import ANTHROPIC_API_KEY

    if not ANTHROPIC_API_KEY:
        print("[SCHEDULER] AI suggestions skipped: no API key configured")
        return

    db = SessionLocal()
    try:
        departments = db.query(Department).all()
        brands = db.query(Brand).all()
        if not brands:
            return

        default_brand = brands[0]

        for dept in departments:
            # Check if there are already pending suggestions for this dept
            existing = db.query(AISuggestion).filter(
                AISuggestion.department_id == dept.id,
                AISuggestion.status == "pending_approval"
            ).count()

            if existing >= 3:
                continue

            tasks = db.query(Task).filter(
                Task.department_id == dept.id
            ).order_by(Task.created_at.desc()).limit(10).all()

            tasks_data = [
                {
                    "title": t.title,
                    "status": t.status.value,
                    "priority": t.priority.value,
                    "department": dept.name,
                }
                for t in tasks
            ]

            suggestions = generate_suggestions(dept.name, default_brand.name, tasks_data, count=2)

            for s in suggestions:
                from backend.models import PriorityEnum
                priority_map = {
                    "urgent": PriorityEnum.URGENT,
                    "high": PriorityEnum.HIGH,
                    "medium": PriorityEnum.MEDIUM,
                    "normal": PriorityEnum.NORMAL,
                }
                suggestion = AISuggestion(
                    department_id=dept.id,
                    brand_id=default_brand.id,
                    title=s.get("title", "Sugerencia sin título"),
                    description=s.get("description", ""),
                    priority=priority_map.get(s.get("priority", "medium"), PriorityEnum.MEDIUM),
                    reasoning=s.get("reasoning", ""),
                    agent_name=f"Agente {dept.name}",
                    status="pending_approval",
                )
                db.add(suggestion)

        db.commit()
        print(f"[SCHEDULER] AI suggestions generadas para {len(departments)} departamentos")
    except Exception as e:
        print(f"[SCHEDULER AI ERROR] {e}")
        db.rollback()
    finally:
        db.close()


def start_scheduler():
    scheduler = BackgroundScheduler()

    # Check reminders every hour
    scheduler.add_job(
        check_and_send_reminders,
        CronTrigger(minute=0),  # Every hour at :00
        id="reminders",
        name="Recordatorios de tareas",
        replace_existing=True,
    )

    # Generate AI suggestions twice daily
    scheduler.add_job(
        run_ai_suggestions,
        CronTrigger(hour="8,16", minute=0),  # 8am and 4pm
        id="ai_suggestions",
        name="Sugerencias IA diarias",
        replace_existing=True,
    )

    scheduler.start()
    print("[SCHEDULER] Iniciado: recordatorios cada hora, sugerencias IA a las 8:00 y 16:00")
    return scheduler
