function checkNews() {
    let textObj = document.getElementById("news");
    let text = textObj.value.trim();

    if (!text) {
        alert("Please enter some text to analyze.");
        return;
    }

    // UI States: Loading
    const btn = document.getElementById("check-btn");
    const btnText = btn.querySelector(".btn-text");
    const btnLoader = btn.querySelector(".btn-loader");
    const resultContainer = document.getElementById("result-container");
    const resultTitle = document.getElementById("result-title");
    const resultConfidence = document.getElementById("result-confidence");
    const resultIcon = document.getElementById("result-icon");

    btn.disabled = true;
    btnText.classList.add("hidden");
    btnLoader.classList.remove("hidden");
    resultContainer.classList.add("hidden");
    resultContainer.classList.remove("real", "fake");

    fetch("http://127.0.0.1:5000/predict", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ text: text })
    })
    .then(response => {
        if(!response.ok) throw new Error("Network response was not ok");
        return response.json();
    })
    .then(data => {
        // Safe check for data prediction. E.g if prediction string includes fake
        const isFake = data.prediction && data.prediction.toString().toLowerCase().includes("fake");

        // Restore UI
        btn.disabled = false;
        btnText.classList.remove("hidden");
        btnLoader.classList.add("hidden");
        
        // Handle result
        resultContainer.classList.remove("hidden");
        
        if (isFake) {
            resultContainer.classList.add("fake");
            resultIcon.innerHTML = `<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>`;
            resultTitle.innerText = "Fake News Detected";
        } else {
            resultContainer.classList.add("real");
            resultIcon.innerHTML = `<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>`;
            resultTitle.innerText = "Real News Detected";
        }

        resultConfidence.innerText = `Confidence Score: ${data.confidence}`;
    })
    .catch(error => {
        console.error("Error:", error);
        
        // Restore UI on error
        btn.disabled = false;
        btnText.classList.remove("hidden");
        btnLoader.classList.add("hidden");
        
        // Show error visually
        resultContainer.classList.remove("hidden");
        resultContainer.classList.add("fake"); // Reuse fake stylings for red danger color
        resultIcon.innerHTML = `<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>`;
        resultTitle.innerText = "Analysis Error";
        resultConfidence.innerText = "Failed to reach the server. Make sure the backend is running.";
    });
}

document.addEventListener("DOMContentLoaded", () => {
    fetchFakeSources();
});

function fetchFakeSources() {
    fetch("http://127.0.0.1:5000/fake_sources")
        .then(response => response.json())
        .then(data => {
            const container = document.getElementById("sources-list");
            container.innerHTML = "";
            if (data.success && data.top_sources.length > 0) {
                data.top_sources.forEach(source => {
                    const chip = document.createElement("div");
                    chip.className = "source-chip";
                    chip.innerHTML = `<span>${source.domain}</span> <span class="badge">${source.count}</span>`;
                    container.appendChild(chip);
                });
            } else {
                container.innerHTML = "<p>No sources found.</p>";
            }
        })
        .catch(err => {
            document.getElementById("sources-list").innerHTML = "<p style='color:var(--danger)'>Failed to load sources. Ensure the backend is running.</p>";
        });
}