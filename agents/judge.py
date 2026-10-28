"""
ScamShield — Judicial Synthesizer & Defense Tactician Agent
Powered by NVIDIA Nemotron Nano 8B via Nebius Token Factory

Responsibilities:
  1. Adversarial deliberation: Corroborate external threat signals (Investigator)
     with behavioral manipulation insights (Psychologist).
  2. Multi-evidence weighted scoring to establish the final Threat Probability Index (0-100%).
  3. Deliver authoritative Verdict (CONFIRMED SCAM / SUSPICIOUS / LIKELY SAFE).
  4. Formulate actionable defensive protocol for the everyday user.
  5. Draft an optional safe counter-response for safe disengagement.
"""

import os
import json
import logging
from typing import Dict, Any
from openai import OpenAI

logger = logging.getLogger("scamshield.judge")

JUDGE_SYSTEM_PROMPT = """You are the Supreme Judicial Arbiter & Defensive Tactician for ScamShield.
You synthesize forensic evidence from the Cyber Investigator (live web threat registries, Tavily data)
and the Cognitive Psychologist (Nemotron Ultra 70B behavioral analysis).

Your task:
1. Synthesize all findings into a definitive verdict:
   - "CONFIRMED SCAM" (Risk Score >= 75): Overwhelming evidence of fraudulent intent, impersonation, or dangerous links.
   - "SUSPICIOUS" (Risk Score 40-74): Significant red flags or unverified sender/links; caution required.
   - "LIKELY SAFE" (Risk Score < 40): Consistent with legitimate, normal organizational communication.
2. Calculate a unified Risk Score (0-100) and Confidence Percentage (50-100%).
3. Write a clear, plain-language Executive Summary for non-technical users (e.g., grandparents, busy consumers).
4. List the Top Red Flags with specific evidence citations.
5. Provide a step-by-step Defensive Action Plan.
6. Provide a Disarming Safe Response (what the user could say if they need to decline/verify safely without leaking info).

You MUST respond strictly with a valid JSON object matching this schema:
{
  "verdict": "<CONFIRMED SCAM | SUSPICIOUS | LIKELY SAFE>",
  "risk_score": <int 0-100>,
  "confidence_percent": <int 50-100>,
  "executive_summary": "<Clear 1-2 sentence explanation of why this message is or isn't a scam>",
  "top_red_flags": [
    "<Concise bullet point 1 with specific evidence>",
    "<Concise bullet point 2 with specific evidence>",
    "<Concise bullet point 3 with specific evidence>"
  ],
  "action_plan": [
    "<Immediate action step 1, e.g. Do not click the link or supply OTP>",
    "<Immediate action step 2, e.g. Block sender and report as spam>",
    "<Immediate action step 3, e.g. Verify directly via official website/app>"
  ],
  "safe_counter_response": "<Safe disarming message template the user can copy/paste if desired>",
  "deliberation_rationale": "<Short technical note on how evidence from Investigator and Psychologist were weighted>"
}

Do not include any Markdown ticks or text outside the JSON object."""


