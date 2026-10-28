"""
ScamShield — Cyber Threat Investigator Agent
Powered by Tavily Search API

Responsibilities:
  1. Parse candidate threat vectors (domains, URLs, phone numbers, brands, financial claims).
  2. Execute live runtime threat intelligence queries against live fraud registries,
     anti-phishing databases, domain reputation trackers, and community scam reports.
  3. Aggregate concrete external evidence with source citations for downstream agents.
"""

import os
import re
import logging
from typing import Dict, Any, List
from urllib.parse import urlparse

logger = logging.getLogger("scamshield.investigator")

# Common brands often impersonated
KNOWN_TARGETS = [
    "usps", "fedex", "ups", "dhl", "amazon", "paypal", "netflix",
    "apple", "microsoft", "google", "geek squad", "chase", "bank of america",
    "wells fargo", "citibank", "sbi", "hdfc", "icici", "irs", "hmrc",
    "binance", "coinbase", "metamask", "whatsapp", "telegram", "facebook"
]

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

    def extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract URLs, domains, phone numbers, email addresses, and brand names."""
        # URL detection (http/https or naked domains)
        url_pattern = r'(https?://[^\s<>"]+|www\.[^\s<>"]+|(?:[a-zA-Z0-9-]+\.)+(?:xyz|top|online|site|club|work|vip|buzz|live|cc|info|me|co|io|app|biz|ru|cn)[^\s<>"]*)'
        raw_urls = re.findall(url_pattern, text, re.IGNORECASE)
        
        cleaned_urls = []
        domains = set()
        for u in raw_urls:
            cleaned = u.rstrip(".,;!?:)'\"")
            cleaned_urls.append(cleaned)
            # extract domain
            parsed = urlparse(cleaned if "://" in cleaned else f"http://{cleaned}")
            netloc = parsed.netloc or parsed.path.split('/')[0]
            if netloc:
                domains.add(netloc.lower())

        # Phone numbers (various formats)
        phone_pattern = r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\+?\d{10,14}'
        phones = list(set(re.findall(phone_pattern, text)))

        # Email addresses
        email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
        emails = list(set(re.findall(email_pattern, text)))

        # Brand / Impersonation detection
        lower_text = text.lower()
        impersonated_brands = [b for b in KNOWN_TARGETS if b in lower_text]

        # Financial keywords
        financial_patterns = ["crypto", "bitcoin", "usdt", "gift card", "wire transfer", "upi", "kyc", "otp", "routing number", "ssn", "wallet"]
        found_financial = [k for k in financial_patterns if k in lower_text]

        return {
            "urls": cleaned_urls,
            "domains": list(domains),
            "phones": phones,
            "emails": emails,
            "brands": impersonated_brands,
            "financial_hooks": found_financial
        }

    async def investigate(self, text: str) -> Dict[str, Any]:
        """
        Conduct deep live runtime threat intelligence research via Tavily.
        """
        entities = self.extract_entities(text)
        queries = []
        
        # Build smart targeted search queries
        if entities["domains"]:
            for dom in entities["domains"][:2]:
                queries.append(f'"{dom}" scam phishing fraud malware reputation')
        
        if entities["phones"]:
            for ph in entities["phones"][:2]:
                queries.append(f'"{ph}" scam fraud spam robocall report')

        if entities["brands"]:
            brand_str = " ".join(entities["brands"][:2])
            # extract first 8-10 words of the text as context hook
            snippet = " ".join(text.split()[:8]).replace('"', '')
            queries.append(f'{brand_str} scam "{snippet}" fake notice')
        else:
            snippet = " ".join(text.split()[:10]).replace('"', '')
            queries.append(f'scam message text "{snippet}" fraud report')

        # Limit to max 3 targeted queries to optimize response latency and credits
        queries = queries[:3]
        
        sources = []
        scam_reports = []
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
                    
                    if response.get("answer"):
                        scam_reports.append({
                            "query": q,
                            "summary": response["answer"],
                            "source": "Tavily AI Synthesized Threat Intelligence"
                        })

                    for item in response.get("results", []):
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
                        
                        # Identify clear scam indicators in search results
                        scam_keywords = ["scam", "phishing", "fraud", "fake", "malicious", "warning", "complaint", "imposter", "spoof"]
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
                heuristic_flags.append(f"Suspicious unverified links: {', '.join(entities['urls'])}")
            if entities["brands"] and ("click" in text.lower() or "urgent" in text.lower() or "verify" in text.lower()):
                heuristic_flags.append(f"Classic brand impersonation signature targeting {', '.join(entities['brands']).title()}")
            if entities["financial_hooks"]:
                heuristic_flags.append(f"Financial pressure indicators: {', '.join(entities['financial_hooks'])}")
            
            scam_reports.append({
                "source_title": "Local Threat Signature Engine (Heuristic)",
                "source_url": "offline://heuristics",
                "indicators": heuristic_flags or ["No known threat database hits"],
                "evidence": "TAVILY_API_KEY not configured or offline. Ran local threat signature heuristics."
            })

        # Calculate threat score contribution from investigator
        threat_level = "LOW"
        if len(scam_reports) >= 2 or (entities["domains"] and any(d.endswith(('.xyz', '.top', '.club', '.buzz', '.vip')) for d in entities["domains"])):
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
            "external_sources": sources,
            "evidence_summary": self._format_evidence_summary(entities, scam_reports, sources, is_live_tavily)
        }

    def _format_evidence_summary(self, entities: Dict, reports: List, sources: List, is_live: bool) -> str:
        lines = []
        lines.append(f"Live Intelligence Mode: {'Active (Tavily Runtime API)' if is_live else 'Offline Heuristics'}")
        if entities['domains']:
            lines.append(f"Target Domains: {', '.join(entities['domains'])}")
        if entities['phones']:
            lines.append(f"Suspicious Numbers: {', '.join(entities['phones'])}")
        if entities['brands']:
            lines.append(f"Impersonated Entities: {', '.join(entities['brands']).title()}")
        if entities['financial_hooks']:
            lines.append(f"Financial Triggers: {', '.join(entities['financial_hooks'])}")
        
        lines.append(f"Total Scam Database / Public Report Matches: {len(reports)}")
        for i, r in enumerate(reports[:3], 1):
            if "summary" in r:
                lines.append(f"  [{i}] {r['summary']}")
            elif "evidence" in r:
                lines.append(f"  [{i}] {r.get('source_title', 'Report')}: {r['evidence']}")
        
        return "\n".join(lines)
