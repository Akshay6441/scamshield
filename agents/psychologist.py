"""
ScamShield — Cognitive & Psychological Analyst Agent
Powered by NVIDIA Nemotron-70B Ultra via Nebius Token Factory

Responsibilities:
  1. Perform deep reasoning on social engineering, persuasion techniques, and cognitive vulnerabilities.
  2. Detect manufactured urgency, artificial authority, fear induction, and greed triggers.
  3. Analyze linguistic markers, obfuscation patterns, and syntax anomalies.
  4. Compute a Psychological Threat Index (0-100) and dissect emotional exploitation vectors.
"""

import os
import json
import logging
from typing import Dict, Any
from openai import OpenAI

logger = logging.getLogger("scamshield.psychologist")

PSYCHOLOGIST_SYSTEM_PROMPT = """You are the Senior Cognitive Defense & Social Engineering Analyst for ScamShield.
Your expertise is in behavioral psychology, linguistic deception analysis, and cyber social engineering tactics.

Your mission is to evaluate the psychological manipulation present in the provided suspicious message.
You must analyze:
1. Manufactured Urgency: Is an artificial time constraint imposed to induce panic and bypass rational critical thinking?
2. Authority & Coercion: Is there intimidation, legal threats, police/tax/bank authority impersonation?
3. Reward & Greed Lure: Are unrealistic financial returns, refunds, lottery wins, or unearned benefits offered?
4. Emotional Exploitation: Does it target fear, loneliness, panic over a loved one, or curiosity?
5. Linguistic Obfuscation: Look for disguised links, deliberate misspellings, grammar glitches, unnatural formal phrasing.

You MUST respond strictly with a valid JSON object matching this schema:
{
  "manipulation_score": <int between 0 and 100>,
  "manipulation_category": "<NONE | LOW | MODERATE | SEVERE | EXTREME>",
  "primary_tactic": "<e.g., False Urgency, Authority Impersonation, Financial Greed, Coercive Intimidation, Legitimate Notice>",
  "detected_triggers": [
    {
      "trigger": "<Name of tactic>",
      "quote": "<Exact phrase from message demonstrating this>",
      "psychological_intent": "<Why scammers use this on human cognition>"
    }
  ],
  "cognitive_assessment": "<2-3 sentence clinical breakdown of the psychological vectors in this message>",
  "target_vulnerability": "<Who is most susceptible: e.g., elderly, job seekers, busy professionals, general public>"
}

Do not include any Markdown ticks or text outside the JSON object."""


class PsychologistAgent:
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key or os.getenv("NEBIUS_API_KEY", "")
        self.base_url = base_url or os.getenv("NEBIUS_BASE_URL", "https://api.studio.nebius.com/v1/")
        # Use Nemotron Ultra 70B for heavy reasoning
        self.model = model or os.getenv("NEMOTRON_ULTRA", "nvidia/Llama-3.1-Nemotron-70B-Instruct-HF")
        self.client = None
        if self.api_key and self.api_key != "your_nebius_api_key_here":
            try:
                self.client = OpenAI(
                    base_url=self.base_url,
                    api_key=self.api_key,
                )
            except Exception as e:
                logger.warning(f"Failed to initialize Nebius OpenAI client: {e}")

    async def analyze(self, text: str, investigator_context: str = "") -> Dict[str, Any]:
        """
        Deploy Nemotron Ultra 70B to deconstruct behavioral manipulation vectors.
        """
        user_prompt = f"""Evaluate this suspicious message:
----------------------------------------
{text}
----------------------------------------

Cyber Threat Investigator Telemetry:
{investigator_context if investigator_context else "No prior telemetry available."}

Conduct a deep psychological & linguistic analysis. Return ONLY the specified JSON."""

        if self.client:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": PSYCHOLOGIST_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.2,
                    max_tokens=800,
                )
                raw_content = response.choices[0].message.content.strip()
                # Parse JSON, handling potential markdown wrappers
                clean_json = raw_content
                if clean_json.startswith("```json"):
                    clean_json = clean_json[7:]
                if clean_json.startswith("```"):
                    clean_json = clean_json[3:]
                if clean_json.endswith("```"):
                    clean_json = clean_json[:-3]
                clean_json = clean_json.strip()

                parsed = json.loads(clean_json)
                parsed["agent"] = "Cognitive Psychologist (Nemotron Ultra 70B)"
                parsed["model_used"] = self.model
                parsed["inference_provider"] = "Nebius Token Factory"
                return parsed

            except Exception as e:
                logger.error(f"Error calling Nemotron Ultra 70B via Nebius: {e}")

        # Intelligent offline fallback if Nebius API key is pending or network fails
        return self._heuristic_analysis(text)

    def _heuristic_analysis(self, text: str) -> Dict[str, Any]:
        """Rule-based psychological heuristic fallback for testing & resilience."""
        lower = text.lower()
        score = 15
        triggers = []
        tactic = "Informational"

        urgency_words = ["immediately", "urgent", "within 24 hours", "suspended", "action required", "expires", "final notice", "terminated", "blocked"]
        found_urgency = [w for w in urgency_words if w in lower]
        if found_urgency:
            score += 35
            tactic = "Manufactured Urgency & Panic"
            triggers.append({
                "trigger": "Artificial Time Constraint",
                "quote": f"Keywords: {', '.join(found_urgency)}",
                "psychological_intent": "Forces fast, emotional decisions to circumvent the victim's critical reasoning faculties."
            })

        fear_words = ["arrest", "police", "legal action", "court", "fraud", "penalty", "warrant", "jail", "compromised"]
        found_fear = [w for w in fear_words if w in lower]
        if found_fear:
            score += 40
            tactic = "Coercive Intimidation & Fear"
            triggers.append({
                "trigger": "Threat of Severe Consequence",
                "quote": f"Keywords: {', '.join(found_fear)}",
                "psychological_intent": "Triggers flight-or-fight response, overriding skepticism."
            })

        greed_words = ["won", "lottery", "claim prize", "free crypto", "exclusive bonus", "part-time job", "earn daily", "guaranteed return"]
        found_greed = [w for w in greed_words if w in lower]
        if found_greed:
            score += 30
            tactic = "Reward & Financial Baiting"
            triggers.append({
                "trigger": "Unearned Reward Hook",
                "quote": f"Keywords: {', '.join(found_greed)}",
                "psychological_intent": "Exploits natural human optimism and financial aspiration."
            })

        score = min(score, 98)
        category = "SEVERE" if score >= 75 else ("MODERATE" if score >= 45 else "LOW")

        return {
            "agent": "Cognitive Psychologist (Offline Heuristic Fallback)",
            "model_used": "Heuristic Behavioral Engine",
            "inference_provider": "Local Defense Runtime",
            "manipulation_score": score,
            "manipulation_category": category,
            "primary_tactic": tactic,
            "detected_triggers": triggers or [{
                "trigger": "Baseline Communication",
                "quote": text[:60],
                "psychological_intent": "Standard informational tone with low coercive pressure."
            }],
            "cognitive_assessment": f"Evaluated communication exhibits {category.lower()} manipulative intensity, primarily leveraging {tactic.lower()}.",
            "target_vulnerability": "General recipients, especially mobile users susceptible to quick push-notification reactions."
        }
