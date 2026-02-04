from flask import Blueprint, request, jsonify
from db import get_connection

auth = Blueprint("auth", __name__)

@auth.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT user_id, name, role 
        FROM users
        WHERE email=%s AND password=%s
    """, (email, password))

    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify({
        "user_id": user[0],
        "name": user[1],
        "role": user[2]
    })
