from flask import Flask
from flask_cors import CORS
from flask_smorest import Api

from . import db
from .routes.health import blp as health_blp
from .routes.api import admin_blp, blp as api_blp


# PUBLIC_INTERFACE
def create_app() -> Flask:
    """Create and configure the Flask application.

    Initializes:
    - CORS (allow frontend on http://localhost:3000)
    - OpenAPI/Swagger UI under /docs
    - SQLite schema + seed reference data (brands/models/problems)
    - Blueprints for health, customer booking APIs, and admin APIs.

    Returns:
        Flask: configured Flask app instance.
    """
    app = Flask(__name__)
    app.url_map.strict_slashes = False

    # CORS: allow React dev server; keep narrow per requirement.
    CORS(
        app,
        resources={r"/api/*": {"origins": ["http://localhost:3000"]}},
    )

    # OpenAPI / Swagger UI config (flask-smorest)
    app.config["API_TITLE"] = "Mobile Service Booking API"
    app.config["API_VERSION"] = "v1"
    app.config["OPENAPI_VERSION"] = "3.0.3"
    app.config["OPENAPI_URL_PREFIX"] = "/docs"
    app.config["OPENAPI_SWAGGER_UI_PATH"] = ""
    app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"

    api = Api(app)

    # Ensure DB exists and has baseline reference data.
    db.init_db()
    db.seed_reference_data_if_empty()

    api.register_blueprint(health_blp)
    api.register_blueprint(api_blp)
    api.register_blueprint(admin_blp)

    # Expose api for generate_openapi.py compatibility (api.spec usage).
    app.extensions["smorest_api"] = api
    return app


# Backwards-compatible globals for existing tooling/imports.
app = create_app()
api = app.extensions["smorest_api"]
