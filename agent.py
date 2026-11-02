"""
Agente conversacional inteligente para gestión rápida del horario.

Interpreta comandos en lenguaje natural (español) y ejecuta acciones:
- Agregar/crear bloques
- Eliminar bloques  
- Modificar bloques
- Configurar preferencias
- Generar horario
- Descargar PDF
- Consultar horario
"""

import re
from typing import Optional


# ── Time parsing ──────────────────────────────────────────────

def _parse_time(text: str) -> Optional[str]:
    """
    Parse a time expression from Spanish text into HH:MM format.
    Handles: "3pm", "3 pm", "15:30", "3 de la tarde", "6 de la mañana",
             "las 10", "mediodia", "medianoche", etc.
    """
    text = text.strip().lower()

    # Direct HH:MM
    m = re.match(r"^(\d{1,2}):(\d{2})$", text)
    if m:
        h, mi = int(m.group(1)), int(m.group(2))
        if 0 <= h <= 23 and 0 <= mi <= 59:
            return f"{h:02d}:{mi:02d}"

    # "3pm", "3:30pm", "3 pm", "3:30 pm"
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)$", text)
    if m:
        h, mi = int(m.group(1)), int(m.group(2) or 0)
        period = m.group(3)
        if "p" in period and h != 12:
            h += 12
        elif "a" in period and h == 12:
            h = 0
        return f"{h:02d}:{mi:02d}"

    # Just a number (interpret as hour)
    m = re.match(r"^(\d{1,2})$", text)
    if m:
        h = int(m.group(1))
        if 0 <= h <= 23:
            return f"{h:02d}:00"

    # Keywords
    keywords = {
        "mediodia": "12:00", "mediodía": "12:00", "medio dia": "12:00",
        "medianoche": "00:00", "media noche": "00:00",
    }
    if text in keywords:
        return keywords[text]

    return None


def _extract_time_from_text(text: str) -> Optional[str]:
    """Extract a time from a longer text string."""
    # "a las 3pm", "a las 15:30", "a las 3 de la tarde"
    m = re.search(r"a\s+las?\s+(\d{1,2}(?::\d{2})?)\s*(am|pm|a\.m\.|p\.m\.)?(?:\s+de\s+la\s+(mañana|tarde|noche))?", text)
    if m:
        h_str = m.group(1)
        period = m.group(2) or ""
        part_of_day = m.group(3) or ""
        
        parts = h_str.split(":")
        h = int(parts[0])
        mi = int(parts[1]) if len(parts) > 1 else 0
        
        if "pm" in period or "p.m" in period:
            if h != 12: h += 12
        elif "am" in period or "a.m" in period:
            if h == 12: h = 0
        elif part_of_day == "tarde" and h < 12:
            h += 12
        elif part_of_day == "noche" and h < 12:
            h += 12
        elif part_of_day == "mañana" and h == 12:
            h = 0
        
        return f"{h:02d}:{mi:02d}"

    # Standalone time patterns: "10:30", "3pm"
    m = re.search(r"(\d{1,2}):(\d{2})", text)
    if m:
        h, mi = int(m.group(1)), int(m.group(2))
        if 0 <= h <= 23 and 0 <= mi <= 59:
            return f"{h:02d}:{mi:02d}"

    m = re.search(r"(\d{1,2})\s*(am|pm)", text)
    if m:
        h = int(m.group(1))
        if "pm" in m.group(2) and h != 12:
            h += 12
        elif "am" in m.group(2) and h == 12:
            h = 0
        return f"{h:02d}:00"

    return None


def _extract_time_range(text: str) -> tuple[Optional[str], Optional[str]]:
    """Extract a time range like 'de 10 a 12', 'de 3pm a 5pm', '10:00-12:00'."""
    # "de X a Y"
    m = re.search(
        r"de\s+(?:las?\s+)?(\d{1,2}(?::\d{2})?)\s*(am|pm)?"
        r"\s+a\s+(?:las?\s+)?(\d{1,2}(?::\d{2})?)\s*(am|pm)?",
        text,
    )
    if m:
        start_str = m.group(1) + (" " + m.group(2) if m.group(2) else "")
        end_str = m.group(3) + (" " + m.group(4) if m.group(4) else "")
        start = _parse_time(start_str)
        end = _parse_time(end_str)
        
        # If end hour is less than start and no AM/PM specified, assume PM
        if start and end:
            sh = int(start.split(":")[0])
            eh = int(end.split(":")[0])
            if eh < sh and not m.group(4):
                eh += 12
                end = f"{eh:02d}:{end.split(':')[1]}"
        
        return start, end

    # "X-Y" or "X - Y"
    m = re.search(r"(\d{1,2}(?::\d{2})?)\s*-\s*(\d{1,2}(?::\d{2})?)", text)
    if m:
        return _parse_time(m.group(1)), _parse_time(m.group(2))

    return None, None


