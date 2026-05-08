import asyncio
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from backend.config import (SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD,
                            SMTP_FROM, SMTP_USE_TLS, BASE_URL, ENVIRONMENT)
from backend.models import PRIORITY_CONFIG, STATUS_LABELS


def _priority_badge(priority):
    cfg = PRIORITY_CONFIG[priority]
    return f'<span style="background:{cfg["color"]};color:white;padding:4px 12px;border-radius:12px;font-weight:bold;font-size:13px;">{cfg["label"]}</span>'


def _build_task_email(task, dept_name, brand_name, subject_prefix="Nueva Tarea"):
    token = task.action_token
    in_progress_url = f"{BASE_URL}/api/tasks/action/{token}/in_progress"
    completed_url = f"{BASE_URL}/api/tasks/action/{token}/completed"
    review_url = f"{BASE_URL}/api/tasks/action/{token}/needs_review"
    priority_cfg = PRIORITY_CONFIG[task.priority]

    deadline_str = task.deadline.strftime("%d/%m/%Y a las %H:%M") if task.deadline else "Sin fecha límite"

    ticket_html = ""
    if task.ticket_number:
        ticket_html = f'<p style="font-size:13px;color:#666;">🎫 Ticket: <strong>{task.ticket_number}</strong></p>'

    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;background:#f4f6f9;margin:0;padding:0;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f9;padding:30px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:white;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.1);">

  <!-- HEADER -->
  <tr><td style="background:linear-gradient(135deg,#1E3A5F 0%,#2563EB 100%);padding:28px 32px;">
    <table width="100%"><tr>
      <td><h1 style="color:white;margin:0;font-size:22px;font-weight:bold;">🏢 Hiram Chile</h1>
          <p style="color:#93C5FD;margin:4px 0 0;font-size:14px;">ProClean Facilities – Sistema de Gestión</p></td>
      <td align="right"><span style="background:rgba(255,255,255,0.15);color:white;padding:6px 14px;border-radius:20px;font-size:12px;font-weight:bold;">{dept_name}</span></td>
    </tr></table>
  </td></tr>

  <!-- BODY -->
  <tr><td style="padding:32px;">
    <h2 style="color:#1E3A5F;margin:0 0 8px;font-size:20px;">{subject_prefix}</h2>
    <h3 style="color:#2563EB;margin:0 0 24px;font-size:18px;">{task.title}</h3>

    <table width="100%" style="background:#F0F4FF;border-radius:8px;padding:16px;margin-bottom:20px;" cellpadding="8">
      <tr><td width="50%"><strong style="color:#6B7280;font-size:12px;text-transform:uppercase;">Área</strong><br><span style="color:#1E3A5F;font-weight:bold;">{dept_name}</span></td>
          <td width="50%"><strong style="color:#6B7280;font-size:12px;text-transform:uppercase;">Empresa/Marca</strong><br><span style="color:#1E3A5F;font-weight:bold;">{brand_name}</span></td></tr>
      <tr><td><strong style="color:#6B7280;font-size:12px;text-transform:uppercase;">Prioridad</strong><br>{_priority_badge(task.priority)}</td>
          <td><strong style="color:#6B7280;font-size:12px;text-transform:uppercase;">Fecha Límite</strong><br><span style="color:#DC2626;font-weight:bold;">⏰ {deadline_str}</span></td></tr>
    </table>

    {ticket_html}

    <div style="background:#FAFAFA;border-left:4px solid #2563EB;padding:16px;border-radius:0 8px 8px 0;margin-bottom:28px;">
      <strong style="color:#374151;font-size:13px;text-transform:uppercase;">Descripción / Instrucciones:</strong>
      <p style="color:#374151;margin:8px 0 0;line-height:1.6;">{task.description or 'Sin descripción adicional.'}</p>
    </div>

    <p style="color:#374151;font-weight:bold;margin-bottom:12px;">Actualiza el estado de esta tarea:</p>
    <table><tr>
      <td style="padding-right:10px;"><a href="{in_progress_url}" style="background:#2563EB;color:white;padding:12px 20px;border-radius:8px;text-decoration:none;font-weight:bold;font-size:14px;display:inline-block;">⚙️ Estoy gestionándolo</a></td>
      <td style="padding-right:10px;"><a href="{completed_url}" style="background:#16A34A;color:white;padding:12px 20px;border-radius:8px;text-decoration:none;font-weight:bold;font-size:14px;display:inline-block;">✅ Realizado</a></td>
      <td><a href="{review_url}" style="background:#D97706;color:white;padding:12px 20px;border-radius:8px;text-decoration:none;font-weight:bold;font-size:14px;display:inline-block;">🔍 Requiere revisión</a></td>
    </tr></table>
  </td></tr>

  <!-- FOOTER -->
  <tr><td style="background:#F8FAFC;padding:16px 32px;border-top:1px solid #E5E7EB;">
    <p style="color:#9CA3AF;font-size:12px;margin:0;text-align:center;">
      Hiram Group – Sistema Interno de Gestión | Este correo fue generado automáticamente.
    </p>
  </td></tr>
