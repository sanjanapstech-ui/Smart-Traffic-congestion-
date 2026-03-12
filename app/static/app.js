const qs = (sel) => document.querySelector(sel);

function setButtonActive(btn, active, activeClass) {
  btn.classList.remove("tab-btn-active-predict", "tab-btn-active-route");
  btn.classList.toggle(activeClass, active);
  btn.classList.toggle("tab-btn-inactive", !active);
}

function animateSwap(showEl, hideEl) {
  if (hideEl && !hideEl.classList.contains("hidden")) {
    const a = hideEl.animate(
      [
        { opacity: 1, transform: "translateY(0px)" },
        { opacity: 0, transform: "translateY(10px)" },
      ],
      { duration: 200, easing: "ease-in" },
    );
    a.finished
      .then(() => hideEl.classList.add("hidden"))
      .catch(() => hideEl.classList.add("hidden"));
  }

  if (showEl && showEl.classList.contains("hidden")) {
    showEl.classList.remove("hidden");
    showEl.animate(
      [
        { opacity: 0, transform: "translateY(10px)" },
        { opacity: 1, transform: "translateY(0px)" },
      ],
      { duration: 240, easing: "cubic-bezier(0.2, 0.9, 0.2, 1)" },
    );
  }
}

function setTab(active) {
  const predictBtn = qs("#tab-predict");
  const routeBtn = qs("#tab-route");
  const predictPanel = qs("#panel-predict");
  const routePanel = qs("#panel-route");

  if (active === "predict") {
    setButtonActive(predictBtn, true, "tab-btn-active-predict");
    setButtonActive(routeBtn, false, "tab-btn-active-route");
    animateSwap(predictPanel, routePanel);
  } else {
    setButtonActive(routeBtn, true, "tab-btn-active-route");
    setButtonActive(predictBtn, false, "tab-btn-active-predict");
    animateSwap(routePanel, predictPanel);
  }
}

function setChip(el, label) {
  const s = String(label || "").toLowerCase();
  el.classList.remove("chip-low", "chip-moderate", "chip-high");
  if (s.includes("low")) el.classList.add("chip-low");
  else if (s.includes("high")) el.classList.add("chip-high");
  else el.classList.add("chip-moderate");
}

function setLoading(button, loading) {
  if (!button) return;
  const spinner = button.querySelector(".spinner");
  const label = button.querySelector(".btn-label");

  button.disabled = !!loading;
  button.style.opacity = loading ? "0.92" : "";
  button.style.cursor = loading ? "not-allowed" : "";

  if (spinner) spinner.classList.toggle("hidden", !loading);
  if (label) {
    if (!label.dataset.original) label.dataset.original = label.textContent;
    label.textContent = loading ? "Working…" : label.dataset.original;
  }
}

function showStatus(el, msg, kind = "info") {
  const colors = {
    info: "text-slate-700",
    ok: "text-emerald-700",
    err: "text-rose-700",
  };
  el.textContent = msg;
  el.className = `mt-3 text-sm ${colors[kind] || colors.info}`;
}

async function loadGraph() {
  const status = qs("#route-status");
  const sourceSel = qs("#route-source");
  const destSel = qs("#route-destination");

  try {
    const res = await fetch("/api/graph");
    if (!res.ok) throw new Error(`Graph request failed (${res.status})`);
    const data = await res.json();
    const nodes = data.nodes || [];

    for (const sel of [sourceSel, destSel]) {
      sel.innerHTML = "";
      for (const node of nodes) {
        const opt = document.createElement("option");
        opt.value = node;
        opt.textContent = node;
        sel.appendChild(opt);
      }
    }

    if (nodes.length > 1) {
      sourceSel.value = nodes[0];
      destSel.value = nodes[nodes.length - 1];
    }
    showStatus(status, "Ready.", "ok");
  } catch (e) {
    showStatus(
      status,
      "API not ready yet. Start the backend and refresh.",
      "err",
    );
  }
}

