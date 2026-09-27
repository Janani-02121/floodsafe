/*
admin.js
Handles all Add / Edit / Delete actions on the Admin Dashboard
by calling the /api/admin/... endpoints with fetch().
*/

function showMessage(text, isSuccess) {
    const box = document.getElementById("adminMessage");
    box.textContent = text;
    box.className = "admin-message " + (isSuccess ? "success" : "error");
    box.style.display = "block";
    window.scrollTo({ top: 0, behavior: "smooth" });
}

async function postJSON(url, data) {
    const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
    });
    return response.json();
}

/* ============== LOCATIONS ============== */

document.getElementById("addLocationForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    const payload = {
        name: form.name.value,
        latitude: form.latitude.value,
        longitude: form.longitude.value,
        description: form.description.value
    };
    const result = await postJSON("/api/admin/locations/add", payload);
    if (result.success) {
        showMessage("Location added successfully.", true);
        setTimeout(() => location.reload(), 800);
    } else {
        showMessage("Failed to add location: " + result.reason, false);
    }
});

document.querySelectorAll(".delete-location").forEach(btn => {
    btn.addEventListener("click", async (e) => {
        const row = e.target.closest("tr");
        const id = row.dataset.id;
        if (!confirm("Delete this location? Connected roads will also be removed.")) return;

        const result = await postJSON(`/api/admin/locations/delete/${id}`, {});
        if (result.success) {
            showMessage("Location deleted.", true);
            setTimeout(() => location.reload(), 600);
        } else {
            showMessage("Failed to delete location.", false);
        }
    });
});

document.querySelectorAll(".edit-location").forEach(btn => {
    btn.addEventListener("click", async (e) => {
        const row = e.target.closest("tr");
        const id = row.dataset.id;

        const name = prompt("Name:", row.querySelector(".f-name").textContent);
        if (name === null) return;
        const lat = prompt("Latitude:", row.querySelector(".f-lat").textContent);
        if (lat === null) return;
        const lng = prompt("Longitude:", row.querySelector(".f-lng").textContent);
        if (lng === null) return;
        const desc = prompt("Description:", row.querySelector(".f-desc").textContent);

        const result = await postJSON(`/api/admin/locations/edit/${id}`, {
            name: name, latitude: lat, longitude: lng, description: desc || ""
        });

        if (result.success) {
            showMessage("Location updated.", true);
            setTimeout(() => location.reload(), 600);
        } else {
            showMessage("Failed to update location: " + result.reason, false);
        }
    });
});

/* ============== SHELTERS ============== */

document.getElementById("addShelterForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    const payload = {
        name: form.name.value,
        latitude: form.latitude.value,
        longitude: form.longitude.value,
        capacity: form.capacity.value || 100
    };
    const result = await postJSON("/api/admin/shelters/add", payload);
    if (result.success) {
        showMessage("Shelter added successfully.", true);
        setTimeout(() => location.reload(), 800);
    } else {
        showMessage("Failed to add shelter: " + result.reason, false);
    }
});

document.querySelectorAll(".delete-shelter").forEach(btn => {
    btn.addEventListener("click", async (e) => {
        const row = e.target.closest("tr");
        const id = row.dataset.id;
        if (!confirm("Delete this shelter? Connected roads will also be removed.")) return;

        const result = await postJSON(`/api/admin/shelters/delete/${id}`, {});
        if (result.success) {
            showMessage("Shelter deleted.", true);
            setTimeout(() => location.reload(), 600);
        } else {
            showMessage("Failed to delete shelter.", false);
        }
    });
});

document.querySelectorAll(".edit-shelter").forEach(btn => {
    btn.addEventListener("click", async (e) => {
        const row = e.target.closest("tr");
        const id = row.dataset.id;

        const name = prompt("Name:", row.querySelector(".f-name").textContent);
        if (name === null) return;
        const lat = prompt("Latitude:", row.querySelector(".f-lat").textContent);
        if (lat === null) return;
        const lng = prompt("Longitude:", row.querySelector(".f-lng").textContent);
        if (lng === null) return;
        const capacity = prompt("Capacity:", row.querySelector(".f-capacity").textContent);

        const result = await postJSON(`/api/admin/shelters/edit/${id}`, {
            name: name, latitude: lat, longitude: lng, capacity: capacity || 100
        });

        if (result.success) {
            showMessage("Shelter updated.", true);
            setTimeout(() => location.reload(), 600);
        } else {
            showMessage("Failed to update shelter: " + result.reason, false);
        }
    });
});

/* ============== ROADS ============== */

document.getElementById("addRoadForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    const payload = {
        from_type: form.from_type.value,
        from_id: form.from_id.value,
        to_type: form.to_type.value,
        to_id: form.to_id.value,
        distance_km: form.distance_km.value,
        flood_status: form.flood_status.value
    };
    const result = await postJSON("/api/admin/roads/add", payload);
    if (result.success) {
        showMessage("Road added successfully.", true);
        setTimeout(() => location.reload(), 800);
    } else {
        showMessage("Failed to add road: " + result.reason, false);
    }
});

document.querySelectorAll(".delete-road").forEach(btn => {
    btn.addEventListener("click", async (e) => {
        const row = e.target.closest("tr");
        const id = row.dataset.id;
        if (!confirm("Delete this road?")) return;

        const result = await postJSON(`/api/admin/roads/delete/${id}`, {});
        if (result.success) {
            showMessage("Road deleted.", true);
            setTimeout(() => location.reload(), 600);
        } else {
            showMessage("Failed to delete road.", false);
        }
    });
});

// Changing the flood status dropdown updates immediately
document.querySelectorAll(".status-select").forEach(select => {
    select.addEventListener("change", async (e) => {
        const row = e.target.closest("tr");
        const id = row.dataset.id;
        const newStatus = e.target.value;

        const result = await postJSON(`/api/admin/roads/status/${id}`, {
            flood_status: newStatus
        });

        if (result.success) {
            showMessage(`Road #${id} flood status updated to "${newStatus.toUpperCase()}".`, true);
        } else {
            showMessage("Failed to update flood status.", false);
        }
    });
});
