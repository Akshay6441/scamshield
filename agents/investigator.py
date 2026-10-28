"""
ScamShield — Cyber Threat Investigator Agent
Powered by Tavily Search API

Responsibilities:
  1. Parse candidate threat vectors (domains, URLs, phone numbers, brands, financial claims).
  2. Defend against prompt injection attempts before query generation.
  3. Execute live runtime threat intelligence queries against live fraud registries,
     anti-phishing databases, domain reputation trackers, and community scam reports.
  4. Crucial Zero-Day Logic: Differentiate between established institutional domains (e.g. amazon.com)
     and zero-footprint / unindexed disposable links (hallmark of novel zero-day phishing kits).
  5. Regional & India-specific scam vector detection (UPI, KYC, APKs, Bijli/Electricity disconnections).
"""

import os
import re
import logging
from typing import Dict, Any, List
from urllib.parse import urlparse

logger = logging.getLogger("scamshield.investigator")

# Global & Regional brands commonly targeted in phishing & smishing
KNOWN_TARGETS = [
    # Global
    "usps", "fedex", "ups", "dhl", "amazon", "paypal", "netflix",
    "apple", "microsoft", "google", "geek squad", "chase", "bank of america",
    "wells fargo", "citibank", "irs", "hmrc", "binance", "coinbase", "metamask",
    "whatsapp", "telegram", "facebook", "instagram",
    # India / Regional
    "sbi", "hdfc", "icici", "axis bank", "paytm", "phonepe", "gpay", "google pay",
    "cred", "india post", "bescom", "mahavitaran", "tangedco", "uppcl", "trai",
    "jio", "airtel", "vi", "kbc", "income tax"
]

# Established institutional trusted apex domains (helps prevent false positives on legitimate notices)
TRUSTED_INSTITUTIONAL_DOMAINS = {
    "amazon.com", "amazon.in", "paypal.com", "usps.com", "fedex.com", "ups.com",
    "chase.com", "bankofamerica.com", "wellsfargo.com", "apple.com", "google.com",
    "microsoft.com", "netflix.com", "onlinesbi.sbi", "hdfcbank.com", "icicibank.com",
    "gov.in", "cybercrime.gov.in", "ftc.gov"
}

