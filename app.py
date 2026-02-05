import os
import sqlite3
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, abort, g
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Cambia esto por algo largo/aleatorio si lo subes a internet
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev_key_change_me_in_prod")

# Cambia la contraseña del admin
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")

DB_PATH = os.path.join(app.instance_path, "respuestas.db")


def ensure_instance_folder():
    os.makedirs(app.instance_path, exist_ok=True)


def get_db():
    ensure_instance_folder()
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS respuestas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            choice TEXT NOT NULL,
            created_at TEXT NOT NULL,
            ip TEXT,
            user_agent TEXT
        )
    """)
    conn.commit()
    # No cerramos aquí explícitamente, se cerrará con teardown_appcontext o al final del script si es standalone
    if 'db' in g:
        conn.close() # Pero en init_db manual mejor cerrar para evitar bloqueos si se llama interactivo


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", nombre="Anghi", titulo="Para Anghi")

@app.route("/flower-intro")
def flower_intro():
    return render_template("flower_intro.html", nombre="Anghi")

@app.route("/respuesta", methods=["POST"])
def respuesta():
    choice = (request.form.get("choice") or "").strip().lower()
    if choice not in ("yes", "time"):
        abort(400)

    conn = get_db()
    conn.execute(
        "INSERT INTO respuestas (choice, created_at, ip, user_agent) VALUES (?, ?, ?, ?)",
        (
            choice,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            request.remote_addr,
            request.headers.get("User-Agent", ""),
        ),
    )
    conn.commit()
    # conn.close() -> Ya no es necesario, se cierra automáticamente con teardown_appcontext

    return render_template("gracias.html", choice=choice, nombre="Anghi")


@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == ADMIN_PASSWORD:
            session["is_admin"] = True
            return redirect(url_for("admin_respuestas"))
        return render_template("admin_login.html", error="Contraseña incorrecta.")
    return render_template("admin_login.html")


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.route("/admin/respuestas", methods=["GET"])
@admin_required
def admin_respuestas():
    conn = get_db()
    rows = conn.execute(
        "SELECT id, choice, created_at, ip FROM respuestas ORDER BY id DESC"
    ).fetchall()
    return render_template("admin.html", rows=rows)


if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(debug=True)