class JudgeAgent:
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key or os.getenv("NEBIUS_API_KEY", "")
        self.base_url = base_url or os.getenv("NEBIUS_BASE_URL", "https://api.studio.nebius.com/v1/")
        # Use Nemotron Nano 8B for fast, cost-effective synthesis
        self.model = model or os.getenv("NEMOTRON_NANO", "nvidia/llama-3.1-nemotron-nano-8b-v1")
        self.client = None
        if self.api_key and self.api_key != "your_nebius_api_key_here":
            try:
                self.client = OpenAI(
                    base_url=self.base_url,
                    api_key=self.api_key,
                )
            except Exception as e:
                logger.warning(f"Failed to initialize Nebius OpenAI client: {e}")

    async def deliberate(self, text: str, investigator_data: Dict[str, Any], psychologist_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synthesize cross-agent intelligence and issue the final ruling using Nemotron Nano 8B.
        """
        investigator_summary = investigator_data.get("evidence_summary", "No telemetry.")
        psych_score = psychologist_data.get("manipulation_score", 0)
        psych_category = psychologist_data.get("manipulation_category", "UNKNOWN")
        psych_tactic = psychologist_data.get("primary_tactic", "None")
        psych_assessment = psychologist_data.get("cognitive_assessment", "None")

        user_prompt = f"""EVIDENCE DOSSIER FOR DELIBERATION:
=============================================================
ORIGINAL SUSPICIOUS CONTENT:
"{text}"

AGENT 1 — CYBER THREAT INVESTIGATOR (Live Web Intelligence):
Threat Level: {investigator_data.get('threat_level', 'UNKNOWN')}
Live Search Active: {investigator_data.get('is_live_search', False)}
Evidence Summary:
{investigator_summary}

AGENT 2 — COGNITIVE PSYCHOLOGIST (Nemotron Ultra 70B Analysis):
Manipulation Score: {psych_score}/100 ({psych_category})
Primary Tactic: {psych_tactic}
Cognitive Assessment: {psych_assessment}
=============================================================

Deliberate on this evidence and output the final verdict strictly in the required JSON format."""

        if self.client:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.1,
                    max_tokens=800,
                )
                raw_content = response.choices[0].message.content.strip()
                clean_json = raw_content
                if clean_json.startswith("```json"):
                    clean_json = clean_json[7:]
                if clean_json.startswith("```"):
                    clean_json = clean_json[3:]
                if clean_json.endswith("```"):
                    clean_json = clean_json[:-3]
                clean_json = clean_json.strip()

                parsed = json.loads(clean_json)
                parsed["agent"] = "Judicial Arbiter (Nemotron Nano 8B)"
                parsed["model_used"] = self.model
                parsed["inference_provider"] = "Nebius Token Factory"
                return parsed

            except Exception as e:
                logger.error(f"Error calling Nemotron Nano 8B via Nebius: {e}")

        # Intelligent offline fallback if Nebius API key is not yet set
        return self._heuristic_deliberation(text, investigator_data, psychologist_data)

    def _heuristic_deliberation(self, text: str, inv_data: Dict, psych_data: Dict) -> Dict[str, Any]:
        """Rule-based synthesis fallback when offline."""
        inv_threat = inv_data.get("threat_level", "LOW")
        psych_score = psych_data.get("manipulation_score", 20)

        # Weighted calculation: 50% threat intelligence + 50% psychological manipulation
        threat_weight = 85 if inv_threat == "HIGH" else (50 if inv_threat == "MEDIUM" else 15)
        combined_score = int((threat_weight * 0.5) + (psych_score * 0.5))

        if combined_score >= 70:
            verdict = "CONFIRMED SCAM"
            confidence = 94
            exec_summary = "This message contains classic digital fraud signatures, impersonating a reputable service to elicit urgent, compromised actions."
        elif combined_score >= 40:
            verdict = "SUSPICIOUS"
            confidence = 82
            exec_summary = "This message displays multiple warning indicators. Do not click unverified links or provide credentials."
        else:
            verdict = "LIKELY SAFE"
            confidence = 88
            exec_summary = "This message appears standard with low manipulative pressure and no matching blacklisted threat signatures."

        red_flags = []
        if inv_data.get("entities_extracted", {}).get("urls"):
            red_flags.append(f"Contains unverified external link(s): {', '.join(inv_data['entities_extracted']['urls'])}")
        if psych_data.get("primary_tactic") and psych_data.get("primary_tactic") != "Informational":
            red_flags.append(f"Employs coercive social engineering: {psych_data['primary_tactic']}")
        if inv_data.get("entities_extracted", {}).get("brands"):
            red_flags.append(f"Likely brand impersonation targeting {', '.join(inv_data['entities_extracted']['brands']).title()}")
        if not red_flags:
            red_flags.append("No critical indicators detected; routine message tone.")

        return {
            "agent": "Judicial Arbiter (Offline Heuristic Fallback)",
            "model_used": "Heuristic Synthesis Engine",
            "inference_provider": "Local Defense Runtime",
            "verdict": verdict,
            "risk_score": combined_score,
            "confidence_percent": confidence,
            "executive_summary": exec_summary,
            "top_red_flags": red_flags,
            "action_plan": [
                "NEVER click on links or open attachments in unsolicited messages.",
                "Verify legitimate status directly by visiting the official organization's website or app independently.",
                "Report this message to your carrier (forward SMS to 7726) and block the sender."
            ],
            "safe_counter_response": "I do not recognize this request. I will reach out to customer service directly through the official website. Do not contact me again.",
            "deliberation_rationale": f"Calculated composite score of {combined_score}/100 from cyber intelligence ({threat_weight}/100) and cognitive pressure ({psych_score}/100)."
        }
