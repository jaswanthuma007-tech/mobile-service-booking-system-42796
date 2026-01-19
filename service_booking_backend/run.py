from app import app

if __name__ == "__main__":
    # Running on 0.0.0.0 allows container access; port 3001 is the expected backend port.
    app.run(host="0.0.0.0", port=3001, debug=True)