def _extract_duration(text: str) -> Optional[int]:
    """Extract duration in minutes from text. E.g., 'por 2 horas', 'durante 30 minutos'."""
    # Hours
    m = re.search(r"(?:por|durante)\s+(\d+(?:\.\d+)?)\s*(?:horas?|hrs?|h)", text)
    if m:
        return int(float(m.group(1)) * 60)

    # Minutes
    m = re.search(r"(?:por|durante)\s+(\d+)\s*(?:minutos?|mins?|m(?:in)?)", text)
    if m:
        return int(m.group(1))

    # "hora y media"
    if re.search(r"(?:por|durante)\s+(?:una?\s+)?hora\s+y\s+media", text):
        return 90

    # "media hora"
    if re.search(r"(?:por|durante)\s+media\s+hora", text):
        return 30

    return None


# ── Category inference ────────────────────────────────────────

CATEGORY_KEYWORDS = {
    "work": [
        "trabajo", "trabajar", "oficina", "reunión", "reunion", "meeting",
        "junta", "llamada", "presentación", "presentacion", "proyecto",
        "cliente", "correos", "emails", "informe",
    ],
    "meal": [
        "desayuno", "desayunar", "almuerzo", "almorzar", "comida", "comer",
        "cena", "cenar", "snack", "merienda", "brunch", "café", "cafe",
    ],
    "exercise": [
        "ejercicio", "gym", "gimnasio", "correr", "trotar", "yoga", "nadar",
        "natación", "natacion", "bici", "ciclismo", "caminar", "caminata",
        "deporte", "entrenar", "entrenamiento", "crossfit", "pesas",
        "futbol", "fútbol", "basket", "tenis", "cardio", "stretching",
    ],
    "study": [
        "estudiar", "estudio", "leer", "lectura", "curso", "clase",
        "tarea", "deberes", "investigar", "aprender", "tutorial",
        "práctica", "practica", "examen", "libro",
    ],
    "personal": [
        "personal", "médico", "medico", "doctor", "cita", "dentista",
        "compras", "supermercado", "banco", "trámite", "tramite",
        "mandado", "diligencia", "recoger",
    ],
    "routine": [
        "rutina", "ducha", "baño", "bañar", "preparar", "higiene",
        "arreglar", "vestir", "despertar",
    ],
    "sleep": [
        "dormir", "siesta", "descansar", "descanso", "nap",
    ],
    "free": [
        "libre", "ocio", "relax", "netflix", "series", "película",
        "pelicula", "jugar", "juego", "gaming", "paseo", "pasear",
        "amigos", "salir", "hobby", "música", "musica", "guitarra",
        "pintar", "dibujar",
    ],
}


def _infer_category(text: str) -> str:
    """Infer the category of an activity from text."""
    text_lower = text.lower()
    scores: dict[str, int] = {}

    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                scores[cat] = scores.get(cat, 0) + 1

    if scores:
        return max(scores, key=scores.get)
    return "personal"


CATEGORY_EMOJI = {
    "work": "💼", "meal": "🍽️", "exercise": "💪", "study": "📚",
    "personal": "👤", "routine": "🔄", "sleep": "🌙", "free": "🎮",
}

CATEGORY_LABEL = {
    "work": "Trabajo", "meal": "Comida", "exercise": "Ejercicio",
    "study": "Estudio", "personal": "Personal", "routine": "Rutina",
    "sleep": "Dormir", "free": "Tiempo libre",
}


# ── Main agent ────────────────────────────────────────────────

def _add_minutes(time_str: str, minutes: int) -> str:
    """Add minutes to a time string."""
    h, m = map(int, time_str.split(":"))
    total = h * 60 + m + minutes
    total = total % 1440
    return f"{total // 60:02d}:{total % 60:02d}"


