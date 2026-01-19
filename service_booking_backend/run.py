import os

from app import app

if __name__ == "__main__":
    # Running on 0.0.0.0 allows container access.
    # Prefer port 5000 (per requirement) with env override for flexibility.
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
