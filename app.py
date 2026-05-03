from datetime import datetime
import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-key")
DB_PATH = "requests.db"
REQUESTS_BOARD_PASSWORD = os.environ.get("REQUESTS_BOARD_PASSWORD", "Fxp12345")

STATUS_ORDER = ["New", "In Progress", "Done"]


def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS help_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_type TEXT NOT NULL,
            appliance_model TEXT NOT NULL DEFAULT '',
            main_version TEXT NOT NULL,
            jhf TEXT NOT NULL,
            sr_number TEXT NOT NULL,
            task_number TEXT NOT NULL,
            fix_path TEXT NOT NULL,
            eta TEXT NOT NULL,
            work_status TEXT NOT NULL DEFAULT 'New',
            sanity_result TEXT NOT NULL DEFAULT '',
            failure_reason TEXT NOT NULL DEFAULT '',
            done_at TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )

    existing_columns = {
        row[1] for row in cur.execute("PRAGMA table_info(help_requests)").fetchall()
    }
    if "appliance_model" not in existing_columns:
        cur.execute(
            "ALTER TABLE help_requests ADD COLUMN appliance_model TEXT NOT NULL DEFAULT ''"
        )
    if "work_status" not in existing_columns:
        cur.execute(
            "ALTER TABLE help_requests ADD COLUMN work_status TEXT NOT NULL DEFAULT 'New'"
        )
    if "sanity_result" not in existing_columns:
        cur.execute(
            "ALTER TABLE help_requests ADD COLUMN sanity_result TEXT NOT NULL DEFAULT ''"
        )
    if "failure_reason" not in existing_columns:
        cur.execute(
            "ALTER TABLE help_requests ADD COLUMN failure_reason TEXT NOT NULL DEFAULT ''"
        )
    if "done_at" not in existing_columns:
        cur.execute(
            "ALTER TABLE help_requests ADD COLUMN done_at TEXT NOT NULL DEFAULT ''"
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
            appliance_model,
            main_version,
            jhf,
            sr_number,
            task_number,
            fix_path,
            eta,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload["machine_type"],
            payload["appliance_model"],
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


def get_requests() -> list[sqlite3.Row]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT
            id,
            machine_type,
            appliance_model,
            main_version,
            jhf,
            sr_number,
            task_number,
            fix_path,
            eta,
            work_status,
            sanity_result,
            failure_reason,
            done_at,
            created_at
        FROM help_requests
        ORDER BY id DESC
        """
    ).fetchall()
    conn.close()
    return rows


def get_requests_grouped() -> tuple[dict[str, list[sqlite3.Row]], list[str]]:
    grouped: dict[str, list[sqlite3.Row]] = {status: [] for status in STATUS_ORDER}

    for row in get_requests():
        status = row["work_status"] or "New"
        if status not in grouped:
            status = "In Progress"
        grouped[status].append(row)

    return grouped, STATUS_ORDER


def get_open_requests() -> list[sqlite3.Row]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT
            id,
            machine_type,
            appliance_model,
            main_version,
            jhf,
            sr_number,
            task_number,
            fix_path,
            eta,
            work_status,
            sanity_result,
            done_at,
            created_at
        FROM help_requests
        WHERE work_status IN ('New', 'In Progress')
        ORDER BY id DESC
        """
    ).fetchall()
    conn.close()
    return rows


def get_pending_tab_data() -> tuple[dict[str, list[sqlite3.Row]], list[str]]:
    rows = get_requests()
    tab_data = {"Open": [], "Done": []}

    for row in rows:
        if row["work_status"] == "Done":
            tab_data["Done"].append(row)
        elif row["work_status"] in {"New", "In Progress"}:
            tab_data["Open"].append(row)

    return tab_data, ["Open", "Done"]


def get_statistics() -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    total_requests = cur.execute("SELECT COUNT(*) FROM help_requests").fetchone()[0]
    open_requests = cur.execute(
        "SELECT COUNT(*) FROM help_requests WHERE work_status IN ('New', 'In Progress')"
    ).fetchone()[0]
    done_requests = cur.execute(
        "SELECT COUNT(*) FROM help_requests WHERE work_status = 'Done'"
    ).fetchone()[0]
    done_today = cur.execute(
        "SELECT COUNT(*) FROM help_requests WHERE done_at != '' AND date(done_at) = date('now', 'localtime')"
    ).fetchone()[0]
    sanity_passed = cur.execute(
        "SELECT COUNT(*) FROM help_requests WHERE sanity_result = 'Sanity Passed'"
    ).fetchone()[0]
    sanity_failed = cur.execute(
        "SELECT COUNT(*) FROM help_requests WHERE sanity_result = 'Sanity Failed'"
    ).fetchone()[0]

    status_counts = {
        row["work_status"]: row["total"]
        for row in cur.execute(
            "SELECT work_status, COUNT(*) AS total FROM help_requests GROUP BY work_status"
        ).fetchall()
    }

    machine_counts = cur.execute(
        """
        SELECT machine_type, COUNT(*) AS total
        FROM help_requests
        GROUP BY machine_type
        ORDER BY total DESC, machine_type ASC
        """
    ).fetchall()

    conn.close()
    return {
        "total_requests": total_requests,
        "open_requests": open_requests,
        "done_requests": done_requests,
        "done_today": done_today,
        "sanity_passed": sanity_passed,
        "sanity_failed": sanity_failed,
        "status_counts": status_counts,
        "machine_counts": machine_counts,
    }