def process_message(
    message: str,
    current_blocks: list[dict],
    current_date: str,
) -> dict:
    """
    Process a natural language message and return an action + response.
    
    Returns dict with:
        - action: str ("add_block", "delete_block", "update_block", 
                        "generate", "download_pdf", "update_preferences",
                        "none")
        - data: dict (action-specific payload)
        - response: str (human-readable response to show in chat)
    """
    msg = message.strip()
    msg_lower = msg.lower()

    # ── Generate schedule ────────────────────────────────
    generate_patterns = [
        r"(?:genera|generar|crea|crear|planifica|planificar|arma|armar).*(?:horario|plan|día|dia|agenda|schedule)",
        r"(?:organiza|organizar).*(?:día|dia|mi tiempo)",
        r"planifica(?:me)?",
    ]
    for pat in generate_patterns:
        if re.search(pat, msg_lower):
            return {
                "action": "generate",
                "data": {},
                "response": "✨ ¡Horario generado! He creado tu planificación de 24 horas basada en tus preferencias.",
            }

    # ── Download PDF ─────────────────────────────────────
    if re.search(r"(?:descarga|descargar|exporta|exportar|baja|bajar|guardar|imprime|imprimir).*(?:pdf|horario|agenda)", msg_lower):
        return {
            "action": "download_pdf",
            "data": {},
            "response": "📥 Descargando tu horario en PDF...",
        }

    # ── Query schedule ───────────────────────────────────
    query_match = re.search(r"(?:qué|que|cual|cuál)\s+(?:tengo|hay|tiene|toca)(?:\s+(?:a|para)\s+las?\s+)?(\d{1,2}(?::\d{2})?)?", msg_lower)
    if query_match:
        query_time = query_match.group(1)
        if query_time:
            qt = _parse_time(query_time)
            if qt:
                qt_min = int(qt.split(":")[0]) * 60 + int(qt.split(":")[1])
                for block in current_blocks:
                    bs = int(block["start_time"].split(":")[0]) * 60 + int(block["start_time"].split(":")[1])
                    be = int(block["end_time"].split(":")[0]) * 60 + int(block["end_time"].split(":")[1])
                    if be <= bs:
                        be += 1440
                    if bs <= qt_min < be:
                        return {
                            "action": "none",
                            "data": {},
                            "response": f"🕐 A las {qt} tienes: **{block['title']}** ({block['start_time']} - {block['end_time']})",
                        }
                return {
                    "action": "none",
                    "data": {},
                    "response": f"🕐 No tienes nada programado a las {qt}.",
                }
        else:
            # Show full summary
            if not current_blocks:
                return {
                    "action": "none",
                    "data": {},
                    "response": "📭 No tienes un horario generado para hoy. Di *genera mi horario* para crear uno.",
                }
            summary = "📋 **Tu horario de hoy:**\n"
            for b in current_blocks:
                if b["category"] != "sleep":
                    emoji = CATEGORY_EMOJI.get(b["category"], "📌")
                    summary += f"\n• {b['start_time']}-{b['end_time']} — {b['title']}"
            return {"action": "none", "data": {}, "response": summary}

    if re.search(r"(?:muestra|mostrar|ver|dame|dime).*(?:horario|agenda|plan|día|dia)", msg_lower):
        if not current_blocks:
            return {
                "action": "none",
                "data": {},
                "response": "📭 No tienes un horario para hoy. Di *genera mi horario* para crear uno.",
            }
        summary = "📋 **Tu horario de hoy:**\n"
        for b in current_blocks:
            if b["category"] != "sleep":
                summary += f"\n• {b['start_time']}-{b['end_time']} — {b['title']}"
        return {"action": "none", "data": {}, "response": summary}

    # ── Delete block ─────────────────────────────────────
    delete_match = re.search(
        r"(?:elimina|eliminar|quita|quitar|borra|borrar|remueve|remover|cancela|cancelar|saca|sacar)\s+(?:el\s+|la\s+|los\s+|las\s+)?(?:bloque\s+(?:de\s+)?)?(.+)",
        msg_lower,
    )
    if delete_match:
        target = delete_match.group(1).strip().rstrip(".")
        # Find matching block
        best_match = None
        best_score = 0
        for block in current_blocks:
            title_lower = block["title"].lower()
            cat_label = CATEGORY_LABEL.get(block["category"], "").lower()
            score = 0
            for word in target.split():
                if word in title_lower:
                    score += 2
                if word in cat_label:
                    score += 1
                if word in block.get("description", "").lower():
                    score += 1
            if score > best_score:
                best_score = score
                best_match = block

        if best_match and best_score > 0:
            return {
                "action": "delete_block",
                "data": {"block_id": best_match["id"]},
                "response": f"🗑️ Eliminado: **{best_match['title']}** ({best_match['start_time']} - {best_match['end_time']})",
            }
        else:
            return {
                "action": "none",
                "data": {},
                "response": f"❌ No encontré un bloque que coincida con \"{target}\". Revisa tu horario actual.",
            }

    # ── Modify/Move block ────────────────────────────────
    modify_match = re.search(
        r"(?:cambia|cambiar|mueve|mover|modifica|modificar|pon|poner|actualiza|actualizar)\s+(?:el\s+|la\s+)?(.+?)(?:\s+(?:a\s+las?|para\s+las?|de)\s+.+)",
        msg_lower,
    )
    if modify_match:
        target = modify_match.group(1).strip()
        new_time = _extract_time_from_text(msg_lower)
        new_start, new_end = _extract_time_range(msg_lower)
        duration = _extract_duration(msg_lower)

        # Find the block
        best_match = None
        best_score = 0
        for block in current_blocks:
            title_lower = block["title"].lower()
            score = sum(2 for w in target.split() if w in title_lower)
            if score > best_score:
                best_score = score
                best_match = block

        if best_match and best_score > 0:
            updates = {}
            if new_start and new_end:
                updates["start_time"] = new_start
                updates["end_time"] = new_end
            elif new_time:
                updates["start_time"] = new_time
                # Keep same duration
                old_sh, old_sm = map(int, best_match["start_time"].split(":"))
                old_eh, old_em = map(int, best_match["end_time"].split(":"))
                dur = (old_eh * 60 + old_em) - (old_sh * 60 + old_sm)
                if dur <= 0:
                    dur += 1440
                updates["end_time"] = _add_minutes(new_time, dur)

            if duration and "start_time" in updates:
                updates["end_time"] = _add_minutes(updates["start_time"], duration)

            if updates:
                return {
                    "action": "update_block",
                    "data": {"block_id": best_match["id"], "updates": updates},
                    "response": f"✏️ Actualizado: **{best_match['title']}** → {updates.get('start_time', best_match['start_time'])} - {updates.get('end_time', best_match['end_time'])}",
                }

    # ── Add block ────────────────────────────────────────
    add_match = re.search(
        r"(?:agrega|agregar|añade|añadir|crea|crear|pon|poner|programa|programar|agendar|agenda|mete|meter|tengo)\s+(?:un\s+|una\s+|el\s+|la\s+)?(?:bloque\s+(?:de\s+)?)?(.+)",
        msg_lower,
    )
    if not add_match:
        # Try pattern: "activity + de X a Y" or "activity + a las X"
        add_match = re.search(
            r"^(.+?)\s+(?:de\s+(?:las?\s+)?\d|a\s+las?\s+\d)",
            msg_lower,
        )

    if add_match:
        activity_text = add_match.group(1).strip()
        
        # Extract time range
        start_time, end_time = _extract_time_range(msg_lower)
        
        # If no range, try single time + duration
        if not start_time:
            start_time = _extract_time_from_text(msg_lower)
        
        duration = _extract_duration(msg_lower)
        
        if start_time and not end_time:
            if duration:
                end_time = _add_minutes(start_time, duration)
            else:
                end_time = _add_minutes(start_time, 60)  # default 1h
        
        if not start_time:
            return {
                "action": "none",
                "data": {},
                "response": f"⏰ ¿A qué hora quieres programar \"{activity_text}\"? Ejemplo: *agrega {activity_text} de 10 a 12*",
            }

        # Clean activity name from time-related words
        clean_name = re.sub(
            r"\s*(?:de\s+(?:las?\s+)?\d.*|a\s+(?:las?\s+)?\d.*|por\s+\d.*|durante\s+\d.*|\b\d{1,2}:\d{2}\b.*|\b\d{1,2}\s*(?:am|pm)\b.*)",
            "", activity_text, flags=re.IGNORECASE
        ).strip().rstrip(",. ")

        # Capitalize
        if clean_name:
            clean_name = clean_name[0].upper() + clean_name[1:]
        else:
            clean_name = "Actividad"

        category = _infer_category(clean_name + " " + msg_lower)
        emoji = CATEGORY_EMOJI.get(category, "📌")

        return {
            "action": "add_block",
            "data": {
                "schedule_date": current_date,
                "start_time": start_time,
                "end_time": end_time,
                "title": f"{clean_name} {emoji}",
                "category": category,
                "description": "",
            },
            "response": f"✅ Agregado: **{clean_name}** {emoji} de {start_time} a {end_time} ({CATEGORY_LABEL.get(category, category)})",
        }

    # ── Preferences shortcuts ────────────────────────────
    pref_updates = {}

    wake_match = re.search(r"(?:despierto|levanto|despertar|levantarme)\s+a\s+las?\s+(\d{1,2}(?::\d{2})?)\s*(am|pm)?", msg_lower)
    if wake_match:
        t = _parse_time(wake_match.group(1) + (" " + wake_match.group(2) if wake_match.group(2) else ""))
        if t:
            pref_updates["wake_time"] = t

    sleep_match = re.search(r"(?:duermo|acuesto|dormir|acostarme)\s+a\s+las?\s+(\d{1,2}(?::\d{2})?)\s*(am|pm)?", msg_lower)
    if sleep_match:
        t = _parse_time(sleep_match.group(1) + (" " + sleep_match.group(2) if sleep_match.group(2) else ""))
        if t:
            pref_updates["sleep_time"] = t

    work_match = re.search(r"trabajo\s+de\s+(?:las?\s+)?(\d{1,2}(?::\d{2})?)\s*(am|pm)?\s+a\s+(?:las?\s+)?(\d{1,2}(?::\d{2})?)\s*(am|pm)?", msg_lower)
    if work_match:
        ws = _parse_time(work_match.group(1) + (" " + work_match.group(2) if work_match.group(2) else ""))
        we = _parse_time(work_match.group(3) + (" " + work_match.group(4) if work_match.group(4) else ""))
        if ws: pref_updates["work_start"] = ws
        if we: pref_updates["work_end"] = we

    if pref_updates:
        parts = []
        if "wake_time" in pref_updates:
            parts.append(f"despertar a las {pref_updates['wake_time']}")
        if "sleep_time" in pref_updates:
            parts.append(f"dormir a las {pref_updates['sleep_time']}")
        if "work_start" in pref_updates:
            parts.append(f"trabajo de {pref_updates.get('work_start', '?')} a {pref_updates.get('work_end', '?')}")

        return {
            "action": "update_preferences",
            "data": pref_updates,
            "response": f"⚙️ Preferencias actualizadas: {', '.join(parts)}. Puedes decir *genera mi horario* para aplicar los cambios.",
        }

    # ── Help ──────────────────────────────────────────────
    if re.search(r"(?:ayuda|help|comandos|qué puedo|que puedo|cómo|como funciona)", msg_lower):
        return {
            "action": "none",
            "data": {},
            "response": (
                "🤖 **¡Hola! Soy tu asistente de horario.** Puedo ayudarte con:\n\n"
                "• **Agregar**: *agrega reunión de 10 a 12*\n"
                "• **Eliminar**: *elimina el ejercicio*\n"
                "• **Mover**: *mueve el estudio a las 6pm*\n"
                "• **Consultar**: *¿qué tengo a las 3?*\n"
                "• **Generar**: *genera mi horario*\n"
                "• **Preferencias**: *me despierto a las 6, trabajo de 8 a 4*\n"
                "• **PDF**: *descarga el horario*\n"
                "• **Ver todo**: *muéstrame mi horario*"
            ),
        }

    # ── Greetings ─────────────────────────────────────────
    if re.search(r"^(?:hola|hey|buenas|buenos|hi|hello|saludos|qué tal|que tal)", msg_lower):
        return {
            "action": "none",
            "data": {},
            "response": (
                "👋 ¡Hola! Soy tu asistente de planificación. "
                "Dime qué necesitas: puedo agregar, eliminar o mover actividades, "
                "generar tu horario completo, o exportarlo a PDF. "
                "Escribe *ayuda* para ver todos los comandos."
            ),
        }

    # ── Fallback ──────────────────────────────────────────
    return {
        "action": "none",
        "data": {},
        "response": (
            "🤔 No logré interpretar eso. Intenta algo como:\n\n"
            "• *agrega yoga de 6 a 7am*\n"
            "• *elimina el tiempo libre*\n"
            "• *genera mi horario*\n"
            "• *¿qué tengo a las 3?*\n\n"
            "Escribe *ayuda* para ver todos los comandos."
        ),
    }
