"""Intelligent planning engine that generates optimized 24-hour schedules."""

from models import Preferences


def _time_to_minutes(time_str: str) -> int:
    """Convert 'HH:MM' to minutes since midnight."""
    h, m = map(int, time_str.split(":"))
    return h * 60 + m


def _minutes_to_time(minutes: int) -> str:
    """Convert minutes since midnight to 'HH:MM'."""
    minutes = minutes % 1440
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _make_block(
    title: str,
    start: int,
    end: int,
    category: str,
    date: str,
    description: str = "",
) -> dict:
    """Create a schedule block dict."""
    return {
        "schedule_date": date,
        "start_time": _minutes_to_time(start),
        "end_time": _minutes_to_time(end),
        "title": title,
        "category": category,
        "description": description,
        "is_fixed": 0,
    }


def generate_schedule(prefs: Preferences, target_date: str) -> list[dict]:
    """
    Generate an intelligent 24-hour schedule based on user preferences.
    
    The algorithm:
    1. Anchor sleep blocks (before wake and after sleep time)
    2. Place morning routine + breakfast
    3. Pre-work activities (exercise if enabled and fits)
    4. Work block split by lunch at midpoint
    5. Post-work: study if enabled, then dinner ~2h before sleep
    6. Fill gaps with free/personal time
    
    Returns a list of non-overlapping blocks covering the full 24 hours.
    """
    blocks: list[dict] = []
    
    wake = _time_to_minutes(prefs.wake_time)
    sleep = _time_to_minutes(prefs.sleep_time)
    work_start = _time_to_minutes(prefs.work_start)
    work_end = _time_to_minutes(prefs.work_end)

    # ── Phase 1: Early morning sleep ────────────────────────
    if wake > 0:
        blocks.append(_make_block(
            "Dormir 🌙", 0, wake, "sleep", target_date,
            "Descanso nocturno"
        ))

    cursor = wake

    # ── Phase 2: Morning routine ────────────────────────────
    routine_dur = 30
    blocks.append(_make_block(
        "Rutina matutina 🌅", cursor, cursor + routine_dur, "routine", target_date,
        "Higiene personal, prepararse para el día"
    ))
    cursor += routine_dur

    # ── Phase 3: Breakfast ──────────────────────────────────
    blocks.append(_make_block(
        "Desayuno 🍳", cursor, cursor + prefs.breakfast_duration, "meal", target_date,
        "Primera comida del día"
    ))
    cursor += prefs.breakfast_duration

    # ── Phase 4: Pre-work exercise ──────────────────────────
    if prefs.exercise_enabled and cursor + prefs.exercise_duration <= work_start:
        blocks.append(_make_block(
            "Ejercicio 💪", cursor, cursor + prefs.exercise_duration, "exercise", target_date,
            "Actividad física matutina"
        ))
        cursor += prefs.exercise_duration

    # ── Phase 5: Gap before work → personal time ────────────
    if cursor < work_start:
        blocks.append(_make_block(
            "Tiempo personal ☕", cursor, work_start, "personal", target_date,
            "Lectura, meditación, preparación"
        ))
        cursor = work_start

    # ── Phase 6: Work with lunch break ──────────────────────
    work_mid = (work_start + work_end) // 2
    lunch_start = work_mid - prefs.lunch_duration // 2
    lunch_end = lunch_start + prefs.lunch_duration

    # Ensure lunch fits within work hours
    lunch_start = max(lunch_start, work_start + 60)
    lunch_end = lunch_start + prefs.lunch_duration

    if lunch_end > work_end - 30:
        lunch_start = work_end - prefs.lunch_duration - 30
        lunch_end = lunch_start + prefs.lunch_duration

    # Work part 1
    if work_start < lunch_start:
        blocks.append(_make_block(
            "Trabajo 💼", work_start, lunch_start, "work", target_date,
            "Bloque de trabajo matutino"
        ))

    # Lunch
    blocks.append(_make_block(
        "Almuerzo 🍽️", lunch_start, lunch_end, "meal", target_date,
        "Comida del mediodía y descanso"
    ))

    # Work part 2
    if lunch_end < work_end:
        blocks.append(_make_block(
            "Trabajo 💼", lunch_end, work_end, "work", target_date,
            "Bloque de trabajo vespertino"
        ))

    cursor = work_end

    # ── Phase 7: Post-work activities ───────────────────────
    # Calculate remaining time before sleep
    remaining = sleep - cursor

    # Exercise (if not done in morning)
    exercise_done = any(b["category"] == "exercise" for b in blocks)
    if prefs.exercise_enabled and not exercise_done and remaining >= prefs.exercise_duration + prefs.dinner_duration + 90:
        blocks.append(_make_block(
            "Ejercicio 💪", cursor, cursor + prefs.exercise_duration, "exercise", target_date,
            "Actividad física vespertina"
        ))
        cursor += prefs.exercise_duration

    # Study
    if prefs.study_enabled:
        available_for_study = sleep - cursor - prefs.dinner_duration - 60
        actual_study = min(prefs.study_duration, max(0, available_for_study))
        if actual_study >= 30:
            blocks.append(_make_block(
                "Estudio 📚", cursor, cursor + actual_study, "study", target_date,
                "Aprendizaje y desarrollo personal"
            ))
            cursor += actual_study

    # ── Phase 8: Dinner ─────────────────────────────────────
    # Place dinner approximately 2 hours before sleep
    ideal_dinner = sleep - 120
    dinner_start = max(cursor, ideal_dinner)

    # Free time before dinner
    if cursor < dinner_start:
        blocks.append(_make_block(
            "Tiempo libre 🎮", cursor, dinner_start, "free", target_date,
            "Ocio, hobbies, descanso"
        ))
        cursor = dinner_start

    blocks.append(_make_block(
        "Cena 🍲", cursor, cursor + prefs.dinner_duration, "meal", target_date,
        "Última comida del día"
    ))
    cursor += prefs.dinner_duration

    # ── Phase 9: Evening wind-down ──────────────────────────
    night_routine_dur = 20
    wind_down_end = sleep - night_routine_dur

    if cursor < wind_down_end:
        blocks.append(_make_block(
            "Tiempo libre 🎮", cursor, wind_down_end, "free", target_date,
            "Relax, series, lectura ligera"
        ))
        cursor = wind_down_end

    # Night routine
    if cursor < sleep:
        blocks.append(_make_block(
            "Rutina nocturna 🌙", cursor, sleep, "routine", target_date,
            "Preparación para dormir, higiene"
        ))
        cursor = sleep

    # ── Phase 10: Night sleep ───────────────────────────────
    if sleep < 1440:
        blocks.append(_make_block(
            "Dormir 🌙", sleep, 1440, "sleep", target_date,
            "Descanso nocturno"
        ))

    # Sort by start time
    blocks.sort(key=lambda b: _time_to_minutes(b["start_time"]))

    return blocks
