// =========================================================
//  HealthSync AI — script.js
//  Handles form interaction and prepares for FastAPI backend
// =========================================================

// ===== Step 1: Wait for the DOM to fully load =====
document.addEventListener("DOMContentLoaded", function () {

  // ===== Step 2: Grab references to key HTML elements =====
  const submitBtn       = document.getElementById("submit-btn");
  const symptomInput    = document.getElementById("symptom-input");
  const responseSection = document.getElementById("response-section");
  const responseMessage = document.getElementById("response-message");
  const responseIcon    = responseSection.querySelector(".response-icon");


  // ===== Step 3: Listen for the submit button click =====
  submitBtn.addEventListener("click", function () {

    // Step 4: Read and trim the textarea value
    const userInput = symptomInput.value.trim();

    // Step 5: Prevent empty submissions
    if (userInput === "") {
      showResponse(
        "error",
        "⚠",
        "Please describe your symptoms before submitting."
      );
      return;
    }

    // Step 6: Show a success message
    showResponse(
      "success",
      "✓",
      "Your symptoms have been received. Analyzing your input — please wait..."
    );

    // Step 7: Send to FastAPI backend (uncomment when ready)
    // sendToBackend(userInput);

  });


  // =========================================================
  //  Helper: showResponse
  // =========================================================
  function showResponse(type, icon, message) {
    responseSection.classList.remove("success", "error");
    responseSection.classList.add(type);
    responseIcon.textContent    = icon;
    responseMessage.textContent = message;
    responseSection.removeAttribute("hidden");
  }


  // =========================================================
  //  FastAPI Integration — uncomment when backend is ready
  // =========================================================

  /*
  async function sendToBackend(inputText) {
    showResponse("success", "⏳", "Connecting to HealthSync AI backend...");

    try {
      const response = await fetch("http://127.0.0.1:8000/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symptoms: inputText })
      });

      const data = await response.json();
      showResponse("success", "✓", data.result || "Analysis complete.");

    } catch (error) {
      console.error("Backend error:", error);
      showResponse("error", "✗", "Could not reach the server. Please try again later.");
    }
  }
  */

}); // end DOMContentLoaded