</table></td></tr></table>
</body></html>"""

    return html


def _build_reminder_email(task, dept_name, brand_name, overdue=False):
    subject_prefix = "⚠️ TAREA ATRASADA" if overdue else "🔔 Recordatorio"
    from backend.date_utils import format_deadline, now_chile, is_overdue
    deadline_str = format_deadline(task.deadline)
    status_label = STATUS_LABELS.get(task.status, task.status)

    if overdue:
        time_info = f'<p style="color:#DC2626;font-weight:bold;font-size:15px;">⚠️ Esta tarea está ATRASADA desde {deadline_str}</p>'
    elif task.deadline:
        now = now_chile()
        dl = task.deadline
        if hasattr(dl, 'tzinfo') and dl.tzinfo is None:
            import pytz
            dl = pytz.timezone("America/Santiago").localize(dl)
        diff = dl - now
        hours_left = diff.total_seconds() / 3600
        if hours_left < 1:
            time_info = f'<p style="color:#DC2626;font-weight:bold;">⏰ Menos de 1 hora para el vencimiento</p>'
        elif hours_left < 24:
            time_info = f'<p style="color:#D97706;font-weight:bold;">⏰ Vence en {int(hours_left)} horas ({deadline_str})</p>'
        else:
            days_left = int(hours_left / 24)
            time_info = f'<p style="color:#2563EB;font-weight:bold;">⏰ Vence en {days_left} días ({deadline_str})</p>'
    else:
        time_info = ""

    token = task.action_token
    in_progress_url = f"{BASE_URL}/api/tasks/action/{token}/in_progress"
    completed_url = f"{BASE_URL}/api/tasks/action/{token}/completed"
    priority_cfg = PRIORITY_CONFIG[task.priority]

    header_color = "#DC2626" if overdue else "#D97706"

    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;background:#f4f6f9;margin:0;padding:0;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f9;padding:30px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:white;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.1);">
  <tr><td style="background:linear-gradient(135deg,{header_color} 0%,#7F1D1D 100%);padding:24px 32px;">
    <h1 style="color:white;margin:0;font-size:20px;">🏢 Hiram Chile – {subject_prefix}</h1>
    <p style="color:#FCA5A5;margin:4px 0 0;font-size:13px;">Sistema Interno de Gestión</p>
  </td></tr>
  <tr><td style="padding:28px 32px;">
    <h3 style="color:#1E3A5F;margin:0 0 6px;">{task.title}</h3>
    <p style="color:#6B7280;margin:0 0 16px;font-size:13px;">Área: <strong>{dept_name}</strong> | Empresa: <strong>{brand_name}</strong> | Estado actual: <strong>{status_label}</strong></p>
    {_priority_badge(task.priority)}
    <br><br>
    {time_info}
    <p style="color:#374151;">Esta tarea sigue pendiente de completarse. Por favor actualiza su estado:</p>
    <table><tr>
      <td style="padding-right:10px;"><a href="{in_progress_url}" style="background:#2563EB;color:white;padding:12px 20px;border-radius:8px;text-decoration:none;font-weight:bold;font-size:14px;display:inline-block;">⚙️ Estoy gestionándolo</a></td>
      <td><a href="{completed_url}" style="background:#16A34A;color:white;padding:12px 20px;border-radius:8px;text-decoration:none;font-weight:bold;font-size:14px;display:inline-block;">✅ Realizado</a></td>
    </tr></table>
  </td></tr>
  <tr><td style="background:#F8FAFC;padding:12px 32px;border-top:1px solid #E5E7EB;">
    <p style="color:#9CA3AF;font-size:11px;margin:0;text-align:center;">Hiram Group – Recordatorio automático del sistema</p>
  </td></tr>
</table></td></tr></table>
</body></html>"""
    return html


def send_email_sync(to_email: str, subject: str, html_content: str):
    """Synchronous email send - used as fallback."""
    if not SMTP_USERNAME or ENVIRONMENT == "development":
        print(f"[EMAIL SIMULADO] Para: {to_email} | Asunto: {subject}")
        return True
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_FROM
        msg["To"] = to_email
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            if SMTP_USE_TLS:
                server.starttls(context=context)
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False


def send_task_email(task, department, brand):
    subject = f"[{PRIORITY_CONFIG[task.priority]['label'].upper()}] Nueva Tarea: {task.title}"
    html = _build_task_email(task, department.name, brand.name)
    return send_email_sync(department.email, subject, html)


def send_reminder_email(task, department, brand):
    from backend.date_utils import is_overdue
    overdue = is_overdue(task.deadline)
    prefix = "⚠️ ATRASADA" if overdue else "🔔 Recordatorio"
    subject = f"[{prefix}] {task.title} – {department.name}"
    html = _build_reminder_email(task, department.name, brand.name, overdue=overdue)
    return send_email_sync(department.email, subject, html)
