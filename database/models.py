"""
database/models.py

All database access code for FloodSafe.
Uses plain SQLite3 (no ORM) so it stays simple and easy to understand.
"""

import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "floodsafe.db")


def get_db_connection():
    """Create a new database connection with dict-like row access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """
    Create all tables if they do not already exist,
    and fill them with sample data ONLY if the database is empty.
    This function is safe to call every time the app starts.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # ---------- USERS TABLE (admin login) ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # ---------- LOCATIONS TABLE ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            description TEXT
        )
    """)

    # ---------- SHELTERS TABLE ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS shelters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            capacity INTEGER DEFAULT 100
        )
    """)

    # ---------- ROADS TABLE ----------
    # from_type / to_type is either 'location' or 'shelter'
    # from_id / to_id refers to the id in the matching table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS roads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_type TEXT NOT NULL,
            from_id INTEGER NOT NULL,
            to_type TEXT NOT NULL,
            to_id INTEGER NOT NULL,
            distance_km REAL NOT NULL,
            flood_status TEXT NOT NULL DEFAULT 'safe'
        )
    """)

    conn.commit()

    # ---------- INSERT SAMPLE DATA ONLY IF TABLES ARE EMPTY ----------
    cur.execute("SELECT COUNT(*) FROM locations")
    location_count = cur.fetchone()[0]

    if location_count == 0:
        insert_sample_data(conn)

    conn.close()


def insert_sample_data(conn):
    """Insert sample admin user, locations, shelters and roads."""
    cur = conn.cursor()

    # ---------- Default admin user ----------
    # username: admin   password: admin123
    hashed_pw = generate_password_hash("admin123")
    cur.execute(
        "INSERT INTO users (username, password) VALUES (?, ?)",
        ("admin", hashed_pw),
    )

    # ---------- Sample locations ----------
    locations = [
        ("City Center", 11.0168, 76.9558, "Main city hub"),
        ("North Colony", 11.0350, 76.9600, "Residential area in the north"),
        ("Riverside Area", 11.0100, 76.9420, "Low-lying area near the river"),
        ("East Market", 11.0200, 76.9750, "Busy market area"),
        ("West Town", 11.0080, 76.9300, "Western residential zone"),
        ("Hilltop", 11.0450, 76.9500, "Elevated safe area"),
    ]
    cur.executemany(
        "INSERT INTO locations (name, latitude, longitude, description) VALUES (?, ?, ?, ?)",
        locations,
    )

    # ---------- Sample shelters ----------
    shelters = [
        ("Community Hall Shelter", 11.0400, 76.9650, 200),
        ("School Shelter", 11.0250, 76.9820, 150),
        ("Stadium Shelter", 11.0500, 76.9550, 300),
    ]
    cur.executemany(
        "INSERT INTO shelters (name, latitude, longitude, capacity) VALUES (?, ?, ?, ?)",
        shelters,
    )

    conn.commit()

    # ---------- Sample roads ----------
    # location ids: 1=City Center, 2=North Colony, 3=Riverside Area,
    #               4=East Market, 5=West Town, 6=Hilltop
    # shelter ids:  1=Community Hall, 2=School Shelter, 3=Stadium Shelter
    roads = [
        ("location", 1, "location", 2, 2.0, "safe"),      # City Center -> North Colony
        ("location", 1, "location", 3, 1.5, "high"),       # City Center -> Riverside (flooded)
        ("location", 1, "location", 4, 3.0, "low"),        # City Center -> East Market
        ("location", 1, "location", 5, 2.5, "medium"),     # City Center -> West Town
        ("location", 2, "shelter", 1, 1.0, "safe"),         # North Colony -> Community Hall
        ("location", 2, "location", 6, 4.0, "safe"),        # North Colony -> Hilltop
        ("location", 2, "location", 4, 3.5, "high"),        # North Colony -> East Market (flooded)
        ("location", 3, "location", 4, 2.0, "blocked"),     # Riverside -> East Market (BLOCKED)
        ("location", 3, "shelter", 1, 3.5, "medium"),       # Riverside -> Community Hall
        ("location", 4, "shelter", 2, 1.2, "safe"),         # East Market -> School Shelter
        ("location", 4, "location", 5, 2.8, "low"),         # East Market -> West Town
        ("location", 5, "location", 6, 3.2, "medium"),      # West Town -> Hilltop
        ("location", 6, "shelter", 3, 1.5, "safe"),         # Hilltop -> Stadium Shelter
        ("location", 3, "location", 6, 5.0, "low"),         # Riverside -> Hilltop
    ]
    cur.executemany(
        """INSERT INTO roads (from_type, from_id, to_type, to_id, distance_km, flood_status)
           VALUES (?, ?, ?, ?, ?, ?)""",
        roads,
    )

    conn.commit()


# ------------------------------------------------------------------
# LOCATIONS CRUD
# ------------------------------------------------------------------

def get_all_locations():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM locations ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_location_by_id(location_id):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM locations WHERE id = ?", (location_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_location(name, latitude, longitude, description):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO locations (name, latitude, longitude, description) VALUES (?, ?, ?, ?)",
        (name, latitude, longitude, description),
    )
    conn.commit()
    conn.close()


def update_location(location_id, name, latitude, longitude, description):
    conn = get_db_connection()
    conn.execute(
        "UPDATE locations SET name=?, latitude=?, longitude=?, description=? WHERE id=?",
        (name, latitude, longitude, description, location_id),
    )
    conn.commit()
    conn.close()


def delete_location(location_id):
    conn = get_db_connection()
    # Also remove roads that reference this location so the graph stays valid
    conn.execute("DELETE FROM roads WHERE (from_type='location' AND from_id=?) OR (to_type='location' AND to_id=?)",
                 (location_id, location_id))
    conn.execute("DELETE FROM locations WHERE id = ?", (location_id,))
    conn.commit()
    conn.close()


# ------------------------------------------------------------------
# SHELTERS CRUD
# ------------------------------------------------------------------

def get_all_shelters():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM shelters ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_shelter_by_id(shelter_id):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM shelters WHERE id = ?", (shelter_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_shelter(name, latitude, longitude, capacity):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO shelters (name, latitude, longitude, capacity) VALUES (?, ?, ?, ?)",
        (name, latitude, longitude, capacity),
    )
    conn.commit()
    conn.close()


def update_shelter(shelter_id, name, latitude, longitude, capacity):
    conn = get_db_connection()
    conn.execute(
        "UPDATE shelters SET name=?, latitude=?, longitude=?, capacity=? WHERE id=?",
        (name, latitude, longitude, capacity, shelter_id),
    )
    conn.commit()
    conn.close()


def delete_shelter(shelter_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM roads WHERE (from_type='shelter' AND from_id=?) OR (to_type='shelter' AND to_id=?)",
                 (shelter_id, shelter_id))
    conn.execute("DELETE FROM shelters WHERE id = ?", (shelter_id,))
    conn.commit()
    conn.close()


# ------------------------------------------------------------------
# ROADS CRUD
# ------------------------------------------------------------------

def get_all_roads():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM roads ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_road_by_id(road_id):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM roads WHERE id = ?", (road_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_road(from_type, from_id, to_type, to_id, distance_km, flood_status):
    conn = get_db_connection()
    conn.execute(
        """INSERT INTO roads (from_type, from_id, to_type, to_id, distance_km, flood_status)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (from_type, from_id, to_type, to_id, distance_km, flood_status),
    )
    conn.commit()
    conn.close()