async function loadStatusPill() {
  const pill = qs("#backend-pill");
  if (!pill) return;

  const set = (text, cls, title) => {
    pill.textContent = text;
    pill.title = title || "";
    pill.classList.remove(
      "status-pill-loading",
      "status-pill-ok",
      "status-pill-warn",
      "status-pill-err",
    );
    pill.classList.add(cls);
  };

  try {
    const res = await fetch("/api/status");
    if (!res.ok) throw new Error(`Status request failed (${res.status})`);
    const data = await res.json();

    const autoMode = String(data.auto_mode || "demo");

    if (autoMode === "ml") {
      set("ML MODE", "status-pill-ok", "Machine-learning route mode is active.");
    } else {
      set("DEMO", "status-pill-warn", "Showing demo routes.");
    }
  } catch (e) {
    set("OFFLINE", "status-pill-err", "Backend not reachable.");
  }
}

function wirePredict() {
  const form = qs("#predict-form");
  const file = qs("#predict-file");
  const preview = qs("#predict-preview");
  const dropzone = qs("#predict-dropzone");
  const previewEmpty = qs("#predict-preview-empty");
  const status = qs("#predict-status");
  const result = qs("#predict-result");
  const button = qs("#predict-submit");

  function setFileFromDrop(f) {
    if (!f) return;
    try {
      const dt = new DataTransfer();
      dt.items.add(f);
      file.files = dt.files;
    } catch {
      // ignore
    }
    preview.src = URL.createObjectURL(f);
    preview.classList.remove("hidden");
    if (previewEmpty) previewEmpty.classList.add("hidden");
    result.classList.add("hidden");
    status.textContent = "";
  }

  file.addEventListener("change", () => {
    result.classList.add("hidden");
    status.textContent = "";
    const f = file.files?.[0];
    if (!f) return;
    setFileFromDrop(f);
  });

  if (dropzone) {
    const onDrag = (ev) => {
      ev.preventDefault();
      ev.stopPropagation();
    };

    dropzone.addEventListener("dragenter", (ev) => {
      onDrag(ev);
      dropzone.classList.add("drop-active");
    });
    dropzone.addEventListener("dragover", onDrag);
    dropzone.addEventListener("dragleave", (ev) => {
      onDrag(ev);
      dropzone.classList.remove("drop-active");
    });
    dropzone.addEventListener("drop", (ev) => {
      onDrag(ev);
      dropzone.classList.remove("drop-active");
      const f = ev.dataTransfer?.files?.[0];
      if (f) setFileFromDrop(f);
    });

    dropzone.addEventListener("click", () => file.click());
  }

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    result.classList.add("hidden");

    const f = file.files?.[0];
    if (!f) {
      showStatus(status, "Choose an image first.", "err");
      return;
    }

    try {
      setLoading(button, true);
      showStatus(status, "Predicting…", "info");
      const fd = new FormData();
      fd.append("file", f);

      const res = await fetch("/api/predict", { method: "POST", body: fd });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const msg = data?.detail || `Prediction failed (${res.status})`;
        throw new Error(msg);
      }

      const labelEl = qs("#predict-label");
      const label = data.label || "unknown";
      labelEl.textContent = label;
      setChip(labelEl, label);

      result.classList.remove("hidden");
      showStatus(status, "Done.", "ok");
    } catch (e) {
      showStatus(status, String(e.message || e), "err");
    } finally {
      setLoading(button, false);
    }
  });
}