def update_request_response(
    request_id: int,
    work_status: str,
    sanity_result: str,
    failure_reason: str,
) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        """
        UPDATE help_requests
        SET
            work_status = ?,
            sanity_result = ?,
            failure_reason = ?,
            done_at = CASE
                WHEN ? = 'Done' AND work_status != 'Done' THEN ?
                WHEN ? != 'Done' THEN ''
                ELSE done_at
            END
        WHERE id = ?
        """,
        (
            work_status,
            sanity_result,
            failure_reason,
            work_status,
            now_text,
            work_status,
            request_id,
        ),
    )
    conn.commit()
    conn.close()


def delete_request(request_id: int) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM help_requests WHERE id = ?", (request_id,))
    conn.commit()
    conn.close()


def is_board_authorized() -> bool:
    if not REQUESTS_BOARD_PASSWORD:
        return True
    return session.get("board_authed", False)


@app.route("/", methods=["GET", "POST"])
def index():
    session.pop("board_authed", None)

    if request.method == "POST":
        payload = {
            "machine_type": request.form.get("machine_type", "").strip(),
            "appliance_model": request.form.get("appliance_model", "").strip(),
            "main_version": request.form.get("main_version", "").strip(),
            "jhf": request.form.get("jhf", "").strip(),
            "sr_number": request.form.get("sr_number", "").strip(),
            "task_number": request.form.get("task_number", "").strip(),
            "fix_path": request.form.get("fix_path", "").strip(),
            "eta": request.form.get("eta", "").strip(),
        }

        required_fields = [
            payload["machine_type"],
            payload["main_version"],
            payload["jhf"],
            payload["sr_number"],
            payload["task_number"],
            payload["fix_path"],
            payload["eta"],
        ]
        if payload["machine_type"] == "Physical":
            required_fields.append(payload["appliance_model"])

        if not all(required_fields):
            flash("Please fill in all fields.")
            return redirect(url_for("index"))

        save_request(payload)
        flash("Request submitted successfully.")
        return redirect(url_for("index"))

    stats = get_statistics()
    return render_template("index.html", stats=stats)


@app.route("/pending", methods=["GET"])
def pending_view():
    tab_data, tab_order = get_pending_tab_data()
    return render_template("pending.html", tab_data=tab_data, tab_order=tab_order)


@app.route("/requests", methods=["GET", "POST"])
def requests_board():
    if not is_board_authorized():
        if request.method == "POST":
            submitted_password = request.form.get("board_password", "")
            if submitted_password == REQUESTS_BOARD_PASSWORD:
                session["board_authed"] = True
                return redirect(url_for("requests_board"))
            flash("Invalid password.")
        return render_template("requests_login.html")

    grouped_requests, status_order = get_requests_grouped()
    return render_template(
        "requests.html",
        grouped_requests=grouped_requests,
        status_order=status_order,
    )


@app.route("/requests/update", methods=["POST"])
def requests_update():
    if not is_board_authorized():
        return redirect(url_for("requests_board"))

    request_id = request.form.get("request_id", "").strip()
    work_status = request.form.get("work_status", "New").strip()
    sanity_result = request.form.get("sanity_result", "").strip()
    failure_reason = request.form.get("failure_reason", "").strip()

    if not request_id.isdigit():
        flash("Invalid request id.")
        return redirect(url_for("requests_board"))

    if work_status not in STATUS_ORDER:
        work_status = "New"

    if sanity_result == "Sanity Failed" and not failure_reason:
        flash("Please add a failure reason when sanity result is failed.")
        return redirect(url_for("requests_board"))

    if sanity_result != "Sanity Failed":
        failure_reason = ""

    update_request_response(
        int(request_id),
        work_status,
        sanity_result,
        failure_reason,
    )
    flash("Work details saved.")
    return redirect(url_for("requests_board"))


@app.route("/requests/delete", methods=["POST"])
def requests_delete():
    if not is_board_authorized():
        return redirect(url_for("requests_board"))

    request_id = request.form.get("request_id", "").strip()
    if not request_id.isdigit():
        flash("Invalid request id.")
        return redirect(url_for("requests_board"))

    delete_request(int(request_id))
    flash("Task deleted.")
    return redirect(url_for("requests_board"))


@app.route("/requests/logout", methods=["POST"])
def requests_logout():
    session.pop("board_authed", None)
    flash("Logged out from work queue.")
    return redirect(url_for("requests_board"))


init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