def update_road(road_id, from_type, from_id, to_type, to_id, distance_km, flood_status):
    conn = get_db_connection()
    conn.execute(
        """UPDATE roads SET from_type=?, from_id=?, to_type=?, to_id=?, distance_km=?, flood_status=?
           WHERE id=?""",
        (from_type, from_id, to_type, to_id, distance_km, flood_status, road_id),
    )
    conn.commit()
    conn.close()


def update_road_status(road_id, flood_status):
    conn = get_db_connection()
    conn.execute("UPDATE roads SET flood_status=? WHERE id=?", (flood_status, road_id))
    conn.commit()
    conn.close()


def delete_road(road_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM roads WHERE id = ?", (road_id,))
    conn.commit()
    conn.close()


# ------------------------------------------------------------------
# USERS (admin login)
# ------------------------------------------------------------------

def get_user_by_username(username):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ------------------------------------------------------------------
# HELPERS FOR NODE NAMES (used to display readable names in routes)
# ------------------------------------------------------------------

def get_node_name(node_type, node_id):
    """Return the human-readable name of a location or shelter node."""
    if node_type == "location":
        loc = get_location_by_id(node_id)
        return loc["name"] if loc else f"Location {node_id}"
    else:
        shel = get_shelter_by_id(node_id)
        return shel["name"] if shel else f"Shelter {node_id}"


def get_node_coords(node_type, node_id):
    """Return (latitude, longitude) of a location or shelter node."""
    if node_type == "location":
        loc = get_location_by_id(node_id)
        return (loc["latitude"], loc["longitude"]) if loc else (None, None)
    else:
        shel = get_shelter_by_id(node_id)
        return (shel["latitude"], shel["longitude"]) if shel else (None, None)
