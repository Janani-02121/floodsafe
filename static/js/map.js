/*
map.js
Handles the Leaflet map: shows locations, shelters, and roads
colored by flood status. Uses OpenStreetMap tiles (free, no API key).
*/

let map;
let roadLayers = [];
let markerLayers = [];
let routeLine = null;

// Colors for each flood status (must match style.css legend)
const FLOOD_COLORS = {
    safe: "#16a34a",
    low: "#84cc16",
    medium: "#f59e0b",
    high: "#ea580c",
    blocked: "#6b7280"
};

function initMap() {
    // Center roughly on the sample data area (Coimbatore-like coordinates)
    map = L.map("map").setView([11.025, 76.955], 13);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors"
    }).addTo(map);

    loadMapData();
}

async function loadMapData() {
    const [locations, shelters, roads] = await Promise.all([
        fetch("/api/locations").then(r => r.json()),
        fetch("/api/shelters").then(r => r.json()),
        fetch("/api/roads").then(r => r.json())
    ]);

    drawRoads(roads);
    drawLocations(locations);
    drawShelters(shelters);
}

function clearLayer(layerArray) {
    layerArray.forEach(l => map.removeLayer(l));
    return [];
}

function drawRoads(roads) {
    roadLayers = clearLayer(roadLayers);

    roads.forEach(road => {
        if (road.from_lat == null || road.to_lat == null) return;

        const color = FLOOD_COLORS[road.flood_status] || "#3388ff";
        const dashed = road.flood_status === "blocked" ? "6,6" : null;

        const line = L.polyline(
            [[road.from_lat, road.from_lng], [road.to_lat, road.to_lng]],
            { color: color, weight: 4, dashArray: dashed }
        ).addTo(map);

        line.bindPopup(
            `<strong>${road.from_name} &rarr; ${road.to_name}</strong><br>` +
            `Distance: ${road.distance_km} km<br>` +
            `Flood Status: <strong>${road.flood_status.toUpperCase()}</strong>`
        );

        roadLayers.push(line);
    });
}

function drawLocations(locations) {
    locations.forEach(loc => {
        const marker = L.circleMarker([loc.latitude, loc.longitude], {
            radius: 8,
            color: "#0b5394",
            fillColor: "#3b82f6",
            fillOpacity: 0.9
        }).addTo(map);

        marker.bindPopup(`<strong>📍 ${loc.name}</strong><br>${loc.description || ""}`);
        markerLayers.push(marker);
    });
}

function drawShelters(shelters) {
    shelters.forEach(shelter => {
        const marker = L.circleMarker([shelter.latitude, shelter.longitude], {
            radius: 9,
            color: "#166534",
            fillColor: "#22c55e",
            fillOpacity: 0.95
        }).addTo(map);

        marker.bindPopup(`<strong>🏠 ${shelter.name}</strong><br>Capacity: ${shelter.capacity}`);
        markerLayers.push(marker);
    });
}

// Draw the calculated evacuation route as a thick blue line with markers
function drawRoute(routeSteps) {
    if (routeLine) {
        map.removeLayer(routeLine);
        routeLine = null;
    }

    const latlngs = routeSteps.map(step => [step.latitude, step.longitude]);

    routeLine = L.polyline(latlngs, {
        color: "#1d4ed8",
        weight: 6,
        opacity: 0.9
    }).addTo(map);

    map.fitBounds(routeLine.getBounds(), { padding: [40, 40] });

    // Highlight start and end
    L.circleMarker(latlngs[0], { radius: 10, color: "#1d4ed8", fillColor: "#93c5fd", fillOpacity: 1 })
        .addTo(map).bindPopup("Start: " + routeSteps[0].name);

    const last = routeSteps[routeSteps.length - 1];
    L.circleMarker([last.latitude, last.longitude], { radius: 10, color: "#166534", fillColor: "#22c55e", fillOpacity: 1 })
        .addTo(map).bindPopup("Destination: " + last.name);
}

document.addEventListener("DOMContentLoaded", initMap);
