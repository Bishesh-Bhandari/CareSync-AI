// =========================================================
//  HealthSync AI — script.js
//  Used ONLY by dashboard.html
//
//  Flow:
//    1. Page loads → check token → GET /auth/me
//       ✓ valid  → show user name, load history
//       ✗ invalid → redirect to login.html
//    2. User types symptoms → clicks Analyze
//       → POST /analyze  (token in Authorization header)
//       → show AI result
//       → reload history
// =========================================================

const API = "http://127.0.0.1:8000";

// ── Get stored token ──────────────────────────────────────
function getToken() {
  return localStorage.getItem("hs_token");
}

// ── Auth headers — every authenticated request needs this ─
function authHeaders() {
  return {
    "Content-Type":  "application/json",
    "Authorization": "Bearer " + getToken(),
  };
}

// ── Escape user-supplied strings before inserting into HTML ──
function esc(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// =========================================================
//  Step 1 — on page load: verify token with /auth/me
// =========================================================
document.addEventListener("DOMContentLoaded", async function () {

  const token = getToken();

  // No token at all → go to login immediately
  if (!token) {
    window.location.href = "login.html";
    return;
  }

  try {
    // Ask the server if this token is still valid
    const res = await fetch(API + "/auth/me", {
      headers: authHeaders(),
    });

    if (!res.ok) {
      // Token expired or invalid → clear storage and redirect
      localStorage.clear();
      window.location.href = "login.html";
      return;
    }

    const user = await res.json();

    // Show greeting in the top nav
    document.getElementById("user-greeting").innerHTML =
      "Hello, <strong>" + esc(user.first_name) + "</strong>";

    // Load past symptom checks
    loadHistory();

  } catch (err) {
    // Network error — server probably not running
    console.error("Auth check failed:", err);
  }

  // ── Wire up logout button ───────────────────────────────
  document.getElementById("logout-btn").addEventListener("click", function () {
    localStorage.clear();
    window.location.href = "login.html";
  });

  // ── Wire up Analyze button ──────────────────────────────
  wireAnalyzeButton();
});


// =========================================================
//  Step 2 — Analyze button
// =========================================================
function wireAnalyzeButton() {
  const submitBtn       = document.getElementById("submit-btn");
  const symptomInput    = document.getElementById("symptom-input");
  const responseSection = document.getElementById("response-section");
  const responseMessage = document.getElementById("response-message");
  const responseIcon    = responseSection.querySelector(".response-icon");

  function setLoading(on) {
    submitBtn.disabled = on;
    submitBtn.querySelector(".btn-text").textContent = on ? "Analyzing…" : "Analyze Symptoms";
    submitBtn.querySelector(".btn-icon").textContent = on ? "⏳" : "→";
  }

  function showResponse(type, icon, html) {
    responseSection.classList.remove("success", "error");
    responseSection.classList.add(type);
    responseIcon.textContent  = icon;
    responseMessage.innerHTML = html;
    responseSection.removeAttribute("hidden");
  }

  submitBtn.addEventListener("click", async function () {

    const userInput = symptomInput.value.trim();

    if (!userInput) {
      showResponse("error", "⚠", "<p>Please describe your symptoms before submitting.</p>");
      return;
    }

    setLoading(true);

    try {
      // POST /analyze — server checks the token before running the AI
      const res = await fetch(API + "/analyze", {
        method:  "POST",
        headers: authHeaders(),
        body:    JSON.stringify({ symptoms: userInput }),
      });

      if (res.status === 401) {
        // Session expired mid-use
        localStorage.clear();
        window.location.href = "login.html";
        return;
      }

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Server error " + res.status);
      }

      const data = await res.json();

      const condition       = data.condition       ?? "Unknown";
      const severity        = data.severity        ?? "Unknown";
      const recommendations = Array.isArray(data.recommendations)
        ? data.recommendations
        : ["Please consult a healthcare professional."];

      const severityClass =
        severity.toLowerCase() === "high"   ? "severity-high"   :
        severity.toLowerCase() === "medium" ? "severity-medium" : "severity-low";

      showResponse("success", "✓", `
        <h3>AI Assessment</h3>
        <p><strong>Possible condition:</strong> ${esc(condition)}
           <span class="severity-badge ${severityClass}">${esc(severity)}</span>
        </p>
        <p><strong>Recommendations:</strong></p>
        <ul>${recommendations.map(r => "<li>" + esc(r) + "</li>").join("")}</ul>
      `);

      // Refresh the history section so the new log appears immediately
      loadHistory();

    } catch (err) {
      console.error("Analyze error:", err);
      showResponse("error", "✗", `
        <h3>Something went wrong</h3>
        <p>${esc(err.message)}</p>
        <p>Please try again or check that the server is running.</p>
      `);
    } finally {
      setLoading(false);
    }
  });
}


// =========================================================
//  History — GET /history
// =========================================================
async function loadHistory() {
  const historyList  = document.getElementById("history-list");
  const historyEmpty = document.getElementById("history-empty");

  try {
    const res = await fetch(API + "/history", {
      headers: authHeaders(),
    });

    if (!res.ok) return;

    const data = await res.json();
    const logs = data.logs || [];

    if (logs.length === 0) {
      historyEmpty.style.display = "block";
      historyList.innerHTML      = "";
      return;
    }

    historyEmpty.style.display = "none";

    historyList.innerHTML = logs.map(function (log) {
      const severityClass =
        (log.severity || "").toLowerCase() === "high"   ? "severity-high"   :
        (log.severity || "").toLowerCase() === "medium" ? "severity-medium" : "severity-low";

      // Format the date nicely
      const date = new Date(log.created_at);
      const dateStr = isNaN(date)
        ? log.created_at
        : date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });

      return `
        <div class="history-item">
          <div class="history-item-top">
            <span class="history-condition">
              ${esc(log.condition || "Unknown")}
              <span class="severity-badge ${severityClass}">${esc(log.severity || "—")}</span>
            </span>
            <span class="history-date">${esc(dateStr)}</span>
          </div>
          <p class="history-symptoms">${esc(log.symptoms)}</p>
        </div>
      `;
    }).join("");

  } catch (err) {
    console.error("History load failed:", err);
  }
}