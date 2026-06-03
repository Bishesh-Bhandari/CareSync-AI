// =========================================================
//  HealthSync AI — script.js  (fixed + improved)
// =========================================================

document.addEventListener("DOMContentLoaded", function () {

  const submitBtn       = document.getElementById("submit-btn");
  const symptomInput    = document.getElementById("symptom-input");
  const responseSection = document.getElementById("response-section");
  const responseMessage = document.getElementById("response-message");
  const responseIcon    = responseSection.querySelector(".response-icon");

  // -------------------------------------------------------
  //  Button state helpers  (DRY – avoids repetition)
  // -------------------------------------------------------
  function setButtonLoading() {
    submitBtn.disabled = true;
    submitBtn.querySelector(".btn-text").textContent = "Analyzing...";
    submitBtn.querySelector(".btn-icon").textContent = "⏳";
  }

  function resetButton() {
    submitBtn.disabled = false;
    submitBtn.querySelector(".btn-text").textContent = "Analyze Symptoms";
    submitBtn.querySelector(".btn-icon").textContent = "→";
  }

  // -------------------------------------------------------
  //  Main click handler
  // -------------------------------------------------------
  submitBtn.addEventListener("click", async function () {

    const userInput = symptomInput.value.trim();

    // ── Step 1: Validate input ──────────────────────────
    if (userInput === "") {
      showResponse(
        "error",
        "⚠",
        "Please describe your symptoms before submitting."
      );
      return;
    }

    // ── Step 2: Enter loading state ─────────────────────
    setButtonLoading();

    // ── Step 3: Call the API ────────────────────────────
    try {
      const response = await fetch("http://127.0.0.1:8000/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symptoms: userInput }),
      });

      // Bug fix #5 — treat non-2xx responses as errors
      if (!response.ok) {
        const errText = await response.text();
        throw new Error(`Server error ${response.status}: ${errText}`);
      }

      const data = await response.json();

      // Bug fix #3 — actually USE the data from the API
      const condition      = data.condition      ?? "Unknown";
      const severity       = data.severity       ?? "Unknown";
      const recommendations = Array.isArray(data.recommendations)
        ? data.recommendations
        : ["Please consult a healthcare professional."];

      showResponse(
        "success",
        "✓",
        `
        <h3>AI Assessment</h3>
        <p><strong>Possible Condition:</strong> ${escapeHtml(condition)}</p>
        <p><strong>Severity:</strong> ${escapeHtml(severity)}</p>
        <p><strong>Recommendations:</strong></p>
        <ul>
          ${recommendations.map(r => `<li>${escapeHtml(r)}</li>`).join("")}
        </ul>
        `
      );

    } catch (error) {
      // Bug fix #4 — button always resets, even on error
      console.error("HealthSync API error:", error);
      showResponse(
        "error",
        "✗",
        `
        <h3>Something went wrong</h3>
        <p>${escapeHtml(error.message)}</p>
        <p>Please try again or contact support if the problem persists.</p>
        `
      );
    } finally {
      // Bug fix #4 — runs whether the request succeeded or failed
      resetButton();
    }
  });


  // =========================================================
  //  Helper: render the response card
  // =========================================================
  function showResponse(type, icon, message) {
    responseSection.classList.remove("success", "error");
    responseSection.classList.add(type);

    responseIcon.textContent  = icon;
    responseMessage.innerHTML = message;

    responseSection.removeAttribute("hidden");
  }


  // =========================================================
  //  Helper: prevent XSS when inserting API strings into HTML
  // =========================================================
  function escapeHtml(str) {
    return String(str)
      .replace(/&/g,  "&amp;")
      .replace(/</g,  "&lt;")
      .replace(/>/g,  "&gt;")
      .replace(/"/g,  "&quot;")
      .replace(/'/g,  "&#39;");
  }

});