function wireRoute() {
  const form = qs("#route-form");
  const status = qs("#route-status");
  const out = qs("#route-output");
  const button = qs("#route-submit");

  function routeSkeleton() {
    out.innerHTML = `
      <div class="route-summary" aria-hidden="true">
        <div class="skeleton" style="height: 12px; width: 120px;"></div>
        <div class="skeleton" style="height: 22px; width: 100%; margin-top: 12px;"></div>
      </div>
      <div class="route-grid" aria-hidden="true">
        ${Array.from({ length: 6 })
          .map(
            () => `
            <div class="route-node-card">
              <div class="skeleton" style="height: 120px; width: 120px; border-radius: 0.9rem;"></div>
              <div style="flex: 1; padding-top: 2px;">
                <div class="skeleton" style="height: 14px; width: 55%; border-radius: 10px;"></div>
                <div class="skeleton" style="height: 12px; width: 38%; margin-top: 10px; border-radius: 10px;"></div>
                <div class="skeleton" style="height: 10px; width: 85%; margin-top: 12px; border-radius: 10px;"></div>
              </div>
            </div>
          `,
          )
          .join("")}
      </div>
    `;
  }

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    out.innerHTML = "";

    const source = qs("#route-source").value;
    const destination = qs("#route-destination").value;
    if (!source || !destination || source === destination) {
      showStatus(status, "Pick different source and destination.", "err");
      return;
    }

    try {
      setLoading(button, true);
      showStatus(status, "Computing best route…", "info");
      routeSkeleton();
      const res = await fetch("/api/route", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source, destination }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const msg = data?.detail || `Route failed (${res.status})`;
        throw new Error(msg);
      }

      out.innerHTML = "";

      const path = data.path || [];
      const nodes = data.nodes || [];

      const pathEl = document.createElement("div");
      pathEl.className = "route-summary";
      pathEl.innerHTML = `
        <div style="font-size: 11px; font-weight: 900; letter-spacing: 0.12em; color: rgba(15,23,42,0.55);">
          BEST ROUTE
        </div>
        <div style="margin-top: 10px; font-size: 16px; font-weight: 700; color: rgba(15,23,42,0.95); line-height: 1.35;">
          ${path
            .map((x) => `<span style="font-weight: 800;">${x}</span>`)
            .join(
              '<span style="margin: 0 10px; color: rgba(100,116,139,0.75);">→</span>',
            )}
        </div>
      `;
      out.appendChild(pathEl);

      const head = document.createElement("div");
      head.className = "route-heading";
      head.innerHTML = `<span class="route-heading-icon">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 7h18"/>
            <path d="M3 12h18"/>
            <path d="M3 17h18"/>
          </svg>
        </span>
        IMAGE PREVIEW FOR ROUTE NODES`;
      out.appendChild(head);

      const grid = document.createElement("div");
      grid.className = "route-grid";

      nodes.forEach((n, idx) => {
        const t = String(n.traffic || "moderate").toLowerCase();
        const cardTint =
          t === "low"
            ? "route-card-low"
            : t === "high"
              ? "route-card-high"
              : "route-card-moderate";
        const card = document.createElement("div");
        card.className = `route-node-card hover-lift ${cardTint}`;

        const img = document.createElement("img");
        img.className = "route-node-img";
        img.src = n.image_data_url || "";
        img.alt = n.name || "node image";

        const meta = document.createElement("div");
        const label = String(n.traffic || "unknown").toUpperCase();
        const chip =
          t === "low"
            ? "chip-low"
            : t === "high"
              ? "chip-high"
              : "chip-moderate";
        meta.innerHTML = `
          <div class="route-node-top">
            <span class="route-node-step">${idx + 1}</span>
            <div class="route-node-name">${n.name}</div>
          </div>
          <div style="margin-top: 10px;"><span class="chip ${chip} text-xs">${label}</span></div>
        `;

        card.appendChild(img);
        card.appendChild(meta);
        grid.appendChild(card);
      });

      out.appendChild(grid);
      showStatus(status, "Done.", "ok");
    } catch (e) {
      showStatus(status, String(e.message || e), "err");
      out.innerHTML = "";
    } finally {
      setLoading(button, false);
    }
  });
}

qs("#tab-predict").addEventListener("click", () => setTab("predict"));
qs("#tab-route").addEventListener("click", () => setTab("route"));

setTab("predict");
wirePredict();
wireRoute();
loadGraph();
loadStatusPill();

try {
  window.startParticles?.(document.getElementById("particles"));
} catch {}
