"""FastAPI main application — Smart Day Planner."""

from contextlib import asynccontextmanager
from datetime import date
import io
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import speech_recognition as sr
from pydub import AudioSegment

import database as db
from models import Preferences, ScheduleBlockCreate, ScheduleBlockUpdate, AgentChatRequest
from planner_engine import generate_schedule
from pdf_generator import generate_pdf
from agent import process_message


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    await db.init_db()
    yield


app = FastAPI(
    title="Smart Day Planner",
    description="Planificador inteligente de 24 horas",
    version="1.0.0",
    lifespan=lifespan,
)

# Static files & templates (resolved relative to this file for serverless compatibility)
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


# ── Pages ────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main SPA page."""
    return templates.TemplateResponse("index.html", {"request": request})


# ── Preferences API ─────────────────────────────────────────

@app.get("/api/preferences")
async def api_get_preferences():
    """Get current user preferences."""
    data = await db.get_preferences()
    # Merge with defaults
    defaults = Preferences().model_dump()
    defaults.update(data)
    return defaults


@app.put("/api/preferences")
async def api_save_preferences(prefs: Preferences):
    """Save user preferences."""
    saved = await db.save_preferences(prefs.model_dump())
    return saved


# ── Schedule API ─────────────────────────────────────────────

@app.get("/api/schedule/{schedule_date}")
async def api_get_schedule(schedule_date: str):
    """Get schedule for a specific date."""
    blocks = await db.get_schedule(schedule_date)
    return {"date": schedule_date, "blocks": blocks}


@app.post("/api/schedule/generate")
async def api_generate_schedule(prefs: Preferences, target_date: str = None):
    """Generate an intelligent schedule and save it."""
    if not target_date:
        target_date = date.today().isoformat()
    
    blocks = generate_schedule(prefs, target_date)
    saved_blocks = await db.save_schedule(target_date, blocks)
    return {"date": target_date, "blocks": saved_blocks}


@app.put("/api/schedule/block/{block_id}")
async def api_update_block(block_id: int, updates: ScheduleBlockUpdate):
    """Update a specific schedule block."""
    update_data = updates.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(400, "No fields to update")
    
    result = await db.update_block(block_id, update_data)
    if not result:
        raise HTTPException(404, "Block not found")
    return result


@app.delete("/api/schedule/block/{block_id}")
async def api_delete_block(block_id: int):
    """Delete a schedule block."""
    deleted = await db.delete_block(block_id)
    if not deleted:
        raise HTTPException(404, "Block not found")
    return {"ok": True}


@app.post("/api/schedule/block")
async def api_add_block(block: ScheduleBlockCreate):
    """Add a new schedule block."""
    result = await db.add_block(block.model_dump())
    return result


@app.get("/api/dates")
async def api_get_dates():
    """Get all dates with saved schedules."""
    dates = await db.get_dates_with_schedules()
    return {"dates": dates}


# ── AI Agent API ─────────────────────────────────────────────

@app.post("/api/agent/chat")
async def api_agent_chat(req: AgentChatRequest):
    """Process natural language request via the planner agent."""
    target_date = req.target_date or date.today().isoformat()
    blocks = await db.get_schedule(target_date)
    
    result = process_message(req.message, blocks, target_date)
    action = result.get("action", "none")
    data = result.get("data", {})
    
    if action == "add_block":
        await db.add_block(data)
    elif action == "delete_block":
        if "block_id" in data:
            await db.delete_block(data["block_id"])
    elif action == "update_block":
        if "block_id" in data and "updates" in data:
            await db.update_block(data["block_id"], data["updates"])
    elif action == "generate":
        prefs_data = await db.get_preferences()
        merged = Preferences().model_dump()
        merged.update(prefs_data)
        prefs_obj = Preferences(**merged)
        generated = generate_schedule(prefs_obj, target_date)
        await db.save_schedule(target_date, generated)
    elif action == "update_preferences":
        prefs_data = await db.get_preferences()
        merged = Preferences().model_dump()
        merged.update(prefs_data)
        merged.update(data)
        await db.save_preferences(merged)
        
    updated_blocks = await db.get_schedule(target_date)
    dates = await db.get_dates_with_schedules()
    prefs_current = await db.get_preferences()
    merged_prefs = Preferences().model_dump()
    merged_prefs.update(prefs_current)
    
    return {
        "response": result.get("response", ""),
        "action": action,
        "blocks": updated_blocks,
        "dates": dates,
        "preferences": merged_prefs,
    }


@app.post("/api/agent/voice")
async def api_agent_voice(
    audio_file: UploadFile = File(...),
    target_date: str = Form(None),
):
    """Transcribe audio recorded in browser and process command."""
    target_date = target_date or date.today().isoformat()
    content = await audio_file.read()
    
    transcribed_text = ""
    try:
        audio_segment = AudioSegment.from_file(io.BytesIO(content))
        wav_io = io.BytesIO()
        audio_segment.export(wav_io, format="wav")
        wav_io.seek(0)
        
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_io) as source:
            recorded_audio = recognizer.record(source)
        
        transcribed_text = recognizer.recognize_google(recorded_audio, language="es-ES")
    except sr.UnknownValueError:
        return {
            "transcription": "",
            "response": "🎙️ No pude entender claramente lo que dijiste. Intenta hablar más cerca del micrófono o más despacio.",
            "action": "none",
            "blocks": await db.get_schedule(target_date),
            "dates": await db.get_dates_with_schedules(),
            "preferences": await db.get_preferences(),
        }
    except Exception as e:
        return {
            "transcription": "",
            "response": f"⚠️ Error en el servicio de transcripción: {str(e)}",
            "action": "none",
            "blocks": await db.get_schedule(target_date),
            "dates": await db.get_dates_with_schedules(),
            "preferences": await db.get_preferences(),
        }

    # Process recognized text
    blocks = await db.get_schedule(target_date)
    result = process_message(transcribed_text, blocks, target_date)
    action = result.get("action", "none")
    data = result.get("data", {})
    
    if action == "add_block":
        await db.add_block(data)
    elif action == "delete_block":
        if "block_id" in data:
            await db.delete_block(data["block_id"])
    elif action == "update_block":
        if "block_id" in data and "updates" in data:
            await db.update_block(data["block_id"], data["updates"])
    elif action == "generate":
        prefs_data = await db.get_preferences()
        merged = Preferences().model_dump()
        merged.update(prefs_data)
        prefs_obj = Preferences(**merged)
        generated = generate_schedule(prefs_obj, target_date)
        await db.save_schedule(target_date, generated)
    elif action == "update_preferences":
        prefs_data = await db.get_preferences()
        merged = Preferences().model_dump()
        merged.update(prefs_data)
        merged.update(data)
        await db.save_preferences(merged)
        
    updated_blocks = await db.get_schedule(target_date)
    dates = await db.get_dates_with_schedules()
    prefs_current = await db.get_preferences()
    merged_prefs = Preferences().model_dump()
    merged_prefs.update(prefs_current)
    
    return {
        "transcription": transcribed_text,
        "response": result.get("response", ""),
        "action": action,
        "blocks": updated_blocks,
        "dates": dates,
        "preferences": merged_prefs,
    }


# ── PDF Export ───────────────────────────────────────────────

@app.get("/api/schedule/{schedule_date}/pdf")
async def api_download_pdf(schedule_date: str):
    """Generate and download the schedule as PDF."""
    blocks = await db.get_schedule(schedule_date)
    if not blocks:
        raise HTTPException(404, "No schedule found for this date")
    
    pdf_bytes = generate_pdf(blocks, schedule_date)
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="horario_{schedule_date}.pdf"'
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
