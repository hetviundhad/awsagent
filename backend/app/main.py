import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.app.api.api import api_router
from backend.app.core.config import settings

app = FastAPI(
    title="StudyMind AI - Multimodal Tutor & Adaptive Learning",
    description="Backend API for Multimodal AI Hackathon 2026 - Track D",
    version="1.0.0"
)

# Configure CORS for Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.responses import JSONResponse
from backend.app.core.errors import AIServiceUnavailableError

@app.exception_handler(AIServiceUnavailableError)
async def ai_service_unavailable_handler(request, exc: AIServiceUnavailableError):
    return JSONResponse(
        status_code=503,
        content={"error": "AI service unavailable, retry"}
    )

from pydantic import BaseModel
import requests

class AutoConfirmRequest(BaseModel):
    email: str

@app.post("/api/auth/auto-confirm")
def auto_confirm_user_email(payload: AutoConfirmRequest):
    """
    Auto-confirms a user's email using Supabase Service Role Admin API.
    Prevents students and evaluators from getting blocked by 'Email not confirmed'.
    """
    target_email = payload.email.strip().lower()
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        return {"status": "skipped", "message": "Supabase credentials not configured"}
    
    admin_headers = {
        "apikey": settings.SUPABASE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        res = requests.get(
            f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/admin/users",
            headers=admin_headers,
            timeout=8
        )
        if res.status_code == 200:
            users = res.json().get("users", [])
            user_match = next((u for u in users if u.get("email", "").lower() == target_email), None)
            if user_match:
                uid = user_match["id"]
                confirm_res = requests.put(
                    f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/admin/users/{uid}",
                    headers=admin_headers,
                    json={"email_confirm": True},
                    timeout=8
                )
                if confirm_res.status_code in (200, 204):
                    return {"status": "success", "message": f"Confirmed email for {target_email}", "user_id": uid}
                else:
                    return {"status": "error", "message": f"Admin update failed: {confirm_res.text}"}
            else:
                return {"status": "not_found", "message": f"User {target_email} not found"}
        return {"status": "error", "message": f"Admin list users failed: {res.text}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/health/ai")
def health_ai():
    """
    Diagnostic health check for AI services:
    Calls LLM model-list endpoint and runs a 1-token completion test.
    Checks embedding, vision, and STT providers.
    Returns {llm_ok, model, embedding_ok, vision_ok, stt_ok, error}.
    """
    import urllib.request
    import json
    from backend.app.core.config import is_test_environment

    llm_ok = False
    embedding_ok = False
    vision_ok = False
    stt_ok = False
    error_msg = None

    target_model = settings.LLM_MODEL
    # 1. LLM check: checks active provider (Bedrock, Groq, Mock)
    try:
        provider = (settings.LLM_PROVIDER or "groq").lower().strip()
        if provider == "bedrock":
            from backend.app.providers.bedrock_provider import get_bedrock
            br = get_bedrock()
            br_stat = br.status(force=True)
            if br_stat.get("ok"):
                llm_ok = True
                target_model = f"Bedrock ({settings.BEDROCK_MODEL_FAST})"
            elif settings.GROQ_API_KEY and settings.GROQ_API_KEY.strip():
                target_model = f"Groq ({settings.LLM_MODEL})"
                llm_ok = True
            else:
                target_model = f"Bedrock ({settings.BEDROCK_MODEL_FAST})"
                error_msg = br_stat.get("error") or "AWS credentials not configured for Amazon Bedrock"
        elif settings.GROQ_API_KEY and settings.GROQ_API_KEY.strip():
            headers = {
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json",
                "User-Agent": "StudyMind/1.0"
            }
            # Test model list endpoint
            req_models = urllib.request.Request("https://api.groq.com/openai/v1/models", headers=headers)
            with urllib.request.urlopen(req_models, timeout=8) as res_models:
                models_data = json.loads(res_models.read().decode('utf-8'))
                available_ids = [m.get("id") for m in models_data.get("data", [])]
                if target_model not in available_ids:
                    error_msg = f"Model '{target_model}' not found in available provider models: {available_ids[:5]}"
                else:
                    payload = json.dumps({
                        "model": target_model,
                        "messages": [{"role": "user", "content": "1"}],
                        "max_tokens": 1
                    }).encode('utf-8')
                    req_comp = urllib.request.Request(
                        "https://api.groq.com/openai/v1/chat/completions",
                        data=payload,
                        headers=headers
                    )
                    with urllib.request.urlopen(req_comp, timeout=8) as res_comp:
                        if res_comp.status == 200:
                            llm_ok = True
        elif is_test_environment() or provider in ("mock", "offline"):
            llm_ok = True
            target_model = "Mock Engine"
        else:
            error_msg = f"{provider.capitalize()} API credentials not configured"
    except Exception as e:
        error_msg = f"LLM health test failed: {e}"

    # 2. Embedding check
    try:
        from backend.app.providers.embedding_provider import get_embedding_provider
        emb_prov = get_embedding_provider(settings.EMBEDDING_PROVIDER, settings.OPENAI_API_KEY)
        v = emb_prov.embed_text("health")
        if v and len(v) > 0:
            embedding_ok = True
    except Exception as e:
        if not error_msg:
            error_msg = f"Embedding provider error: {e}"

    # 3. Vision check
    vision_ok = False
    vision_reason = None
    if settings.VISION_MODEL and settings.VISION_MODEL.strip():
        try:
            import httpx
            tiny_png_b64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAEAST+4AQAAAAASUVORK5CYII="
            if settings.GROQ_API_KEY and settings.GROQ_API_KEY.strip():
                v_headers = {
                    "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                    "Content-Type": "application/json"
                }
                v_payload = {
                    "model": settings.VISION_MODEL,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Describe this in 1 word"},
                                {"type": "image_url", "image_url": {"url": tiny_png_b64}}
                            ]
                        }
                    ],
                    "max_tokens": 10
                }
                with httpx.Client(timeout=8.0) as client:
                    v_res = client.post("https://api.groq.com/openai/v1/chat/completions", headers=v_headers, json=v_payload)
                    if v_res.status_code == 200:
                        vision_ok = True
                    else:
                        vision_reason = f"Vision call failed ({v_res.status_code})"
            else:
                vision_reason = "GROQ_API_KEY is not configured"
        except Exception as e:
            vision_reason = f"Vision call failed: {e}"
    else:
        vision_ok = False
        vision_reason = "VISION_MODEL not set"

    # 4. STT check
    try:
        from backend.app.providers.stt_provider import get_stt_provider
        s_prov = get_stt_provider(settings.STT_PROVIDER)
        if s_prov:
            stt_ok = True
    except Exception as e:
        if not error_msg:
            error_msg = f"STT provider error: {e}"

    return {
        "llm_ok": llm_ok,
        "model": target_model,
        "embedding_ok": embedding_ok,
        "vision_ok": vision_ok,
        "vision_reason": vision_reason,
        "stt_ok": stt_ok,
        "error": error_msg
    }

