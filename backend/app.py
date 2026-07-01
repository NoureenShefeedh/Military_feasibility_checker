from flask import Flask
from flask_cors import CORS
from routes.plans import plans_bp
from apscheduler.schedulers.background import BackgroundScheduler
from db import get_connection  # ← your existing db file

app = Flask(__name__)
CORS(app)

app.register_blueprint(plans_bp)

# ── cleanup job ──────────────────────────────────────────
def cleanup_expired_availability():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT cleanup_expired_availability();")
    conn.commit()
    cur.close()
    conn.close()

scheduler = BackgroundScheduler()
scheduler.add_job(cleanup_expired_availability, 'interval', minutes=1)
scheduler.start()
# ─────────────────────────────────────────────────────────

@app.route("/")
def home():
    return "Flask is running"

if __name__ == "__main__":
    app.run(debug=True)