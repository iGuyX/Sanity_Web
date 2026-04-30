from datetime import datetime
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-secret-key"
DB_PATH = "requests.db"


def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS help_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_type TEXT NOT NULL,
            main_version TEXT NOT NULL,
            jhf TEXT NOT NULL,
            sr_number TEXT NOT NULL,
            task_number TEXT NOT NULL,
            fix_path TEXT NOT NULL,
            eta TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def save_request(payload: dict) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO help_requests (
            machine_type,
            main_version,
            jhf,
            sr_number,
            task_number,
            fix_path,
            eta,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload["machine_type"],
            payload["main_version"],
            payload["jhf"],
            payload["sr_number"],
            payload["task_number"],
            payload["fix_path"],
            payload["eta"],
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    conn.commit()
    conn.close()


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        payload = {
            "machine_type": request.form.get("machine_type", "").strip(),
            "main_version": request.form.get("main_version", "").strip(),
            "jhf": request.form.get("jhf", "").strip(),
            "sr_number": request.form.get("sr_number", "").strip(),
            "task_number": request.form.get("task_number", "").strip(),
            "fix_path": request.form.get("fix_path", "").strip(),
            "eta": request.form.get("eta", "").strip(),
        }

        if not all(payload.values()):
            flash("Please fill in all fields.")
            return redirect(url_for("index"))

        save_request(payload)
        flash("Request submitted successfully. Guy T is on it.")
        return redirect(url_for("index"))

    return render_template("index.html")


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
