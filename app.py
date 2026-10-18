"""
Trainee Registration API + استضافة الواجهة الأمامية.

يحافظ هذا الملف على عقد الـ API الأصلي في المستودع:
  GET  /          -> {"status": "API is running securely"}      (200)
  POST /register  -> {"message": ..., "trainee_id": ...}        (201)
                     {"error": "Missing required fields"}       (400)
ويضيف: تحقق أدق من المدخلات، منع تكرار البريد (409)، رؤوس أمان، CORS محدود.
"""
import os
import re
from pathlib import Path
from threading import Lock

from flask import Flask, jsonify, request, send_from_directory

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024  # نرفض أي طلب أكبر من 10KB

# المواقع المسموح لها بالاتصال بالـ API من المتصفح (يمكن تغييرها بمتغير بيئة)
ALLOWED_ORIGINS = set(
    os.environ.get(
        "ALLOWED_ORIGINS",
        "http://127.0.0.1:5000,http://localhost:5000,"
        "http://127.0.0.1:5500,http://localhost:5500",  # 5500 = Live Server
    ).split(",")
)

REQUIRED_FIELDS = ("name", "email", "track")
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")

trainees_db = []  # تخزين مؤقت في الذاكرة (يُفقد عند إعادة التشغيل)
db_lock = Lock()  # يمنع تضارب الطلبات المتزامنة


@app.after_request
def add_headers(response):
    """رؤوس أمان + CORS للمصادر المسموحة فقط."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"

    origin = request.headers.get("Origin")
    if origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Vary"] = "Origin"
    return response


# ---------- تقديم ملفات الواجهة (قائمة بيضاء، لا نكشف app.py) ----------
@app.route("/app", methods=["GET"])
def serve_index():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/style.css", methods=["GET"])
def serve_css():
    return send_from_directory(BASE_DIR, "style.css")


@app.route("/script.js", methods=["GET"])
def serve_js():
    return send_from_directory(BASE_DIR, "script.js")


# ---------- مسارات الـ API ----------
@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "API is running securely"}), 200


@app.route("/register", methods=["POST"])
def register_trainee():
    data = request.get_json(silent=True)  # silent: لا ينهار إن لم يكن JSON صالحًا

    # 1) الحقول الناقصة (نفس سلوك المستودع الأصلي)
    if not isinstance(data, dict) or any(k not in data for k in REQUIRED_FIELDS):
        return jsonify({"error": "Missing required fields"}), 400

    # 2) النوع والطول والصيغة
    values = {k: data[k].strip() if isinstance(data[k], str) else None
              for k in REQUIRED_FIELDS}
    invalid = []
    if not values["name"] or not 2 <= len(values["name"]) <= 80:
        invalid.append("name")
    if not values["email"] or len(values["email"]) > 254 \
            or not EMAIL_RE.match(values["email"]):
        invalid.append("email")
    if not values["track"] or len(values["track"]) > 60:
        invalid.append("track")
    if invalid:
        return jsonify({"error": "Invalid field values", "fields": invalid}), 400

    # 3) منع تكرار البريد + الحفظ داخل القفل
    with db_lock:
        email_key = values["email"].lower()
        if any(t["email"].lower() == email_key for t in trainees_db):
            return jsonify({"error": "Email already registered"}), 409

        new_trainee = {"id": len(trainees_db) + 1, **values}
        trainees_db.append(new_trainee)

    return jsonify({
        "message": "Trainee registered successfully!",
        "trainee_id": new_trainee["id"],
    }), 201


if __name__ == "__main__":
    # إعداد آمن: debug=False كما في المستودع الأصلي
    app.run(host="127.0.0.1", port=5000, debug=False)
