// =========================================================
//  HealthSync AI — script.js
// =========================================================

document.addEventListener("DOMContentLoaded", function () {

  const submitBtn       = document.getElementById("submit-btn");
  const symptomInput    = document.getElementById("symptom-input");
  const responseSection = document.getElementById("response-section");
  const responseMessage = document.getElementById("response-message");
  const responseIcon    = responseSection.querySelector(".response-icon");


  submitBtn.addEventListener("click", function () {

  const userInput = symptomInput.value.trim();

    // Step 1: Validate input immediately
    if (userInput === "") {
      showResponse(
        "error",
        "⚠",
        "Please describe your symptoms before submitting."
      );
      return;
    }

    // Step 2: Show loading state immediately
    submitBtn.disabled = true;

    submitBtn.querySelector(".btn-text").textContent =
      "Analyzing...";

    submitBtn.querySelector(".btn-icon").textContent =
      "⏳";


    try {

  const response = await fetch(
    "http://127.0.0.1:8000/analyze",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        symptoms: userInput
      })
    }
  );

  const data = await response.json();

  console.log(data);

} catch (error) {
  console.error(error);
}gi

    // Step 3: Simulate AI processing
    

      showResponse(
        "success",
        "✓",
        `
        <h3>AI Assessment</h3>

        <p><strong>Possible Condition:</strong> Common Cold</p>

        <p><strong>Severity:</strong> Low</p>

        <p><strong>Recommendations:</strong></p>

        <ul>
          <li>Drink plenty of fluids</li>
          <li>Get adequate rest</li>
          <li>Monitor symptoms</li>
        </ul>
        `
      );

      // Reset button
      submitBtn.disabled = false;

      submitBtn.querySelector(".btn-text").textContent =
        "Analyze Symptoms";

      submitBtn.querySelector(".btn-icon").textContent =
        "→";

    }, 2000);

  });


  // =========================================================
  //  Helper Function
  // =========================================================

  function showResponse(type, icon, message) {

    responseSection.classList.remove("success", "error");
    responseSection.classList.add(type);

    responseIcon.textContent = icon;

    responseMessage.innerHTML = message;

    responseSection.removeAttribute("hidden");
  }

});