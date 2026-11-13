"""Recipe Box API — BE104 course skeleton.

A working Flask + SQLite CRUD API for recipes. It stores data perfectly —
and it trusts everyone. There is no authentication and no authorization yet.
That is the point: you will add both, lesson by lesson, in Units 2 and 3.
"""

import sqlite3

from werkzeug.security import generate_password_hash, check_password_hash

from flask import Flask, g, jsonify, request

import os

import jwt

from datetime import datetime, timedelta

from dotenv import load_dotenv 


load_dotenv()

JWT_SECRET = os.environ.get("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET is not set")

JWT_ALGORITHM = "HS256"

DATABASE = "recipes.db"

app = Flask(__name__)

def hash_password(plain_password: str) -> str:
    return generate_password_hash(plain_password)

def verify_password(stored_hash: str, candidate_password: str) -> bool:
    return check_password_hash(stored_hash, candidate_password) 

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def recipe_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "ingredients": row["ingredients"],
        "instructions": row["instructions"],
        "is_public": bool(row["is_public"]),
    }


@app.get("/")
def hello():
    return jsonify({"message": "Recipe Box API", "recipes": "/recipes"})


@app.get("/recipes")
def list_recipes():
    rows = get_db().execute("SELECT * FROM recipes ORDER BY id").fetchall()
    return jsonify([recipe_to_dict(r) for r in rows])


@app.get("/recipes/<int:recipe_id>")
def get_recipe(recipe_id):
    row = get_db().execute(
        "SELECT * FROM recipes WHERE id = ?", (recipe_id,)
    ).fetchone()
    if row is None:
        return jsonify({"error": "recipe not found"}), 404
    return jsonify(recipe_to_dict(row))

@app.get("/debug-decode")
def debug_decode():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return {"error": "no bearer"}, 400

    token = auth_header.split(" ", 1)[1]

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return {"status": "ok", "payload": payload}, 200
    except Exception as e:
        return {
            "status": "error",
            "type": type(e).__name__,
            "message": str(e),
        }, 401 

@app.post("/recipes")
def create_recipe():
    # 1 Read Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid Authorization header"}), 401

    # 2 Pull out the token string
    token = auth_header.split(" ", 1)[1]

    #3 Verify token
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "token expired, please log in again"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401

    # 4 Store verified identity on request (for later use)
    request.user = {
        "id": payload.get("sub"),
        "username": payload.get("username"),
        "role": payload.get("role"),  # 👈 NEW: role claim 
    }

    # 5 Existing create logic
    data = request.get_json(silent=True)
    if not data or not data.get("title") or not data.get("ingredients"):
        return jsonify({"error": "title and ingredients are required"}), 400

    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO recipes (title, ingredients, instructions, is_public, owner_id)"
            " VALUES (?, ?, ?, ?, ?)",
            (
                data["title"],
                data["ingredients"],
                data.get("instructions", ""),
                1 if data.get("is_public", True) else 0,
                request.user["id"],
            ),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "a recipe with that title already exists"}), 409

    row = db.execute(
        "SELECT * FROM recipes WHERE id = ?", (cur.lastrowid,)
    ).fetchone()
    return jsonify(recipe_to_dict(row)), 201

@app.post("/register")
def register():
    data = request.get_json()

    if not data:
        return {"error": "Request body must be JSON"}, 400

    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not username or not email or not password:
        return {"error": "Missing username, email, or password"}, 400

    password_hash = generate_password_hash(password)

    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, password_hash),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return {"error": "User already exists"}, 409

    return {
        "id": cursor.lastrowid,
        "username": username,
        "email": email,
    }, 201

@app.post("/login")
def login():
    data = request.get_json() or {}

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return {"error": "username and password are required"}, 400

    db = get_db()
    cursor = db.execute(
        "SELECT id, username, email, password_hash, role FROM users WHERE username = ?",
        (username,),
    )
    user = cursor.fetchone()

    if user is None:
        return {"error": "invalid credentials"}, 401

    if not check_password_hash(user["password_hash"], password):
        return {"error": "invalid credentials"}, 401    

    payload = {
        "sub": str(user["id"]),               # id as STRING
        "username": user["username"],
        "role": user["role"],                # 👈 NEW: role claim
        "exp": datetime.utcnow() + timedelta(minutes=30),
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

    return {"token": token}, 200

@app.patch("/recipes/<int:recipe_id>")
def update_recipe(recipe_id):
    # Auth guard
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid Authorization header"}), 401

    token = auth_header.split(" ", 1)[1]

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "token expired, please log in again"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401

    request.user = {
        "id": payload.get("sub"),
        "username": payload.get("username"),
        "role": payload.get("role"),  # 👈 NEW: role claim
    }

    db = get_db()

    # 1) Load recipe first
    row = db.execute(
        "SELECT * FROM recipes WHERE id = ?", (recipe_id,)
    ).fetchone()
    if row is None:
        return jsonify({"error": "recipe not found"}), 404

        # 2) Enforce admin-or-owner
    is_owner = row["owner_id"] == request.user["id"]
    is_admin = request.user.get("role") == "admin"

    if not is_owner and not is_admin:
        return jsonify({"error": "forbidden: not your recipe"}), 403

    # 3) Build update fields
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "a JSON body is required"}), 400

    fields, values = [], []
    for column in ("title", "ingredients", "instructions"):
        if column in data:
            fields.append(f"{column} = ?")
            values.append(data[column])
    if "is_public" in data:
        fields.append("is_public = ?")
        values.append(1 if data["is_public"] else 0)
    if not fields:
        return jsonify({"error": "nothing to update"}), 400

    values.append(recipe_id)
    try:
        cur = db.execute(
            f"UPDATE recipes SET {', '.join(fields)} WHERE id = ?", values
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "a recipe with that title already exists"}), 409

    row = db.execute(
        "SELECT * FROM recipes WHERE id = ?", (recipe_id,)
    ).fetchone()
    return jsonify(recipe_to_dict(row))


@app.delete("/recipes/<int:recipe_id>")
def delete_recipe(recipe_id):
    # Auth guard
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid Authorization header"}), 401

    token = auth_header.split(" ", 1)[1]

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "token expired, please log in again"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401

    request.user = {
        "id": payload.get("sub"),
        "username": payload.get("username"),
        "role": payload.get("role"),  # 👈 NEW: role claim
    }

    db = get_db()

    # 1) Load recipe first
    row = db.execute(
        "SELECT * FROM recipes WHERE id = ?", (recipe_id,)
    ).fetchone()
    if row is None:
        return jsonify({"error": "recipe not found"}), 404

        # 2) Enforce admin-or-owner
    is_owner = row["owner_id"] == request.user["id"]
    is_admin = request.user.get("role") == "admin"

    if not is_owner and not is_admin:
        return jsonify({"error": "forbidden: not your recipe"}), 403

    # 3) Perform delete
    cur = db.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
    db.commit()
    return "", 204

if __name__ == "__main__":
    app.run(debug=True)
