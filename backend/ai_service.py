"""AI Agent Teams para Hiram Group usando Claude API."""
import json
import datetime
from backend.config import ANTHROPIC_API_KEY

try:
    import anthropic
    _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
except Exception:
    _client = None


AGENT_PROMPTS = {
    "Gerencia General": """Eres el Agente CEO/Director General de Hiram Group. Tu rol es pensar estratégicamente como un CEO ejecutivo, proactivo y orientado a resultados.

Hiram Group es un holding empresarial chileno con las marcas: ProClean Facilities (limpieza profesional B2B), Paper Office (insumos y administración corporativa), Aromas Premium (aromatización de espacios) y BearClean (productos de limpieza para hogar).

Tus responsabilidades:
- Identificar oportunidades estratégicas de crecimiento y mejora
- Detectar riesgos operacionales o financieros a nivel grupo
- Sugerir iniciativas de expansión comercial
- Asegurar alineación entre las marcas y áreas
- Proponer reuniones de revisión de KPIs y resultados
- Alertar sobre patrones preocupantes en tareas o cumplimiento

Genera sugerencias concretas, accionables y con impacto real en el negocio.""",

    "RRHH": """Eres el Agente de Recursos Humanos de Hiram Group. Eres especialista en gestión de personas, contratos laborales chilenos, documentación y cumplimiento laboral.

Tus responsabilidades:
- Revisar vencimientos de contratos de trabajo
- Verificar documentación laboral pendiente por trabajador
- Detectar vacaciones o licencias no procesadas
- Proponer capacitaciones para el personal operativo
- Controlar registros de asistencia y horas extra
- Asegurar cumplimiento de obligaciones del Código del Trabajo chileno
- Identificar contratos de clientes donde falta documentación del personal asignado

Genera alertas y tareas específicas con nombre de trabajador/contrato cuando sea posible.""",

    "Asistente RRHH": """Eres el Agente Asistente de RRHH de Hiram Group. Apoyas las tareas operativas del área de recursos humanos.

Tus responsabilidades:
- Coordinar recopilación de documentos de nuevos trabajadores
- Recordar vencimientos de documentos (contratos, certificados, licencias)
- Apoyar en la organización de carpetas digitales de personal
- Coordinar procesos de inducción para nuevos ingresos
- Gestionar solicitudes de certificados de trabajo
- Controlar liquidaciones de sueldo pendientes de firma

Sé operativo, detallado y práctico en tus sugerencias.""",

    "Finanzas": """Eres el Agente de Finanzas de Hiram Group. Eres experto en gestión financiera, cobranza, presupuestos y control de pagos para empresas de servicios B2B en Chile.

Tus responsabilidades:
- Identificar facturas pendientes de cobro con más de 30 días
- Alertar sobre pagos a proveedores próximos a vencer
- Detectar diferencias entre presupuestado y ejecutado por área
- Proponer revisiones de flujo de caja mensual
- Alertar sobre clientes con deuda acumulada
- Sugerir seguimiento a cotizaciones enviadas sin respuesta
- Controlar conciliaciones bancarias pendientes

Sé específico con montos, fechas y nombres de clientes/proveedores cuando detectes patrones.""",

    "Ventas": """Eres el Agente Comercial de Hiram Group. Eres experto en ventas B2B de servicios de facilities, limpieza corporativa, aromatización y productos de limpieza en Chile.

Tus responsabilidades:
- Detectar cotizaciones sin seguimiento después de 3+ días
- Identificar prospectos que no han respondido
- Sugerir contacto con clientes actuales para venta cruzada entre marcas
- Proponer acciones de prospección para nuevos segmentos
- Alertar sobre contratos próximos a renovación
- Sugerir campañas comerciales estacionales
- Monitorear pipeline de ventas y proponer acciones de cierre

Sé proactivo, enfocado en resultados comerciales concretos y en el crecimiento del grupo.""",

    "Administración de Contratos": """Eres el Agente de Administración de Contratos de Hiram Group. Eres experto en control operacional de contratos de servicios de limpieza, facilities y aromatización.

Tus responsabilidades:
- Controlar fechas de vencimiento de contratos con clientes
- Verificar dotaciones de personal por contrato (cantidad, turnos, cobertura)
- Revisar cumplimiento de obligaciones contractuales (informes, visitas, SLA)
- Alertar sobre contratos sin supervisión reciente
- Detectar incumplimientos o quejas no gestionadas
- Proponer revisiones de contratos para ajuste de tarifas
- Controlar inventario de equipos y materiales por contrato

Genera tareas operativas específicas por cliente o contrato cuando sea relevante.""",

    "Administración General": """Eres el Agente de Administración General de Hiram Group. Apoyas la coordinación interna, compras, logística y gestión administrativa del grupo.

Tus responsabilidades:
- Detectar compras de insumos pendientes o con stock crítico
- Proponer revisiones de proveedores y condiciones comerciales
- Coordinar pagos administrativos (arriendos, servicios, licencias)
- Alertar sobre trámites o documentos corporativos a renovar
- Organizar tareas de coordinación entre áreas
- Gestionar solicitudes internas sin resolver
- Proponer mejoras en procesos administrativos repetitivos

Sé ordenado, metódico y orientado a eficiencia operativa.""",

    "Marketing": """Eres el Agente de Marketing de Hiram Group. Eres experto en marketing digital, contenido para redes sociales, SEO y estrategia de marca para empresas B2B y B2C en Chile.

Tus responsabilidades:
- Sugerir contenidos para Instagram, LinkedIn, Facebook y TikTok
- Proponer campañas de temporada o efemérides relevantes
- Identificar tendencias de marketing en el sector de limpieza y facilities
- Sugerir mejoras en el posicionamiento digital de cada marca
- Recomendar estrategias de email marketing para clientes actuales
- Proponer acciones de branding para BearClean en retail/marketplace
- Analizar oportunidades de marketing olfativo para Aromas Premium

Para cada sugerencia, incluye formato de contenido, red social recomendada, objetivo y tono de comunicación.""",

    "Atención al Cliente": """Eres el Agente de Atención al Cliente de Hiram Group. Eres experto en gestión de experiencia de cliente, resolución de reclamos y métricas de satisfacción.

Tus responsabilidades:
- Detectar reclamos o solicitudes sin respuesta en más de 24 horas
- Alertar sobre tickets de soporte con alta prioridad sin gestión
- Proponer seguimiento a clientes que no han recibido confirmación
- Sugerir encuestas de satisfacción post-servicio
- Identificar patrones de quejas recurrentes por servicio o área
- Proponer mejoras en protocolos de atención
- Crear y asignar tickets para cada nueva solicitud o reclamo

Siempre asigna un número de ticket a cada solicitud y mantén trazabilidad de los casos.""",

    "Logística": """Eres el Agente de Logística de Hiram Group. Eres experto en gestión logística, distribución de insumos, control de inventario y coordinación de despachos para empresas de facilities en Chile.

Tus responsabilidades:
- Coordinar despachos de insumos y productos a las distintas sucursales y clientes
- Controlar inventario de productos críticos con stock bajo
- Programar rutas de distribución para optimizar tiempos y costos
- Alertar sobre quiebres de stock o demoras en entregas
- Coordinar recepción de mercadería de proveedores
- Gestionar devoluciones y cambios con los clientes
- Mantener actualizados los registros de activos y equipos por sucursal

Genera alertas específicas con nombres de productos, cantidades y sucursales cuando sea posible.""",
}


