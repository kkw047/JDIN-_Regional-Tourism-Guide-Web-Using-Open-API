from flask import Blueprint, request, jsonify
import itertools
import math

bp = Blueprint('map', __name__)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

@bp.route('/optimize_route', methods=['POST'])
def optimize_route():
    data = request.json.get("sites", [])
    return_to_start = request.json.get("return_to_start", False)

    if not data or len(data) < 2:
        return jsonify({"error": "Not enough sites"}), 400
    if len(data) > 7:
        return jsonify({"error": "Too many sites (max 7 allowed)"}), 400

    for site in data:
        try:
            site["lat"] = float(site["lat"])
            site["lon"] = float(site["lon"])
        except (KeyError, ValueError, TypeError):
            return jsonify({"error": f"Invalid coordinates: {site}"}), 400

    min_distance = float("inf")
    best_order = []

    for perm in itertools.permutations(data):
        dist = sum(
            haversine(perm[i]["lat"], perm[i]["lon"], perm[i + 1]["lat"], perm[i + 1]["lon"])
            for i in range(len(perm) - 1)
        )
        if return_to_start:
            dist += haversine(perm[-1]["lat"], perm[-1]["lon"], perm[0]["lat"], perm[0]["lon"])

        if dist < min_distance:
            min_distance = dist
            best_order = perm

    return jsonify({"optimized": list(best_order)})
