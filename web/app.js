(() => {
  const topicEl = document.getElementById("topic");
  const runBtn = document.getElementById("run-btn");
  const statusLine = document.getElementById("status-line");
  const errorBanner = document.getElementById("error-banner");
  const pipelineFlow = document.getElementById("pipeline-flow");
  const eventsSection = document.getElementById("events-section");
  const eventsList = document.getElementById("events-list");
  const toggleEvents = document.getElementById("toggle-events");
  const reportSection = document.getElementById("report-section");
  const reportTopic = document.getElementById("report-topic");
  const reportBody = document.getElementById("report-body");
  const sourcesSection = document.getElementById("sources-section");
  const sourcesList = document.getElementById("sources-list");
  const navNew = document.getElementById("nav-new");

  const DEFAULT_TOPIC =
    "How is generative AI changing software engineering jobs and developer productivity in 2026?";

  function esc(text) {
    return String(text ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function domainFromUrl(url) {
    try {
      return new URL(url).hostname.replace(/^www\./, "");
    } catch {
      return "";
    }
  }

  function showError(message) {
    errorBanner.textContent = message;
    errorBanner.classList.remove("hidden");
  }

  function clearError() {
    errorBanner.textContent = "";
    errorBanner.classList.add("hidden");
  }

  function agentCompleted(events, agentName) {
    return events.some((e) => e.agent === agentName && e.status === "completed");
  }

  function agentErrored(events, agentName) {
    return events.some((e) => e.agent === agentName && e.status === "error");
  }

  function agentRunning(events, agentName) {
    if (!events.length) return false;
    if (agentCompleted(events, agentName) || agentErrored(events, agentName)) return false;
    return events.some((e) => e.agent === agentName);
  }

  function statusInfo(events, agentName, hasArtifact) {
    if (agentErrored(events, agentName)) return { text: "Error", cls: "error" };
    if (agentCompleted(events, agentName) || hasArtifact) return { text: "Complete", cls: "done" };
    if (agentRunning(events, agentName)) return { text: "Running", cls: "running" };
    return { text: "Idle", cls: "idle" };
  }

  function citeChips(ids) {
    if (!ids || !ids.length) return "";
    return `<div class="cite-chips">${ids
      .map((id) => `<a class="cite-chip" href="#source-${esc(id)}">[${esc(id)}]</a>`)
      .join("")}</div>`;
  }

  function agentCard({ num, name, role, meta, status }) {
    return `
      <article class="agent-card ${status.cls}">
        <div class="agent-card-top">
          <span class="agent-num">${esc(num)}</span>
        </div>
        <h3 class="agent-name">${esc(name)}</h3>
        <p class="agent-role">${esc(role)}</p>
        ${meta ? `<div class="agent-meta">${esc(meta)}</div>` : `<div class="agent-meta">—</div>`}
        <div class="agent-status ${status.cls}">
          <span class="dot" aria-hidden="true"></span>
          ${esc(status.text)}
        </div>
      </article>
    `;
  }

  function handoffBlock(label, meta) {
    return `
      <div class="handoff" aria-label="${esc(label)} handoff">
        <div class="handoff-line"></div>
        <div class="handoff-pill">${esc(label)}</div>
        ${meta ? `<div class="handoff-meta">${esc(meta)}</div>` : ""}
        <span class="handoff-arrow">→</span>
      </div>
    `;
  }

  function renderPipeline(payload) {
    const events = payload?.events || [];
    const rp = payload?.research_packet || null;
    const ap = payload?.analysis_packet || null;
    const report = payload?.final_report || null;
    const hasRun = !!(events.length || rp || ap || report);

    const researchStatus = statusInfo(events, "Research Agent", !!rp);
    const analysisStatus = statusInfo(events, "Analysis Agent", !!ap);
    const reportStatus = statusInfo(events, "Report Agent", !!report);

    const queryCount = rp?.search_queries?.length ?? null;
    const sourceCount = rp?.sources?.length ?? null;
    const findingCount = ap?.findings?.length ?? null;
    const conflictCount = ap?.conflicts?.length ?? null;

    let researchRole = "Live web search";
    let researchMeta = hasRun ? "" : "Awaiting topic";
    if (queryCount != null && sourceCount != null) {
      researchMeta = `${queryCount} quer${queryCount === 1 ? "y" : "ies"} · ${sourceCount} source${sourceCount === 1 ? "" : "s"}`;
    }

    let analysisRole = "Evidence review";
    let analysisMeta = hasRun && !ap ? "Awaiting ResearchPacket" : hasRun ? "" : "Standby";
    if (findingCount != null && conflictCount != null) {
      analysisMeta = `${findingCount} finding${findingCount === 1 ? "" : "s"} · ${conflictCount} conflict${conflictCount === 1 ? "" : "s"}`;
    }

    let reportRole = "Synthesis";
    let reportMeta = hasRun && !report ? "Awaiting AnalysisPacket" : hasRun ? "" : "Standby";
    if (report) {
      const sectionN = report.sections?.length ?? 0;
      reportMeta = sectionN ? `${sectionN} section${sectionN === 1 ? "" : "s"} · Final report` : "Final report";
    }

    const parts = [];

    parts.push(
      agentCard({
        num: "01",
        name: "Research Agent",
        role: researchRole,
        meta: researchMeta,
        status: researchStatus,
      })
    );

    if (rp) {
      parts.push(handoffBlock("ResearchPacket", `${sourceCount} sources`));
    } else {
      parts.push(`
        <div class="handoff">
          <div class="handoff-line"></div>
          <div class="handoff-pill">ResearchPacket</div>
          <div class="handoff-meta">${hasRun ? "pending" : "structured handoff"}</div>
          <span class="handoff-arrow">→</span>
        </div>
      `);
    }

    parts.push(
      agentCard({
        num: "02",
        name: "Analysis Agent",
        role: analysisRole,
        meta: analysisMeta,
        status: analysisStatus,
      })
    );

    if (ap) {
      parts.push(
        handoffBlock(
          "AnalysisPacket",
          `${findingCount} findings · ${conflictCount} conflicts`
        )
      );
    } else {
      parts.push(`
        <div class="handoff">
          <div class="handoff-line"></div>
          <div class="handoff-pill">AnalysisPacket</div>
          <div class="handoff-meta">${hasRun ? "pending" : "structured handoff"}</div>
          <span class="handoff-arrow">→</span>
        </div>
      `);
    }

    parts.push(
      agentCard({
        num: "03",
        name: "Report Agent",
        role: reportRole,
        meta: reportMeta,
        status: reportStatus,
      })
    );

    pipelineFlow.innerHTML = parts.join("");
  }

  function renderEvents(events) {
    if (!events || !events.length) {
      eventsList.innerHTML = `
        <li>
          <span class="event-check pending">○</span>
          <div>
            <div class="event-agent">System</div>
            <div class="event-step">Waiting for run</div>
            <p class="event-msg">AgentEvents will appear here after orchestration starts.</p>
          </div>
        </li>`;
      eventsSection.classList.remove("hidden");
      return;
    }

    eventsList.innerHTML = events
      .map((e) => {
        const mark =
          e.status === "error" ? "!" : e.status === "completed" || e.status === "started" ? "✓" : "•";
        const cls =
          e.status === "error" ? "error" : e.status === "completed" ? "" : "pending";
        return `
      <li>
        <span class="event-check ${cls}">${mark}</span>
        <div>
          <div class="event-agent">${esc(e.agent)} · ${esc(e.status)}</div>
          <div class="event-step">${esc(e.step)}</div>
          <p class="event-msg">${esc(e.message)}</p>
        </div>
      </li>`;
      })
      .join("");
    eventsSection.classList.remove("hidden");
  }

  function extractCitationIds(text) {
    if (!text) return [];
    const matches = String(text).match(/\[(S\d+)\]/g) || [];
    return [...new Set(matches.map((m) => m.slice(1, -1)))];
  }

  function renderReport(report) {
    if (!report) {
      reportSection.classList.add("hidden");
      return;
    }

    reportTopic.textContent = report.topic || report.title || "Research Report";

    const hasSummary = !!report.executive_summary;
    const hasFindings = !!(report.key_findings && report.key_findings.length);
    const blocks = [];

    if (hasSummary || hasFindings) {
      let left = "";
      let right = "";

      if (hasSummary) {
        left = `
          <div class="report-block cardish">
            <h3>Executive Summary</h3>
            <p>${esc(report.executive_summary)}</p>
          </div>`;
      }

      if (hasFindings) {
        const items = report.key_findings
          .map((finding, i) => {
            const cites = extractCitationIds(finding);
            return `
              <div class="finding-item">
                <div class="finding-num">${String(i + 1).padStart(2, "0")}</div>
                <div>
                  <p class="finding-text">${esc(finding)}</p>
                  ${citeChips(cites)}
                </div>
              </div>`;
          })
          .join("");
        right = `
          <div class="report-block cardish">
            <h3>Key Findings</h3>
            ${items}
          </div>`;
      } else {
        right = `
          <div class="report-block cardish">
            <h3>Key Findings</h3>
            <p class="empty-note">No key_findings returned in this FinalReport.</p>
          </div>`;
      }

      if (!hasSummary) {
        left = `
          <div class="report-block cardish">
            <h3>Executive Summary</h3>
            <p class="empty-note">No executive_summary returned in this FinalReport.</p>
          </div>`;
      }

      blocks.push(`<div class="report-grid">${left}${right}</div>`);
    }

    if (report.sections && report.sections.length) {
      report.sections.forEach((sec) => {
        blocks.push(`
          <div class="report-block">
            <h3>${esc(sec.heading)}</h3>
            <p class="section-content">${esc(sec.content)}</p>
            ${citeChips(sec.citations || [])}
          </div>
        `);
      });
    }

    if (report.conflict_analysis && report.conflict_analysis.length) {
      const conflicts = report.conflict_analysis
        .map(
          (c) => `
        <div class="conflict-card">
          <p class="conflict-topic">${esc(c.topic)}</p>
          <p class="conflict-side"><strong>Viewpoint A</strong> ${citeChips(c.side_a_sources || [])}<br>${esc(c.side_a)}</p>
          <p class="conflict-side"><strong>Viewpoint B</strong> ${citeChips(c.side_b_sources || [])}<br>${esc(c.side_b)}</p>
          ${c.resolution_or_assessment ? `<p class="conflict-assess">${esc(c.resolution_or_assessment)}</p>` : ""}
        </div>`
        )
        .join("");
      blocks.push(`
        <div class="report-block">
          <h3>Evidence &amp; Conflicts</h3>
          ${conflicts}
        </div>
      `);
    }

    const conclusions = report.conclusions?.length
      ? report.conclusions
      : report.conclusion
        ? [report.conclusion]
        : [];
    if (conclusions.length) {
      blocks.push(`
        <div class="report-block">
          <h3>Conclusions</h3>
          <ul class="plain-list">${conclusions.map((c) => `<li>${esc(c)}</li>`).join("")}</ul>
        </div>
      `);
    }

    if (report.recommendations && report.recommendations.length) {
      blocks.push(`
        <div class="report-block">
          <h3>Recommendations</h3>
          <ul class="plain-list">${report.recommendations.map((r) => `<li>${esc(r)}</li>`).join("")}</ul>
        </div>
      `);
    }

    if (report.limitations && report.limitations.length) {
      blocks.push(`
        <div class="report-block">
          <h3>Limitations</h3>
          <ul class="plain-list">${report.limitations.map((l) => `<li>${esc(l)}</li>`).join("")}</ul>
        </div>
      `);
    }

    reportBody.innerHTML = blocks.join("") || `<p class="empty-note">Report received with no renderable fields.</p>`;
    reportSection.classList.remove("hidden");
  }

  function renderSources(sources) {
    if (!sources || !sources.length) {
      sourcesSection.classList.add("hidden");
      return;
    }

    sourcesList.innerHTML = sources
      .map((s) => {
        const domain = domainFromUrl(s.url);
        const date = s.published_date ? ` · ${esc(s.published_date)}` : "";
        return `
        <article class="source-item" id="source-${esc(s.id)}">
          <div class="source-id">${esc(s.id)}</div>
          <div>
            <h3 class="source-title">${esc(s.title)}</h3>
            <div class="source-meta">${esc(domain)}${date}</div>
            ${s.snippet ? `<p class="source-snippet">${esc(s.snippet)}</p>` : ""}
          </div>
          <a class="source-link" href="${esc(s.url)}" target="_blank" rel="noopener noreferrer" title="${esc(s.url)}">↗ Open</a>
        </article>`;
      })
      .join("");

    sourcesSection.classList.remove("hidden");
  }

  function resetResults() {
    reportSection.classList.add("hidden");
    sourcesSection.classList.add("hidden");
    reportBody.innerHTML = "";
    sourcesList.innerHTML = "";
    renderPipeline(null);
    renderEvents([]);
  }

  function focusNewResearch() {
    resetResults();
    clearError();
    statusLine.textContent = "Ready";
    topicEl.focus();
  }

  async function runResearch() {
    const topic = (topicEl.value || "").trim() || DEFAULT_TOPIC;
    topicEl.value = topic;

    clearError();
    reportSection.classList.add("hidden");
    sourcesSection.classList.add("hidden");
    reportBody.innerHTML = "";
    sourcesList.innerHTML = "";

    runBtn.disabled = true;
    statusLine.textContent = "Running pipeline…";
    renderPipeline(null);
    renderEvents([]);

    try {
      const res = await fetch("/api/research", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic }),
      });

      const payload = await res.json();

      renderPipeline(payload);
      renderEvents(payload.events || []);

      if (!payload.success) {
        showError(payload.error || "Pipeline failed. Please retry.");
        statusLine.textContent = "Failed — retry available";
        if (payload.research_packet?.sources) {
          renderSources(payload.research_packet.sources);
        }
        return;
      }

      renderReport(payload.final_report);
      const sources =
        payload.final_report?.sources?.length
          ? payload.final_report.sources
          : payload.research_packet?.sources || [];
      renderSources(sources);
      statusLine.textContent = "Pipeline complete";
    } catch (err) {
      showError(err.message || "Network error contacting the research server.");
      statusLine.textContent = "Request failed — retry";
      renderPipeline(null);
      renderEvents([]);
    } finally {
      runBtn.disabled = false;
    }
  }

  toggleEvents?.addEventListener("click", () => {
    const collapsed = eventsSection.classList.toggle("collapsed");
    toggleEvents.textContent = collapsed ? "Expand" : "Collapse";
    toggleEvents.setAttribute("aria-expanded", collapsed ? "false" : "true");
  });

  navNew?.addEventListener("click", focusNewResearch);
  runBtn.addEventListener("click", runResearch);
  topicEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      runResearch();
    }
  });

  // Idle application state — no fake research data
  renderPipeline(null);
  renderEvents([]);
})();
