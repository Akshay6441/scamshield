"""
ScamShield — Autonomous Multi-Agent Digital Scam Detection System
Nebius x NVIDIA Global AI Hackathon (Best Apps and Agents Track)

Architectural Workflow:
  1. Input: Suspicious SMS, WhatsApp message, email, or URL
  2. Agent 1 (Cyber Threat Investigator): Live threat intelligence via Tavily API
  3. Agent 2 (Cognitive Psychologist): Deep reasoning via NVIDIA Nemotron Ultra 70B (Nebius)
  4. Agent 3 (Judicial Synthesizer): Swift verdict & defense protocol via NVIDIA Nemotron Nano 8B (Nebius)
  5. Real-Time Streaming: Server-Sent Events (SSE) push live agent deliberations to UI
"""

import os
import uuid
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from agents.investigator import InvestigatorAgent
from agents.psychologist import PsychologistAgent
from agents.judge import JudgeAgent

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("scamshield.main")

# Load environment variables
load_dotenv()

app = FastAPI(
    title="ScamShield",
    description="Multi-Agent Scam & Social Engineering Defense System — Nebius x NVIDIA Hackathon",
    version="1.0.0",
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static assets
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# In-memory job repository
jobs: Dict[str, Dict[str, Any]] = {}

# Preloaded Benchmark Test Cases for Hackathon Judges & Users
PRESET_EXAMPLES = [
    {
        "id": "usps-phishing",
        "category": "SMS Phishing (Smishing)",
        "label": "USPS Package Delivery Failure",
        "text": "USPS Notice: Your package #US94001092023 cannot be delivered due to incomplete address information. Please update your details within 12 hours at https://usps-parcel-track-update.xyz/verify or your package will be returned to sender and an administrative penalty fee applied.",
        "expected": "CONFIRMED SCAM"
    },
    {
        "id": "bank-impersonation",
        "category": "Banking Fraud",
        "label": "Chase Fraud Alert & OTP Theft",
        "text": "CHASE FRAUD ALERT: A suspicious charge of $1,842.90 at Apple Store NYC was attempted on your debit card ending in 4108. If this was NOT you, call our urgent fraud line immediately at +1-888-941-0294 or reply with your 6-digit one-time passcode to freeze the transaction immediately.",
        "expected": "CONFIRMED SCAM"
    },
    {
        "id": "telegram-job-scam",
        "category": "Task / Employment Scam",
        "label": "Remote YouTube Review Job",
        "text": "Hello! I am Sarah from Global Digital HR. We saw your resume on LinkedIn and are pleased to offer a flexible remote part-time role. Earn $300 to $800 daily by simply rating YouTube videos and Google Maps locations for 30 minutes a day. No experience needed! Contact our hiring manager on Telegram @GlobalHR_Sarah to receive your $50 signup bonus in USDT.",
        "expected": "CONFIRMED SCAM"
    },
    {
        "id": "ceo-giftcard",
        "category": "Business Email Compromise (BEC)",
        "label": "Urgent CEO Apple Gift Card Request",
        "text": "Hi, I am currently stuck in an executive board meeting and cannot take calls right now. I urgently need you to purchase 5 x $100 Apple Gift Cards for our client appreciation presentation this afternoon. Please scratch the backs, take clear photos of the redemption codes, and email them back to me as soon as possible. I will reimburse you by end of day.",
        "expected": "CONFIRMED SCAM"
    },
    {
        "id": "legit-amazon",
        "category": "Legitimate Notification",
        "label": "Amazon Official Order Confirmation",
        "text": "Hi Alex, thanks for your order #114-8291048-2849102. Your order of 'USB-C Cable 2-Pack' has shipped and is expected to arrive on Thursday, October 30. You can view your order status, track shipment, or manage delivery anytime in the official Amazon app or by visiting your Account on amazon.com.",
        "expected": "LIKELY SAFE"
    }
]


class AnalyzeRequest(BaseModel):
    content: str = Field(..., min_length=5, max_length=5000, description="Suspicious text, message, or email to inspect")


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve the ScamShield web interface."""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>ScamShield Defense Platform</h1><p>Static files missing.</p>")


@app.get("/api/health")
async def health_check():
    """Verify runtime configuration, Nebius models, and Tavily connectivity."""
    nebius_key = os.getenv("NEBIUS_API_KEY", "")
    tavily_key = os.getenv("TAVILY_API_KEY", "")

    nebius_active = bool(nebius_key and nebius_key != "your_nebius_api_key_here")
    tavily_active = bool(tavily_key and tavily_key != "your_tavily_api_key_here")

    return {
        "status": "ready" if (nebius_active and tavily_active) else "partially_configured",
        "nebius_token_factory": {
            "configured": nebius_active,
            "base_url": os.getenv("NEBIUS_BASE_URL", "https://api.studio.nebius.com/v1/"),
            "ultra_model": os.getenv("NEMOTRON_ULTRA", "nvidia/Llama-3.1-Nemotron-70B-Instruct-HF"),
            "nano_model": os.getenv("NEMOTRON_NANO", "nvidia/llama-3.1-nemotron-nano-8b-v1")
        },
        "tavily_search": {
            "configured": tavily_active,
            "role": "Live threat intelligence & fraud telemetry search"
        },
        "hackathon_track": "Best Apps and Agents Track",
        "target_bonus": "Best Use of Tavily ($3,000 USD)"
    }


@app.get("/api/examples")
async def get_examples():
    """Return preloaded test cases for rapid judge evaluation."""
    return {"examples": PRESET_EXAMPLES}


async def run_scamshield_pipeline(job_id: str, content: str):
    """
    Execute the multi-agent investigation pipeline and stream events.
    """
    job = jobs[job_id]
    
    def log_event(event_type: str, message: str, data: Any = None):
        payload = {
            "event": event_type,
            "message": message,
            "data": data,
            "step": job["step"]
        }
        job["events"].append(payload)
        job["step"] += 1
        logger.info(f"[{job_id}] Event: {event_type} - {message}")

    try:
        # -------------------------------------------------------------
        # STAGE 1: Cyber Threat Investigator (Tavily Search API)
        # -------------------------------------------------------------
        job["status"] = "investigating"
        log_event(
            "investigator_started",
            "Agent 1 (Cyber Threat Investigator) launched: scanning content for suspicious URLs, domains, phone numbers, and brand signatures."
        )
        await asyncio.sleep(0.3)

        investigator = InvestigatorAgent()
        entities = investigator.extract_entities(content)
        log_event(
            "entities_extracted",
            f"Extracted threat vectors: {len(entities['urls'])} URLs, {len(entities['domains'])} domains, {len(entities['phones'])} phone numbers, {len(entities['brands'])} brand mentions.",
            {"entities": entities}
        )
        await asyncio.sleep(0.3)

        log_event(
            "tavily_search_dispatched",
            "Dispatching targeted live queries to Tavily Search API across public fraud registries, scam complaint boards, and threat feeds..."
        )
        investigator_result = await investigator.investigate(content)

        log_event(
            "investigator_complete",
            f"Investigation finished with Threat Level [{investigator_result['threat_level']}]. Found {len(investigator_result['scam_reports_found'])} matching threat records and {len(investigator_result['external_sources'])} live web citations.",
            {"investigator_result": investigator_result}
        )
        await asyncio.sleep(0.4)

        # -------------------------------------------------------------
        # STAGE 2: Cognitive Psychologist (NVIDIA Nemotron Ultra 70B)
        # -------------------------------------------------------------
        job["status"] = "psychological_profiling"
        log_event(
            "psychologist_started",
            "Routing to Agent 2 (Cognitive Psychologist) powered by NVIDIA Nemotron Ultra 70B via Nebius Token Factory for deep social engineering analysis."
        )
        await asyncio.sleep(0.3)

        psychologist = PsychologistAgent()
        psychologist_result = await psychologist.analyze(
            content,
            investigator_context=investigator_result.get("evidence_summary", "")
        )

        log_event(
            "psychologist_complete",
            f"Cognitive analysis completed. Manipulation Score: {psychologist_result.get('manipulation_score', 0)}/100 ({psychologist_result.get('manipulation_category', 'UNKNOWN')}). Primary Tactic: {psychologist_result.get('primary_tactic', 'N/A')}.",
            {"psychologist_result": psychologist_result}
        )
        await asyncio.sleep(0.4)

        # -------------------------------------------------------------
        # STAGE 3: Judicial Arbiter (NVIDIA Nemotron Nano 8B)
        # -------------------------------------------------------------
        job["status"] = "judicial_deliberation"
        log_event(
            "judge_started",
            "Routing to Agent 3 (Judicial Arbiter) powered by NVIDIA Nemotron Nano 8B via Nebius Token Factory for rapid adversarial synthesis and defensive action planning."
        )
        await asyncio.sleep(0.3)

        judge = JudgeAgent()
        judge_result = await judge.deliberate(
            content,
            investigator_data=investigator_result,
            psychologist_data=psychologist_result
        )

        log_event(
            "judge_complete",
            f"Final ruling rendered: [{judge_result.get('verdict', 'SUSPICIOUS')}] with {judge_result.get('risk_score', 50)}% Risk Score and {judge_result.get('confidence_percent', 85)}% Confidence.",
            {"judge_result": judge_result}
        )

        # Finalize job
        job["status"] = "completed"
        job["result"] = {
            "verdict": judge_result.get("verdict", "SUSPICIOUS"),
            "risk_score": judge_result.get("risk_score", 50),
            "confidence_percent": judge_result.get("confidence_percent", 85),
            "executive_summary": judge_result.get("executive_summary", ""),
            "top_red_flags": judge_result.get("top_red_flags", []),
            "action_plan": judge_result.get("action_plan", []),
            "safe_counter_response": judge_result.get("safe_counter_response", ""),
            "investigator": investigator_result,
            "psychologist": psychologist_result,
            "judge": judge_result
        }
        log_event("pipeline_finished", "Autonomous ScamShield defense workflow concluded successfully.")

    except Exception as e:
        logger.exception(f"Pipeline error for job {job_id}: {e}")
        job["status"] = "failed"
        job["error"] = str(e)
        log_event("error", f"Pipeline encountered an exception: {e}")


@app.post("/api/analyze")
async def start_analysis(req: AnalyzeRequest, background_tasks: BackgroundTasks):
    """Initiate an autonomous scam investigation job."""
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "step": 0,
        "content": req.content,
        "events": [],
        "result": None,
        "error": None
    }
    background_tasks.add_task(run_scamshield_pipeline, job_id, req.content)
    return {"job_id": job_id, "status": "queued"}


@app.get("/api/jobs/{job_id}/stream")
async def stream_job_events(job_id: str):
    """
    Stream real-time Server-Sent Events (SSE) representing agent thoughts and findings.
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Investigation job not found")

    async def event_generator():
        last_index = 0
        job = jobs[job_id]

        while True:
            events = job["events"]
            while last_index < len(events):
                ev = events[last_index]
                yield {
                    "event": ev["event"],
                    "data": json.dumps(ev)
                }
                last_index += 1

            if job["status"] in ("completed", "failed"):
                # Yield final state wrap-up
                yield {
                    "event": "done",
                    "data": json.dumps({
                        "status": job["status"],
                        "result": job["result"],
                        "error": job.get("error")
                    })
                }
                break

            await asyncio.sleep(0.2)

    return EventSourceResponse(event_generator())


@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Retrieve the full status and result payload of an investigation job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    logger.info(f"Starting ScamShield server on http://{host}:{port}")
    uvicorn.run("main:app", host=host, port=port, reload=True)