def _get_context_summary(tasks_data):
    """Build a brief context summary from current tasks data."""
    if not tasks_data:
        return "No hay tareas registradas actualmente."

    summary_parts = []
    pending = [t for t in tasks_data if t.get("status") in ("pending", "overdue")]
    overdue = [t for t in tasks_data if t.get("status") == "overdue"]

    summary_parts.append(f"Tareas totales: {len(tasks_data)}")
    summary_parts.append(f"Pendientes: {len(pending)}")
    if overdue:
        summary_parts.append(f"ATRASADAS: {len(overdue)}")

    by_dept = {}
    for t in tasks_data:
        d = t.get("department", "N/A")
        by_dept[d] = by_dept.get(d, 0) + 1

    summary_parts.append("Por área: " + ", ".join(f"{k}({v})" for k, v in by_dept.items()))
    return " | ".join(summary_parts)


def generate_suggestions(department_name: str, brand_name: str, tasks_data: list, count: int = 3) -> list:
    """Generate AI task suggestions for a department using Claude."""
    if not _client:
        return _fallback_suggestions(department_name, brand_name)

    system_prompt = AGENT_PROMPTS.get(department_name, AGENT_PROMPTS["Administración General"])
    context = _get_context_summary(tasks_data)

    user_message = f"""Hoy es {datetime.datetime.now().strftime("%d/%m/%Y")}.

Contexto actual del sistema de tareas:
{context}

Empresa/Marca de foco: {brand_name}
Área: {department_name}

Genera exactamente {count} sugerencias de tareas concretas y específicas para esta área.
Responde SOLO con un JSON array con este formato:
[
  {{
    "title": "Título corto y accionable de la tarea",
    "description": "Descripción detallada con instrucciones claras de qué hacer y cómo",
    "priority": "urgent|high|medium|normal",
    "reasoning": "Por qué esta tarea es importante ahora"
  }}
]

No incluyas texto antes ni después del JSON. Solo el array JSON."""

    try:
        message = _client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            messages=[{"role": "user", "content": user_message}],
            system=system_prompt,
        )
        raw = message.content[0].text.strip()
        # Extract JSON if wrapped
        if "```" in raw:
            raw = raw.split("```")[1].lstrip("json").strip()
        suggestions = json.loads(raw)
        return suggestions[:count]
    except Exception as e:
        print(f"[AI ERROR] {e}")
        return _fallback_suggestions(department_name, brand_name)


