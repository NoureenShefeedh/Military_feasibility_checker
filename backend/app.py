from flask import Flask
from flask_cors import CORS
from routes.plans import plans_bp

app = Flask(__name__)
CORS(app)

app.register_blueprint(plans_bp)

@app.route("/")
def home():
    return "Flask is running"

if __name__ == "__main__":
    app.run(debug=True)