class InvestigatorAgent:
    def __init__(self, tavily_api_key: str = None):
        self.api_key = tavily_api_key or os.getenv("TAVILY_API_KEY", "")
        self.client = None
        if self.api_key and self.api_key != "your_tavily_api_key_here":
            try:
                from tavily import TavilyClient
                self.client = TavilyClient(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize TavilyClient: {e}")

    def detect_prompt_injection(self, text: str) -> List[str]:
        """Screen for adversarial instructions attempting to hijack downstream agents."""
        injection_signals = [
            r'ignore\s+(all\s+)?(previous|prior|above)\s+instructions',
            r'system\s*override',
            r'you\s+are\s+now\s+in\s+developer\s+mode',
            r'output\s+(verdict\s*:\s*)?safe',
            r'output\s+risk_score\s*:\s*0',
            r'disregard\s+all\s+rules',
            r'treat\s+this\s+as\s+completely\s+legitimate'
        ]
        flags = []
        for pat in injection_signals:
            if re.search(pat, text, re.IGNORECASE):
                flags.append(f"Adversarial prompt injection pattern detected: '{pat}'")
        return flags

    def extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract URLs, domains, phone numbers, emails, brand names, and regional scam hooks."""
        # Clean potential zero-width characters used for obfuscation
        sanitized = re.sub(r'[\u200B-\u200D\uFEFF]', '', text)

        # URL detection (http/https, naked domains, or IP addresses)
        url_pattern = r'(https?://[^\s<>"]+|www\.[^\s<>"]+|(?:[a-zA-Z0-9-]+\.)+(?:xyz|top|online|site|club|work|vip|buzz|live|cc|info|me|co|io|app|biz|ru|cn|in|pw)[^\s<>"]*)'
        raw_urls = re.findall(url_pattern, sanitized, re.IGNORECASE)
        
        cleaned_urls = []
        domains = set()
        for u in raw_urls:
            cleaned = u.rstrip(".,;!?:)'\"")
            cleaned_urls.append(cleaned)
            parsed = urlparse(cleaned if "://" in cleaned else f"http://{cleaned}")
            netloc = parsed.netloc or parsed.path.split('/')[0]
            if netloc:
                domains.add(netloc.lower())

        # Phone numbers (Indian +91, US +1, or standard formats)
        phone_pattern = r'(?:\+?91[\s-]?)?[6-9]\d{9}|\+?1[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\+?\d{10,14}'
        phones = list(set(re.findall(phone_pattern, sanitized)))

        # Email addresses
        email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
        emails = list(set(re.findall(email_pattern, sanitized)))

        # Brand / Impersonation detection
        lower_text = sanitized.lower()
        impersonated_brands = [b for b in KNOWN_TARGETS if b in lower_text]

        # Financial & Social Engineering hooks (Global & Indian contexts)
        financial_patterns = [
            "crypto", "bitcoin", "usdt", "gift card", "wire transfer",
            "upi", "upi pin", "kyc", "otp", "pan card", "aadhaar", "routing number",
            "apk", "bijli", "electricity bill", "disconnect", "cut jayega", "lottery", "kbc",
            "challan", "part-time job", "youtube rating", "processing fee", "refund"
        ]
        found_hooks = [k for k in financial_patterns if k in lower_text]

        # Check prompt injection canary
        injection_flags = self.detect_prompt_injection(sanitized)

        return {
            "urls": cleaned_urls,
            "domains": list(domains),
            "phones": phones,
            "emails": emails,
            "brands": impersonated_brands,
            "financial_hooks": found_hooks,
            "prompt_injection_flags": injection_flags
        }

    async def investigate(self, text: str) -> Dict[str, Any]:
        """
        Conduct deep live runtime threat intelligence research via Tavily Search API.
        """
        entities = self.extract_entities(text)
        queries = []
        
        # Build targeted search queries
        if entities["domains"]:
            for dom in entities["domains"][:2]:
                queries.append(f'"{dom}" scam phishing fraud malware reputation')
        
        if entities["phones"]:
            for ph in entities["phones"][:2]:
                queries.append(f'"{ph}" scam fraud spam robocall complaint report')

        if entities["brands"]:
            brand_str = " ".join(entities["brands"][:2])
            snippet = " ".join(text.split()[:8]).replace('"', '')
            queries.append(f'{brand_str} scam "{snippet}" fake notice alert')
        else:
            snippet = " ".join(text.split()[:10]).replace('"', '')
            queries.append(f'scam message text "{snippet}" fraud report')

        queries = queries[:3]
        
        sources = []
        scam_reports = []
        zero_day_alerts = []
        is_live_tavily = False

        if self.client:
            for q in queries:
                try:
                    response = self.client.search(
                        query=q,
                        search_depth="advanced",
                        max_results=3,
                        include_answer=True
                    )
                    is_live_tavily = True
                    results_list = response.get("results", [])

                    # CRITICAL ZERO-DAY LOGIC:
                    # If Tavily finds zero results for a domain or phone number, that does NOT mean safe.
                    if not results_list and ("phishing" in q or "robocall" in q):
                        target_entity = q.split('"')[1] if '"' in q else q
                        # Check if it's NOT an established domain
                        if not any(trusted in target_entity for trusted in TRUSTED_INSTITUTIONAL_DOMAINS):
                            zero_day_alerts.append({
                                "entity": target_entity,
                                "warning": "UNINDEXED_ANOMALY: No legitimate institutional presence or indexed corporate history found. Classic indicator of a novel zero-day phishing kit or burner phone infrastructure."
                            })

                    if response.get("answer"):
                        scam_reports.append({
                            "query": q,
                            "summary": response["answer"],
                            "source": "Tavily AI Synthesized Threat Intelligence"
                        })

                    for item in results_list:
                        title = item.get("title", "")
                        content = item.get("content", "").strip()
                        url = item.get("url", "")
                        score = item.get("score", 0.0)
                        
                        sources.append({
                            "title": title,
                            "url": url,
                            "snippet": content[:240] + "..." if len(content) > 240 else content,
                            "relevance": score
                        })
                        
                        scam_keywords = ["scam", "phishing", "fraud", "fake", "malicious", "warning", "complaint", "imposter", "spoof", "apk", "cheating", "cybercrime"]
                        found_indicators = [kw for kw in scam_keywords if kw in title.lower() or kw in content.lower()]
                        if found_indicators:
                            scam_reports.append({
                                "source_title": title,
                                "source_url": url,
                                "indicators": found_indicators,
                                "evidence": content[:200]
                            })
                except Exception as e:
                    logger.error(f"Error querying Tavily with '{q}': {e}")
        else:
            # Offline / Heuristic fallback when Tavily key is unpopulated
            is_live_tavily = False
            heuristic_flags = []
            if entities["urls"]:
                heuristic_flags.append(f"Unverified external link(s): {', '.join(entities['urls'])}")
            if entities["brands"] and ("click" in text.lower() or "urgent" in text.lower() or "verify" in text.lower() or "update" in text.lower()):
                heuristic_flags.append(f"Classic brand impersonation signature targeting {', '.join(entities['brands']).title()}")
            if entities["financial_hooks"]:
                heuristic_flags.append(f"Financial pressure/threat triggers: {', '.join(entities['financial_hooks'])}")
            
            scam_reports.append({
                "source_title": "Local Threat Signature Engine (Heuristic)",
                "source_url": "offline://heuristics",
                "indicators": heuristic_flags or ["No known threat database hits"],
                "evidence": "TAVILY_API_KEY not configured or offline. Ran local threat heuristics."
            })

        # Calculate threat score contribution from investigator
        threat_level = "LOW"
        has_suspicious_domain = entities["domains"] and any(d.endswith(('.xyz', '.top', '.club', '.buzz', '.vip', '.online', '.site', '.live')) for d in entities["domains"])
        has_apk = "apk" in entities["financial_hooks"]
        
        if len(scam_reports) >= 2 or has_suspicious_domain or has_apk or len(zero_day_alerts) >= 1 or entities["prompt_injection_flags"]:
            threat_level = "HIGH"
        elif len(scam_reports) == 1 or entities["brands"]:
            threat_level = "MEDIUM"

        return {
            "agent": "Cyber Threat Investigator",
            "is_live_search": is_live_tavily,
            "entities_extracted": entities,
            "queries_executed": queries,
            "threat_level": threat_level,
            "scam_reports_found": scam_reports,
            "zero_day_alerts": zero_day_alerts,
            "external_sources": sources,
            "evidence_summary": self._format_evidence_summary(entities, scam_reports, zero_day_alerts, sources, is_live_tavily)
        }

    def _format_evidence_summary(self, entities: Dict, reports: List, zero_days: List, sources: List, is_live: bool) -> str:
        lines = []
        lines.append(f"Live Intelligence Mode: {'Active (Tavily Runtime API)' if is_live else 'Offline Heuristics'}")
        if entities['prompt_injection_flags']:
            lines.append(f"HOSTILE INPUT ALERT: {', '.join(entities['prompt_injection_flags'])}")
        if entities['domains']:
            lines.append(f"Target Domains: {', '.join(entities['domains'])}")
        if entities['phones']:
            lines.append(f"Suspicious Numbers: {', '.join(entities['phones'])}")
        if entities['brands']:
            lines.append(f"Impersonated Entities: {', '.join(entities['brands']).title()}")
        if entities['financial_hooks']:
            lines.append(f"Financial / Social Vectors: {', '.join(entities['financial_hooks'])}")
        
        if zero_days:
            for zd in zero_days:
                lines.append(f"  [ZERO-DAY ALERT] {zd['entity']}: {zd['warning']}")

        lines.append(f"Scam Database / Public Report Matches: {len(reports)}")
        for i, r in enumerate(reports[:3], 1):
            if "summary" in r:
                lines.append(f"  [{i}] {r['summary']}")
            elif "evidence" in r:
                lines.append(f"  [{i}] {r.get('source_title', 'Report')}: {r['evidence']}")
        
        return "\n".join(lines)
