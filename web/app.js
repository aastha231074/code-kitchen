// Plain JS, no build step -- deliberately simple for a lab/demo frontend.
// All calls go through app-api (the BFF); this file never talks to ai-api
// or referral-api directly.

function currentEmail() {
  return document.getElementById("user-email").value.trim();
}

async function api(path, options = {}) {
  const resp = await fetch(`${window.APP_API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-User-Email": currentEmail(),
      ...(options.headers || {}),
    },
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`${resp.status} ${resp.statusText}: ${text}`);
  }
  if (resp.status === 204) return null;
  return resp.json();
}

// ---- tabs ----
document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
  });
});

// ---- profile ----
async function loadProfile() {
  try {
    const data = await api("/profile");
    const p = data.profile || {};
    document.getElementById("profile-skills").value = (p.skills || []).join(", ");
    document.getElementById("profile-experience").value = p.experience || "";
    document.getElementById("profile-preferences").value = p.preferences || "";
    document.getElementById("profile-location").value = p.location || "";
  } catch (e) {
    console.warn("no profile yet", e);
  }
}

document.getElementById("save-profile").addEventListener("click", async () => {
  const status = document.getElementById("profile-status");
  status.textContent = "Saving...";
  try {
    await api("/profile", {
      method: "PUT",
      body: JSON.stringify({
        skills: document.getElementById("profile-skills").value.split(",").map((s) => s.trim()).filter(Boolean),
        experience: document.getElementById("profile-experience").value,
        preferences: document.getElementById("profile-preferences").value,
        location: document.getElementById("profile-location").value,
      }),
    });
    status.textContent = "Saved.";
  } catch (e) {
    status.textContent = `Error: ${e.message}`;
  }
});

// ---- matches ----
document.getElementById("run-match").addEventListener("click", async () => {
  const status = document.getElementById("match-status");
  const list = document.getElementById("matches-list");
  status.textContent = "Matching (vector pre-filter + Gemini Flash)...";
  list.innerHTML = "";
  try {
    const data = await api("/match", { method: "POST", body: JSON.stringify({ top_n: 10 }) });
    status.textContent = `${data.matches.length} matches (query took ${data.query_latency_ms}ms)`;
    data.matches.forEach((m) => list.appendChild(renderMatchCard(m)));
  } catch (e) {
    status.textContent = `Error: ${e.message}`;
  }
});

function renderMatchCard(m) {
  const card = document.createElement("div");
  card.className = "card";
  card.innerHTML = `
    <h4>${m.title} -- ${m.company}</h4>
    <div class="meta">${m.location || "Location n/a"} &middot; similarity ${m.similarity.toFixed(3)}</div>
    <div class="rationale">${m.rationale}</div>
    <div class="row">
      <button data-job-id="${m.job_id}" data-job-title="${m.title}" class="gen-resume">Generate resume &amp; outreach</button>
      <button data-company="${m.company}" data-job-id="${m.job_id}" class="find-referral secondary">Find a referral contact</button>
    </div>
  `;
  card.querySelector(".gen-resume").addEventListener("click", (e) => onGenerate(e.target.dataset.jobId, e.target.dataset.jobTitle));
  card.querySelector(".find-referral").addEventListener("click", (e) => onFindReferral(e.target.dataset.company, e.target.dataset.jobId));
  return card;
}

async function onGenerate(jobId, jobTitle) {
  try {
    const data = await api("/generate", { method: "POST", body: JSON.stringify({ job_id: jobId }) });
    document.getElementById("generate-title").textContent = jobTitle;
    document.getElementById("generate-resume").value = data.resume;
    document.getElementById("generate-outreach").value = data.outreach_message;
    document.getElementById("generate-modal").classList.remove("hidden");
  } catch (e) {
    alert(`Error generating: ${e.message}`);
  }
}
document.getElementById("generate-close").addEventListener("click", () => {
  document.getElementById("generate-modal").classList.add("hidden");
});

async function onFindReferral(company, jobId) {
  try {
    await api("/referral/lookup", { method: "POST", body: JSON.stringify({ company, job_id: jobId }) });
    alert(`Found a contact at ${company} -- check the Outreach tab to review before sending.`);
  } catch (e) {
    alert(`Error: ${e.message}`);
  }
}

// ---- applications ----
async function loadApplications() {
  const list = document.getElementById("applications-list");
  list.innerHTML = "";
  const data = await api("/applications");
  data.applications.forEach((a) => {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <h4>${a.title} -- ${a.company}</h4>
      <div class="meta">${a.location || ""}</div>
      <span class="pill ${a.status}">${a.status}</span>
      <div class="row">
        ${a.status === "draft" ? `<button data-id="${a.id}" class="mark-applied">Mark as applied</button>` : ""}
      </div>
    `;
    const btn = card.querySelector(".mark-applied");
    if (btn) {
      btn.addEventListener("click", async () => {
        await api(`/applications/${a.id}/status`, { method: "POST", body: JSON.stringify({ status: "applied" }) });
        loadApplications();
      });
    }
    list.appendChild(card);
  });
}
document.getElementById("refresh-applications").addEventListener("click", loadApplications);

// ---- outreach ----
async function loadOutreach() {
  const list = document.getElementById("outreach-list");
  list.innerHTML = "";
  const data = await api("/outreach");
  data.outreach.forEach((o) => {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <h4>${o.title || "General outreach"} ${o.company ? "-- " + o.company : ""}</h4>
      <span class="pill ${o.status}">${o.status.replace("_", " ")}</span>
      <p>${o.message}</p>
      <div class="row">
        ${o.status === "pending_review" ? `
          <button data-id="${o.id}" class="approve">Approve &amp; send</button>
          <button data-id="${o.id}" class="decline danger">Decline</button>
        ` : ""}
      </div>
    `;
    const approveBtn = card.querySelector(".approve");
    if (approveBtn) approveBtn.addEventListener("click", async () => { await api(`/outreach/${o.id}/approve`, { method: "POST" }); loadOutreach(); });
    const declineBtn = card.querySelector(".decline");
    if (declineBtn) declineBtn.addEventListener("click", async () => { await api(`/outreach/${o.id}/decline`, { method: "POST" }); loadOutreach(); });
    list.appendChild(card);
  });
}
document.getElementById("refresh-outreach").addEventListener("click", loadOutreach);

// ---- init ----
loadProfile();
loadApplications();
loadOutreach();