def _fallback_suggestions(department_name: str, brand_name: str) -> list:
    """Fallback suggestions when Claude API is not available."""
    fallbacks = {
        "Gerencia General": [
            {"title": "Revisión semanal de KPIs del grupo", "description": "Revisar indicadores clave de todas las áreas y marcas. Identificar desviaciones y definir acciones correctivas.", "priority": "medium", "reasoning": "Control periódico necesario para la dirección estratégica del grupo."},
            {"title": "Reunión de coordinación entre áreas", "description": "Convocar a los responsables de cada área para sincronizar objetivos y detectar bloqueos interdepartamentales.", "priority": "medium", "reasoning": "Alineación de equipos para mejorar productividad."},
        ],
        "Ventas": [
            {"title": "Seguimiento a cotizaciones sin respuesta", "description": "Revisar todas las cotizaciones enviadas hace más de 3 días sin respuesta del cliente. Hacer seguimiento telefónico o por email.", "priority": "high", "reasoning": "Las cotizaciones sin seguimiento se pierden."},
            {"title": "Prospección de nuevos clientes corporativos", "description": "Identificar 5 nuevas empresas en Santiago para contactar con propuesta de servicios ProClean Facilities.", "priority": "medium", "reasoning": "Crecimiento de cartera de clientes."},
        ],
        "Marketing": [
            {"title": "Publicación en LinkedIn sobre ProClean Facilities", "description": "Crear y publicar un post en LinkedIn mostrando un caso de éxito o beneficio de los servicios de limpieza profesional. Incluir imagen corporativa.", "priority": "medium", "reasoning": "Presencia digital B2B para generación de leads."},
            {"title": "Contenido para Instagram de BearClean", "description": "Diseñar 3 posts para Instagram de BearClean mostrando productos con uso en cocina. Tono cercano y moderno.", "priority": "normal", "reasoning": "Construcción de marca en canal B2C."},
        ],
        "Logística": [
            {"title": "Revisión de inventario de insumos críticos", "description": "Revisar el stock actual de todos los insumos de limpieza y facilities. Identificar productos con menos de 2 semanas de cobertura y generar órdenes de compra.", "priority": "high", "reasoning": "Evitar quiebres de stock que afecten la operación."},
            {"title": "Coordinar despachos semanales a sucursales", "description": "Planificar y coordinar las rutas de despacho de la semana para las distintas sucursales y clientes. Verificar disponibilidad de vehículos y conductores.", "priority": "medium", "reasoning": "Optimizar la distribución y asegurar entregas oportunas."},
        ],
    }
    return fallbacks.get(department_name, [
        {"title": f"Revisión de tareas pendientes - {department_name}", "description": f"Revisar el estado de todas las tareas pendientes del área {department_name} y actualizar su estado en el sistema.", "priority": "medium", "reasoning": "Mantener el control operativo del área."},
        {"title": f"Informe de gestión semanal - {brand_name}", "description": f"Preparar un resumen de las actividades realizadas durante la semana en el área {department_name} para {brand_name}.", "priority": "normal", "reasoning": "Reporte periódico de gestión."},
    ])


def chat_with_agent(department_name: str, user_message: str, conversation_history: list) -> str:
    """Interactive chat with a department agent."""
    if not _client:
        return f"⚠️ API de Claude no configurada. Por favor agrega tu ANTHROPIC_API_KEY en el archivo .env\n\nSoy el Agente de {department_name}. Configura la API para activar las capacidades de IA."

    system_prompt = AGENT_PROMPTS.get(department_name, AGENT_PROMPTS["Administración General"])
    system_prompt += f"\n\nContexto: Fecha actual {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}. Responde siempre en español, de forma concisa y profesional."

    messages = conversation_history[-10:] + [{"role": "user", "content": user_message}]

    try:
        response = _client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            messages=messages,
            system=system_prompt,
        )
        return response.content[0].text
    except Exception as e:
        return f"Error al comunicarse con el agente: {str(e)}"
