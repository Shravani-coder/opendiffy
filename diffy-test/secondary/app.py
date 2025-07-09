
import os
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

SERVICE_NAME = os.getenv("SERVICE_NAME", "Secondary")
PORT         = int(os.getenv("PORT", 9200))

@app.route('/products', methods=['POST'])
def products():
    data = request.get_json(force=True)
    id_    = int(data.get("id"))
    name   = data.get("name", "Unknown")
    price  = float(data.get("price"))

    print(f"[{SERVICE_NAME}] POST /products  body={data}")

    response = {
        "id":           id_,
        "name":         name,
        "price":        price + 5,  # add a handling fee to simulate difference
        "fee_applied":  5,
        "processed_by": SERVICE_NAME,
        "processed_at": datetime.utcnow().isoformat()
    }
    return jsonify(response), 200

@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        "service":   SERVICE_NAME,
        "status":    "running",
        "timestamp": datetime.utcnow().isoformat()
    }), 200

def start():
    print(f"\n Running: {__file__}")
    print(" Registered routes:")
    print(app.url_map)
    print(f" {SERVICE_NAME} starting on port {PORT}")
    app.run(host='127.0.0.1', port=PORT, debug=True)

start()
