"""
app.py

FloodSafe - Smart Flood Evacuation Route Finder
Main Flask application file.

Run with:  python app.py
Open:      http://127.0.0.1:5000
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import check_password_hash

from database import models
from algorithm.dijkstra import build_graph, dijkstra, node_key

app = Flask(__name__)
app.secret_key = "floodsafe_secret_key_change_this_in_production"


# ============================================================
# INITIALIZE DATABASE ON STARTUP
# ============================================================
models.init_db()


# ============================================================
# LOGIN REQUIRED HELPER
# ============================================================
def is_logged_in():
    return session.get("admin_logged_in", False)


# ============================================================
# PUBLIC PAGES
# ============================================================

@app.route("/")
def home():
    """Home page."""
    return render_template("index.html")


@app.route("/route-finder")
def route_finder():
    """Route finder page with the interactive Leaflet map."""
    return render_template("route_finder.html")


# ============================================================
# PUBLIC API - DATA FOR THE MAP
# ============================================================

@app.route("/api/locations", methods=["GET"])
def api_get_locations():
    return jsonify(models.get_all_locations())


@app.route("/api/shelters", methods=["GET"])
def api_get_shelters():
    return jsonify(models.get_all_shelters())


@app.route("/api/roads", methods=["GET"])
def api_get_roads():
    roads = models.get_all_roads()
    # Attach readable names and coordinates for drawing on the map
    for r in roads:
        r["from_name"] = models.get_node_name(r["from_type"], r["from_id"])
        r["to_name"] = models.get_node_name(r["to_type"], r["to_id"])
        from_lat, from_lng = models.get_node_coords(r["from_type"], r["from_id"])
        to_lat, to_lng = models.get_node_coords(r["to_type"], r["to_id"])
        r["from_lat"] = from_lat
        r["from_lng"] = from_lng
        r["to_lat"] = to_lat
        r["to_lng"] = to_lng
    return jsonify(roads)


# ============================================================
# ROUTE CALCULATION API (DIJKSTRA)
# ============================================================

@app.route("/api/calculate-route", methods=["POST"])
def api_calculate_route():
    """
    Expects JSON:
        {
            "start_type": "location",
            "start_id": 1,
            "dest_type": "shelter",
            "dest_id": 2
        }

    Returns the shortest / safest route using Dijkstra's algorithm.
    """
    try:
        data = request.get_json(force=True, silent=True)

        if data is None:
            return jsonify({"found": False, "reason": "Invalid or missing JSON in request body."}), 400

        start_type = data.get("start_type")
        start_id = int(data.get("start_id"))
        dest_type = data.get("dest_type")
        dest_id = int(data.get("dest_id"))

        if start_type not in ("location", "shelter") or dest_type not in ("location", "shelter"):
            return jsonify({"found": False, "reason": "Invalid start or destination type."}), 400

        start_key = node_key(start_type, start_id)
        dest_key = node_key(dest_type, dest_id)

        if start_key == dest_key:
            return jsonify({"found": False, "reason": "Start and destination cannot be the same place."}), 400

        roads = models.get_all_roads()
        graph = build_graph(roads)

        result = dijkstra(graph, start_key, dest_key)

        if not result["found"]:
            return jsonify(result), 200

        # Build a detailed, human-readable route for the frontend
        route_steps = []
        for node in result["path"]:
            node_type, node_id = node.split("_")
            node_id = int(node_id)
            name = models.get_node_name(node_type, node_id)
            lat, lng = models.get_node_coords(node_type, node_id)
            route_steps.append({
                "type": node_type,
                "id": node_id,
                "name": name,
                "latitude": lat,
                "longitude": lng,
            })

        # Estimated travel time assuming average evacuation speed of 30 km/h
        avg_speed_kmph = 30
        estimated_minutes = round((result["total_distance"] / avg_speed_kmph) * 60, 1)

        response = {
            "found": True,
            "reason": result["reason"],
            "route": route_steps,
            "total_distance_km": result["total_distance"],
            "total_cost": result["total_cost"],
            "estimated_time_minutes": estimated_minutes,
        }
        return jsonify(response), 200

    except Exception as e:
        return jsonify({"found": False, "reason": f"Server error: {str(e)}"}), 500


# ============================================================
# ADMIN LOGIN / LOGOUT
# ============================================================

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = models.get_user_by_username(username)

        if user and check_password_hash(user["password"], password):
            session["admin_logged_in"] = True
            session["admin_username"] = username
            return redirect(url_for("admin_dashboard"))
        else:
            error = "Invalid username or password."

    return render_template("admin_login.html", error=error)


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


# ============================================================
# ADMIN DASHBOARD PAGE
# ============================================================

@app.route("/admin/dashboard")
def admin_dashboard():
    if not is_logged_in():
        return redirect(url_for("admin_login"))

    return render_template(
        "admin_dashboard.html",
        locations=models.get_all_locations(),
        shelters=models.get_all_shelters(),
        roads=models.get_all_roads(),
        username=session.get("admin_username"),
    )


# ============================================================
# ADMIN API - LOCATIONS CRUD
# ============================================================

@app.route("/api/admin/locations/add", methods=["POST"])
def admin_add_location():
    if not is_logged_in():
        return jsonify({"success": False, "reason": "Not logged in."}), 401
    data = request.get_json(force=True)
    try:
        models.add_location(
            data["name"], float(data["latitude"]), float(data["longitude"]),
            data.get("description", "")
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "reason": str(e)}), 400


@app.route("/api/admin/locations/edit/<int:location_id>", methods=["POST"])
def admin_edit_location(location_id):
    if not is_logged_in():
        return jsonify({"success": False, "reason": "Not logged in."}), 401
    data = request.get_json(force=True)
    try:
        models.update_location(
            location_id, data["name"], float(data["latitude"]), float(data["longitude"]),
            data.get("description", "")
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "reason": str(e)}), 400


@app.route("/api/admin/locations/delete/<int:location_id>", methods=["POST"])
def admin_delete_location(location_id):
    if not is_logged_in():
        return jsonify({"success": False, "reason": "Not logged in."}), 401
    models.delete_location(location_id)
    return jsonify({"success": True})


# ============================================================
# ADMIN API - SHELTERS CRUD
# ============================================================

@app.route("/api/admin/shelters/add", methods=["POST"])
def admin_add_shelter():
    if not is_logged_in():
        return jsonify({"success": False, "reason": "Not logged in."}), 401
    data = request.get_json(force=True)
    try:
        models.add_shelter(
            data["name"], float(data["latitude"]), float(data["longitude"]),
            int(data.get("capacity", 100))
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "reason": str(e)}), 400


@app.route("/api/admin/shelters/edit/<int:shelter_id>", methods=["POST"])
def admin_edit_shelter(shelter_id):
    if not is_logged_in():
        return jsonify({"success": False, "reason": "Not logged in."}), 401
    data = request.get_json(force=True)
    try:
        models.update_shelter(
            shelter_id, data["name"], float(data["latitude"]), float(data["longitude"]),
            int(data.get("capacity", 100))
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "reason": str(e)}), 400


@app.route("/api/admin/shelters/delete/<int:shelter_id>", methods=["POST"])
def admin_delete_shelter(shelter_id):
    if not is_logged_in():
        return jsonify({"success": False, "reason": "Not logged in."}), 401
    models.delete_shelter(shelter_id)
    return jsonify({"success": True})


# ============================================================
# ADMIN API - ROADS CRUD
# ============================================================

VALID_STATUSES = ("safe", "low", "medium", "high", "blocked")


@app.route("/api/admin/roads/add", methods=["POST"])
def admin_add_road():
    if not is_logged_in():
        return jsonify({"success": False, "reason": "Not logged in."}), 401
    data = request.get_json(force=True)
    try:
        status = data.get("flood_status", "safe").lower()
        if status not in VALID_STATUSES:
            return jsonify({"success": False, "reason": "Invalid flood status."}), 400
        models.add_road(
            data["from_type"], int(data["from_id"]),
            data["to_type"], int(data["to_id"]),
            float(data["distance_km"]), status
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "reason": str(e)}), 400


@app.route("/api/admin/roads/edit/<int:road_id>", methods=["POST"])
def admin_edit_road(road_id):
    if not is_logged_in():
        return jsonify({"success": False, "reason": "Not logged in."}), 401
    data = request.get_json(force=True)
    try:
        status = data.get("flood_status", "safe").lower()
        if status not in VALID_STATUSES:
            return jsonify({"success": False, "reason": "Invalid flood status."}), 400
        models.update_road(
            road_id, data["from_type"], int(data["from_id"]),
            data["to_type"], int(data["to_id"]),
            float(data["distance_km"]), status
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "reason": str(e)}), 400


@app.route("/api/admin/roads/status/<int:road_id>", methods=["POST"])
def admin_update_road_status(road_id):
    if not is_logged_in():
        return jsonify({"success": False, "reason": "Not logged in."}), 401
    data = request.get_json(force=True)
    status = data.get("flood_status", "").lower()
    if status not in VALID_STATUSES:
        return jsonify({"success": False, "reason": "Invalid flood status."}), 400
    models.update_road_status(road_id, status)
    return jsonify({"success": True})


@app.route("/api/admin/roads/delete/<int:road_id>", methods=["POST"])
def admin_delete_road(road_id):
    if not is_logged_in():
        return jsonify({"success": False, "reason": "Not logged in."}), 401
    models.delete_road(road_id)
    return jsonify({"success": True})


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(404)
def not_found(e):
    return render_template("index.html"), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error", "message": str(e)}), 500


# ============================================================
# RUN THE APP
# ============================================================

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
