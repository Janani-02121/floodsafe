/*
route.js
Handles the start/destination dropdowns and calls the
/api/calculate-route endpoint, then displays the result.
*/

let allLocations = [];
let allShelters = [];

async function loadDropdownData() {
    allLocations = await fetch("/api/locations").then(r => r.json());
    allShelters = await fetch("/api/shelters").then(r => r.json());

    populateSelect("startSelect", document.getElementById("startType").value);
    populateSelect("destSelect", document.getElementById("destType").value);
}

function populateSelect(selectId, type) {
    const select = document.getElementById(selectId);
    select.innerHTML = "";

    const items = type === "location" ? allLocations : allShelters;

    items.forEach(item => {
        const opt = document.createElement("option");
        opt.value = item.id;
        opt.textContent = item.name;
        select.appendChild(opt);
    });
}

document.addEventListener("DOMContentLoaded", () => {
    loadDropdownData();

    document.getElementById("startType").addEventListener("change", (e) => {
        populateSelect("startSelect", e.target.value);
    });

    document.getElementById("destType").addEventListener("change", (e) => {
        populateSelect("destSelect", e.target.value);
    });

    document.getElementById("findRouteBtn").addEventListener("click", calculateRoute);
});

async function calculateRoute() {
    const startType = document.getElementById("startType").value;
    const startId = document.getElementById("startSelect").value;
    const destType = document.getElementById("destType").value;
    const destId = document.getElementById("destSelect").value;

    const resultBox = document.getElementById("routeResult");
    const errorBox = document.getElementById("routeError");
    resultBox.style.display = "none";
    errorBox.style.display = "none";

    if (!startId || !destId) {
        showError("Please select both a start point and a destination.");
        return;
    }

    try {
        const response = await fetch("/api/calculate-route", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                start_type: startType,
                start_id: parseInt(startId),
                dest_type: destType,
                dest_id: parseInt(destId)
            })
        });

        const data = await response.json();

        if (!data.found) {
            showError(data.reason || "No route could be found.");
            return;
        }

        showResult(data);
        drawRoute(data.route);

    } catch (err) {
        showError("Something went wrong while contacting the server: " + err.message);
    }
}

function showResult(data) {
    const resultBox = document.getElementById("routeResult");

    let stepsHtml = data.route.map(step =>
        `<li>${step.name} <em>(${step.type})</em></li>`
    ).join("");

    resultBox.innerHTML = `
        <h3>✅ Safest Route Found</h3>
        <ol>${stepsHtml}</ol>
        <p><strong>Total Distance:</strong> ${data.total_distance_km} km</p>
        <p><strong>Total Cost (distance + flood penalty):</strong> ${data.total_cost}</p>
        <p><strong>Estimated Travel Time:</strong> ${data.estimated_time_minutes} minutes</p>
    `;
    resultBox.style.display = "block";
}

function showError(message) {
    const errorBox = document.getElementById("routeError");
    errorBox.textContent = "⚠️ " + message;
    errorBox.style.display = "block";
}