# Mount API routes
app.include_router(api_router)

# Mount local storage for direct static viewing (uploads, figures, keyframes)
uploads_dir = os.path.join(settings.STORAGE_DIR, "uploads")
figures_dir = os.path.join(settings.STORAGE_DIR, "figures")
keyframes_dir = os.path.join(settings.STORAGE_DIR, "keyframes")
os.makedirs(uploads_dir, exist_ok=True)
os.makedirs(figures_dir, exist_ok=True)
os.makedirs(keyframes_dir, exist_ok=True)
app.mount("/static/uploads", StaticFiles(directory=uploads_dir), name="uploads")
app.mount("/static/figures", StaticFiles(directory=figures_dir), name="figures")
app.mount("/static/keyframes", StaticFiles(directory=keyframes_dir), name="keyframes")

from backend.app.services.startup_check import run_startup_self_check

@app.on_event("startup")
def startup_event():
    print("==================================================")
    print("StudyMind AI Backend Initializing...")
    print(f"Storage Directory: {settings.STORAGE_DIR}")
    print(f"Supabase configured: {'Yes' if settings.SUPABASE_URL else 'No (using local persistent store)'}")
    # Students start clean with their own isolated database. Demo can be loaded on-demand via Reload Demo.
    print("Running startup integrity self-check (Step 1 Requirement 6)...")
    run_startup_self_check()
    print("StudyMind AI is ready for Hackathon demonstration!")
    print("==================================================")

@app.get("/")
def root():
    return {
        "name": "StudyMind AI",
        "tagline": "Your course material. Your learning path. Your AI tutor.",
        "status": "online",
        "api_docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
