/* -------------------------------------------------------------
   ScamShield — Frontend Controller & SSE Stream Handler
   Nebius x NVIDIA Global AI Hackathon
------------------------------------------------------------- */

document.addEventListener("DOMContentLoaded", () => {
  // UI Elements
  const scamInput = document.getElementById("scamInput");
  const analyzeBtn = document.getElementById("analyzeBtn");
  const pasteBtn = document.getElementById("pasteBtn");
  const clearBtn = document.getElementById("clearBtn");
  const benchmarkButtons = document.getElementById("benchmarkButtons");
  
  // Investigation Section
  const investigationSection = document.getElementById("investigationSection");
  const terminalLogs = document.getElementById("terminalLogs");
  
  // Agent Cards & Status
  const cardInv = document.getElementById("agentCardInvestigator");
  const statusInv = document.getElementById("statusInv");
  const outputInv = document.getElementById("outputInv");
  
  const cardPsych = document.getElementById("agentCardPsychologist");
  const statusPsych = document.getElementById("statusPsych");
  const outputPsych = document.getElementById("outputPsych");
  
  const cardJudge = document.getElementById("agentCardJudge");
  const statusJudge = document.getElementById("statusJudge");
  const outputJudge = document.getElementById("outputJudge");
  
  // Results Section
  const resultsSection = document.getElementById("resultsSection");
  const verdictBanner = document.getElementById("verdictBanner");
  const verdictBadge = document.getElementById("verdictBadge");
  const verdictTitle = document.getElementById("verdictTitle");
  const verdictSummary = document.getElementById("verdictSummary");
  const riskScoreEl = document.getElementById("riskScore");
  const confidenceLevelEl = document.getElementById("confidenceLevel");
  const redFlagsList = document.getElementById("redFlagsList");
  const psychInsightContent = document.getElementById("psychInsightContent");
  const actionPlanList = document.getElementById("actionPlanList");
  const counterResponseText = document.getElementById("counterResponseText");
  const copyResponseBtn = document.getElementById("copyResponseBtn");
  const sourcesCard = document.getElementById("sourcesCard");
  const sourcesGrid = document.getElementById("sourcesGrid");

  let examplesData = [];
  let currentEventSource = null;

  // Load benchmark examples from backend
  async function loadExamples() {
    try {
      const res = await fetch("/api/examples");
      const data = await res.json();
      examplesData = data.examples || [];
      
      // Wire up click handlers for benchmark buttons
      document.querySelectorAll(".benchmark-btn").forEach(btn => {
        btn.addEventListener("click", () => {
          const id = btn.getAttribute("data-id");
          const ex = examplesData.find(e => e.id === id);
          if (ex) {
            scamInput.value = ex.text;
            scamInput.focus();
            // Scroll slightly to input
            scamInput.scrollIntoView({ behavior: "smooth", block: "center" });
          }
        });
      });
    } catch (e) {
      console.warn("Could not load examples from API:", e);
    }
  }

  // Paste from clipboard
  pasteBtn.addEventListener("click", async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        scamInput.value = text;
      }
    } catch (err) {
      alert("Clipboard access denied or unsupported in this browser. Please paste with Ctrl+V.");
    }
  });

  // Clear input
  clearBtn.addEventListener("click", () => {
    scamInput.value = "";
    scamInput.focus();
  });

  // Copy safe counter-response
  copyResponseBtn.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(counterResponseText.textContent.trim());
      const originalText = copyResponseBtn.textContent;
      copyResponseBtn.textContent = "Copied!";
      setTimeout(() => {
        copyResponseBtn.textContent = originalText;
      }, 2000);
    } catch (err) {
      console.error("Copy failed", err);
    }
  });

  // Append a log line to terminal
  function appendTerminal(agentName, message) {
    const timeStr = new Date().toLocaleTimeString([], { hour12: false });
    const line = document.createElement("div");
    line.className = "terminal-line";
    line.innerHTML = `<span class="t-stamp">[${timeStr}]</span><span class="t-agent">${agentName ? `[${agentName}]` : ''}</span>${message}`;
    terminalLogs.appendChild(line);
    terminalLogs.scrollTop = terminalLogs.scrollHeight;
  }

  // Reset agent card states
  function resetInvestigationUI() {
    investigationSection.classList.remove("hidden");
    resultsSection.classList.add("hidden");
    terminalLogs.innerHTML = "";

    // Reset Agent 1
    cardInv.className = "agent-card";
    statusInv.className = "agent-status";
    statusInv.textContent = "Standby";
    outputInv.textContent = "Waiting for telemetry dispatch...";

    // Reset Agent 2
    cardPsych.className = "agent-card";
    statusPsych.className = "agent-status";
    statusPsych.textContent = "Standby";
    outputPsych.textContent = "Awaiting forensic context...";

    // Reset Agent 3
    cardJudge.className = "agent-card";
    statusJudge.className = "agent-status";
    statusJudge.textContent = "Standby";
    outputJudge.textContent = "Waiting for deliberation phase...";
  }

  // Handle main analyze button click
  analyzeBtn.addEventListener("click", async () => {
    const text = scamInput.value.trim();
    if (!text || text.length < 5) {
      alert("Please enter or paste suspicious message text or a URL to investigate.");
      scamInput.focus();
      return;
    }

    if (currentEventSource) {
      currentEventSource.close();
      currentEventSource = null;
    }

    // Set UI to running
    analyzeBtn.disabled = true;
    analyzeBtn.querySelector(".btn-text").textContent = "Investigating...";
    resetInvestigationUI();

    try {
      appendTerminal("SYSTEM", "Initiating ScamShield Autonomous Defense Pipeline...");
      
      // POST to start job
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: text })
      });

      if (!res.ok) {
        throw new Error(`Server returned ${res.status}`);
      }

      const { job_id } = await res.json();
      appendTerminal("SYSTEM", `Job #${job_id} assigned. Opening real-time SSE telemetry channel...`);

      // Open SSE stream
      currentEventSource = new EventSource(`/api/jobs/${job_id}/stream`);

      currentEventSource.onmessage = (e) => {
        // Generic messages
      };

      // Handle specific event types
      currentEventSource.addEventListener("investigator_started", (e) => {
        const payload = JSON.parse(e.data);
        cardInv.classList.add("active");
        statusInv.className = "agent-status running";
        statusInv.textContent = "Scanning";
        outputInv.textContent = "Extracting URLs, domains, phone numbers, and brand signatures...";
        appendTerminal("INVESTIGATOR", payload.message);
      });

      currentEventSource.addEventListener("entities_extracted", (e) => {
        const payload = JSON.parse(e.data);
        appendTerminal("INVESTIGATOR", payload.message);
      });

      currentEventSource.addEventListener("tavily_search_dispatched", (e) => {
        const payload = JSON.parse(e.data);
        outputInv.textContent = "Querying live Tavily threat feeds & anti-phishing databases...";
        appendTerminal("TAVILY_API", payload.message);
      });

      currentEventSource.addEventListener("investigator_complete", (e) => {
        const payload = JSON.parse(e.data);
        cardInv.classList.remove("active");
        cardInv.classList.add("completed");
        statusInv.className = "agent-status done";
        statusInv.textContent = "Complete";

        const invResult = payload.data?.investigator_result || {};
        outputInv.textContent = `Threat Level: [${invResult.threat_level || 'EVALUATED'}]. Found ${invResult.scam_reports_found?.length || 0} threat hits and ${invResult.external_sources?.length || 0} live sources.`;
        appendTerminal("INVESTIGATOR", payload.message);
      });

      currentEventSource.addEventListener("psychologist_started", (e) => {
        const payload = JSON.parse(e.data);
        cardPsych.classList.add("active");
        statusPsych.className = "agent-status running";
        statusPsych.textContent = "Profiling";
        outputPsych.textContent = "Nemotron Ultra 70B deconstructing psychological levers and social engineering hooks...";
        appendTerminal("PSYCHOLOGIST", payload.message);
      });

      currentEventSource.addEventListener("psychologist_complete", (e) => {
        const payload = JSON.parse(e.data);
        cardPsych.classList.remove("active");
        cardPsych.classList.add("completed");
        statusPsych.className = "agent-status done";
        statusPsych.textContent = "Complete";

        const psychResult = payload.data?.psychologist_result || {};
        outputPsych.textContent = `Manipulation: ${psychResult.manipulation_score || 0}/100 (${psychResult.manipulation_category || 'N/A'})\nPrimary Tactic: ${psychResult.primary_tactic || 'Analyzed'}`;
        appendTerminal("PSYCHOLOGIST", payload.message);
      });

      currentEventSource.addEventListener("judge_started", (e) => {
        const payload = JSON.parse(e.data);
        cardJudge.classList.add("active");
        statusJudge.className = "agent-status running";
        statusJudge.textContent = "Deliberating";
        outputJudge.textContent = "Nemotron Nano 8B synthesizing forensic dossier into unified verdict & defense plan...";
        appendTerminal("JUDGE", payload.message);
      });

      currentEventSource.addEventListener("judge_complete", (e) => {
        const payload = JSON.parse(e.data);
        cardJudge.classList.remove("active");
        cardJudge.classList.add("completed");
        statusJudge.className = "agent-status done";
        statusJudge.textContent = "Ruling Issued";

        const judgeResult = payload.data?.judge_result || {};
        outputJudge.textContent = `Verdict: ${judgeResult.verdict || 'DONE'}\nRisk: ${judgeResult.risk_score || 0}% | Confidence: ${judgeResult.confidence_percent || 0}%`;
        appendTerminal("JUDGE", payload.message);
      });

      currentEventSource.addEventListener("pipeline_finished", (e) => {
        const payload = JSON.parse(e.data);
        appendTerminal("SYSTEM", payload.message);
      });

      currentEventSource.addEventListener("done", (e) => {
        const payload = JSON.parse(e.data);
        currentEventSource.close();
        currentEventSource = null;

        analyzeBtn.disabled = false;
        analyzeBtn.querySelector(".btn-text").textContent = "Investigate Threats";

        if (payload.status === "completed" && payload.result) {
          renderResults(payload.result);
        } else {
          alert("Investigation failed: " + (payload.error || "Unknown error"));
        }
      });

      currentEventSource.onerror = (err) => {
        console.error("SSE stream error:", err);
        appendTerminal("ERROR", "SSE connection dropped or terminated.");
        analyzeBtn.disabled = false;
        analyzeBtn.querySelector(".btn-text").textContent = "Investigate Threats";
        if (currentEventSource) {
          currentEventSource.close();
          currentEventSource = null;
        }
      };

    } catch (err) {
      console.error(err);
      alert("Error starting investigation: " + err.message);
      analyzeBtn.disabled = false;
      analyzeBtn.querySelector(".btn-text").textContent = "Investigate Threats";
    }
  });

  // Render the Final Results Dashboard
  function renderResults(result) {
    resultsSection.classList.remove("hidden");

    const verdict = (result.verdict || "SUSPICIOUS").toUpperCase();
    const risk = result.risk_score !== undefined ? result.risk_score : 50;
    const confidence = result.confidence_percent || 85;

    // Reset banner class
    verdictBanner.className = "verdict-banner";
    if (verdict.includes("SCAM") || risk >= 75) {
      verdictBanner.classList.add("verdict-scam");
      verdictBadge.textContent = "🚨 CONFIRMED SCAM";
      verdictTitle.textContent = "High Risk Fraud Vector Detected";
    } else if (verdict.includes("SUSPICIOUS") || risk >= 40) {
      verdictBanner.classList.add("verdict-suspicious");
      verdictBadge.textContent = "⚠️ SUSPICIOUS / HIGH CAUTION";
      verdictTitle.textContent = "Anomalies & Social Engineering Signals Present";
    } else {
      verdictBanner.classList.add("verdict-safe");
      verdictBadge.textContent = "✅ LIKELY LEGITIMATE / SAFE";
      verdictTitle.textContent = "No Critical Threat Signatures Found";
    }

    verdictSummary.textContent = result.executive_summary || "Autonomous investigation complete.";
    riskScoreEl.textContent = risk;
    confidenceLevelEl.textContent = `Confidence: ${confidence}%`;

    // Red Flags
    redFlagsList.innerHTML = "";
    const redFlags = result.top_red_flags || [];
    if (redFlags.length === 0) {
      const li = document.createElement("li");
      li.className = "red-flag-item";
      li.textContent = "No prominent threat indicators discovered.";
      redFlagsList.appendChild(li);
    } else {
      redFlags.forEach(flag => {
        const li = document.createElement("li");
        li.className = "red-flag-item";
        li.textContent = flag;
        redFlagsList.appendChild(li);
      });
    }

    // Cognitive Psychologist insight
    const psych = result.psychologist || {};
    if (psych.cognitive_assessment) {
      psychInsightContent.innerHTML = `<strong>Tactic:</strong> ${psych.primary_tactic || 'General'}<br>${psych.cognitive_assessment}`;
    } else {
      psychInsightContent.textContent = "Standard psychological baseline observed.";
    }

    // Defensive Action Plan
    actionPlanList.innerHTML = "";
    const actions = result.action_plan || [];
    actions.forEach(action => {
      const li = document.createElement("li");
      li.textContent = action;
      actionPlanList.appendChild(li);
    });

    // Safe Counter-Response
    if (result.safe_counter_response) {
      counterResponseText.textContent = `"${result.safe_counter_response}"`;
    }

    // Live Tavily Citations
    const sources = result.investigator?.external_sources || [];
    sourcesGrid.innerHTML = "";
    if (sources.length > 0) {
      sourcesCard.classList.remove("hidden");
      sources.slice(0, 6).forEach(src => {
        const item = document.createElement("div");
        item.className = "source-item";
        item.innerHTML = `
          <a href="${src.url}" target="_blank" rel="noopener noreferrer" class="source-title-link">
            ${src.title || src.url}
          </a>
          <p class="source-snippet">${src.snippet || ''}</p>
        `;
        sourcesGrid.appendChild(item);
      });
    } else {
      sourcesCard.classList.add("hidden");
    }

    // Scroll smoothly to results
    resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // Initialize
  loadExamples();
});
