"""
ScamShield Multi-Agent Autonomous Defense Framework
Contains:
  - InvestigatorAgent: Live web threat telemetry & fraud database verification (Tavily API)
  - PsychologistAgent: Cognitive manipulation & social engineering analysis (Nemotron Ultra 70B)
  - JudgeAgent: Adversarial deliberation, risk scoring & defensive action planning (Nemotron Nano 8B)
"""

from .investigator import InvestigatorAgent
from .psychologist import PsychologistAgent
from .judge import JudgeAgent

__all__ = ["InvestigatorAgent", "PsychologistAgent", "JudgeAgent"]
