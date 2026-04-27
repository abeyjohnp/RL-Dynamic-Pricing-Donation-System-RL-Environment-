from flask import Flask, render_template, jsonify, request, Response
from env import SupermarketEnv, PricingAction
import csv, io, random
from datetime import datetime

app = Flask(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

DONATION_PARTNERS = [
    {"id": 1, "name": "City Food Bank",          "distance_km": 2.3, "capacity": "High",   "emoji": "🏪", "contact": "citybank@foodrescue.org",  "accepts": "Produce, Dairy, Bakery"},
    {"id": 2, "name": "Sunrise Community Kitchen","distance_km": 4.1, "capacity": "Medium", "emoji": "🍳", "contact": "sunrise@kitchen.org",       "accepts": "Produce, Prepared"},
    {"id": 3, "name": "Hope Shelter",             "distance_km": 6.7, "capacity": "Low",    "emoji": "🏠", "contact": "hope@shelter.org",          "accepts": "Produce, Bakery"},
]

EVENT_MODES = {
    "normal":          {"label": "Normal Operations", "emoji": "🟢", "expiry_delta":  0, "description": "Standard inventory conditions."},
    "holiday":         {"label": "Holiday Rush",      "emoji": "🎄", "expiry_delta": -2, "description": "High footfall but perishables move faster. Tight expiry windows."},
    "low_demand":      {"label": "Low Demand",        "emoji": "📉", "expiry_delta":  0, "description": "Slow sales. Items risk spoilage from sitting too long."},
    "transport_delay": {"label": "Transport Delay",   "emoji": "🚛", "expiry_delta": -1, "description": "Supply disruption. Items arrive with reduced shelf life."},
    "heatwave":        {"label": "Heatwave",          "emoji": "🌡️", "expiry_delta": -3, "description": "Heat accelerates spoilage. Urgent action on all perishables."},
}

# ── Global state ──────────────────────────────────────────────────────────────
_env           = SupermarketEnv()
_obs           = None
_total_revenue = 0.0
_current_event = "normal"
_history       = {"days": [], "waste": [], "revenue": [], "donations": [], "risk_avg": []}
_session_log   = []

# ── Risk scoring ──────────────────────────────────────────────────────────────
def _waste_risk(item) -> int:
    if item.status != "on_shelf": return 0
    d = item.days_to_expiration
    if d <= 0: return 100
    if d == 1: return 92
    if d == 2: return 75
    if d == 3: return 55
    if d <= 5: return 30
    if d <= 7: return 15
    return max(5, 100 - d * 8)

def _risk_label(s: int) -> str:
    if s >= 80: return "critical"
    if s >= 50: return "high"
    if s >= 25: return "medium"
    return "low"

def _pick_partner() -> dict:
    return min(DONATION_PARTNERS, key=lambda p: p["distance_km"])

# ── Recommendation engine ─────────────────────────────────────────────────────
def _recommend_for_item(item) -> dict:
    risk = _waste_risk(item)
    base = {
        "item_id": item.item_id, "item_name": item.name,
        "days_to_expiry": item.days_to_expiration, "base_price": item.base_price,
        "risk_score": risk, "risk_label": _risk_label(risk), "partner": None,
    }
    if item.days_to_expiration <= 1:
        return {**base,
            "action_type": "donate", "badge": "DONATE", "badge_class": "badge-donate",
            "reason": f"Critical: expires in {item.days_to_expiration} day(s). Donating prevents landfill.",
            "expected_result": "Item rescued. Food rescue +1. Landfill avoided.",
            "financial_note": f"Full loss avoided: ${item.base_price:.2f}. Goodwill value: HIGH.",
            "partner": _pick_partner(),
        }
    elif item.days_to_expiration <= 3:
        saved = item.base_price * 0.5
        return {**base,
            "action_type": "set_discount", "badge": "SET DISCOUNT", "badge_class": "badge-discount",
            "reason": f"Tight window — {item.days_to_expiration} days. A 50% markdown drives fast sale.",
            "expected_result": "Item sold at half price. Partial revenue recovered. Waste avoided.",
            "financial_note": f"Hold = risk ${item.base_price:.2f} loss. Discount = recover ${saved:.2f}.",
            "partner": None,
        }
    else:
        return {**base,
            "action_type": "hold_price", "badge": "HOLD PRICE", "badge_class": "badge-hold",
            "reason": f"Fresh item — {item.days_to_expiration} days remaining. No action needed.",
            "expected_result": "Item sold at full price. Maximum revenue.",
            "financial_note": f"Full price: ${item.base_price:.2f}. No markdown required.",
            "partner": None,
        }

def _get_first_recommendation(inventory):
    on_shelf = sorted(
        [i for i in inventory if i.status == "on_shelf"],
        key=lambda i: _waste_risk(i), reverse=True
    )
    return _recommend_for_item(on_shelf[0]) if on_shelf else None

# ── Impact metrics ────────────────────────────────────────────────────────────
def _compute_impact(obs):
    donated = sum(1 for i in obs.inventory if i.status == "donated")
    return {
        "food_rescued":  donated,
        "meals_donated": round(donated * 2.5),
        "co2_saved_kg":  round(donated * 2.1, 1),
        "value_saved":   round(donated * 5.0, 2),
    }

# ── Build full state ──────────────────────────────────────────────────────────
def _build_state(obs, recommendation=None):
    impact = _compute_impact(obs)
    on_shelf_items = [i for i in obs.inventory if i.status == "on_shelf"]
    items_at_risk  = sum(1 for i in on_shelf_items if i.days_to_expiration <= 2)
    avg_risk       = round(sum(_waste_risk(i) for i in on_shelf_items) / max(len(on_shelf_items), 1))
    inv_list = sorted(
        [{**i.model_dump(), "risk_score": _waste_risk(i), "risk_label": _risk_label(_waste_risk(i))} for i in obs.inventory],
        key=lambda x: x["risk_score"], reverse=True
    )
    return {
        "current_day":          obs.current_day,
        "total_revenue":        round(_total_revenue, 2),
        "landfill_waste_count": obs.landfill_waste_count,
        "items_at_risk":        items_at_risk,
        "avg_risk_score":       avg_risk,
        "done":                 obs.done,
        "reward":               obs.reward,
        "current_event":        _current_event,
        "event_info":           EVENT_MODES[_current_event],
        "inventory":            inv_list,
        "recommendation":       recommendation,
        "history":              _history,
        "impact":               impact,
        "action_log":           _session_log[-20:],
    }

# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/api/reset", methods=["POST"])
def api_reset():
    global _obs, _history, _session_log, _total_revenue, _current_event
    data  = request.get_json(silent=True) or {}
    task  = data.get("task", "medium")
    event = data.get("event", "normal")
    _current_event = event if event in EVENT_MODES else "normal"
    _obs = _env.reset(task=task)
    delta = EVENT_MODES[_current_event]["expiry_delta"]
    if delta != 0:
        for item in _obs.inventory:
            item.days_to_expiration = max(1, item.days_to_expiration + delta)
    _history      = {"days": [], "waste": [], "revenue": [], "donations": [], "risk_avg": []}
    _session_log  = []
    _total_revenue = 0.0
    return jsonify(_build_state(_obs, _get_first_recommendation(_obs.inventory)))

def _record_step(obs, action_type, item_id, item_name, reward):
    global _total_revenue
    food_rescued = sum(1 for i in obs.inventory if i.status == "donated")
    on_shelf     = [i for i in obs.inventory if i.status == "on_shelf"]
    avg_risk     = round(sum(_waste_risk(i) for i in on_shelf) / max(len(on_shelf), 1))
    _history["days"].append(obs.current_day - 1)
    _history["waste"].append(obs.landfill_waste_count)
    _history["revenue"].append(round(_total_revenue, 2))
    _history["donations"].append(food_rescued)
    _history["risk_avg"].append(avg_risk)
    _session_log.append({
        "day": obs.current_day - 1, "item_id": item_id, "item_name": item_name,
        "action": action_type, "reward": round(reward, 4), "revenue": round(_total_revenue, 2),
    })

@app.route("/api/step", methods=["POST"])
def api_step():
    global _obs, _total_revenue
    if _obs is None: return jsonify({"error": "Press Reset first."}), 400
    if _obs.done:    return jsonify({"error": "Simulation complete.", "done": True}), 200
    rec = _get_first_recommendation(_obs.inventory)
    if not rec:      return jsonify({"error": "No items on shelf.", "done": True}), 200
    _obs, reward, done, _ = _env.step(PricingAction(item_id=rec["item_id"], action_type=rec["action_type"]))
    if rec["action_type"] == "hold_price":    _total_revenue += rec["base_price"]
    elif rec["action_type"] == "set_discount": _total_revenue += rec["base_price"] * 0.5
    _record_step(_obs, rec["action_type"], rec["item_id"], rec["item_name"], reward)
    return jsonify(_build_state(_obs, _get_first_recommendation(_obs.inventory)))

@app.route("/api/action", methods=["POST"])
def api_action():
    global _obs, _total_revenue
    if _obs is None: return jsonify({"error": "Simulation not started."}), 400
    data        = request.get_json()
    item_id     = data.get("item_id")
    action_type = data.get("action_type")
    item        = next((i for i in _obs.inventory if i.item_id == item_id), None)
    prev_price  = item.base_price if item else 5.0
    _obs, reward, done, _ = _env.step(PricingAction(item_id=item_id, action_type=action_type))
    if action_type == "hold_price":    _total_revenue += prev_price
    elif action_type == "set_discount": _total_revenue += prev_price * 0.5
    _record_step(_obs, action_type, item_id, item.name if item else "Unknown", reward)
    return jsonify(_build_state(_obs, _get_first_recommendation(_obs.inventory)))

@app.route("/api/recommend", methods=["POST"])
def api_recommend():
    if _obs is None: return jsonify({"error": "Simulation not started."}), 400
    data    = request.get_json()
    item_id = data.get("item_id")
    item    = next((i for i in _obs.inventory if i.item_id == item_id), None)
    if not item:               return jsonify({"error": "Item not found."}), 404
    if item.status != "on_shelf": return jsonify({"error": "Item not on shelf.", "status": item.status}), 400
    return jsonify(_recommend_for_item(item))

@app.route("/api/partners")
def api_partners():
    return jsonify(DONATION_PARTNERS)

@app.route("/api/whatif", methods=["POST"])
def api_whatif():
    if _obs is None: return jsonify({"error": "No simulation running."}), 400
    data             = request.get_json(silent=True) or {}
    demand_drop_pct  = max(0, min(100, data.get("demand_drop_pct", 30)))
    price_sens       = max(0.1, min(2.0, data.get("price_sensitivity", 1.0)))
    on_shelf         = [i for i in _obs.inventory if i.status == "on_shelf"]
    if not on_shelf: return jsonify({"error": "No items on shelf."}), 400

    sell_rate = max(0.0, 1.0 - demand_drop_pct / 100) * price_sens
    no_waste = no_rev = no_donate = rl_waste = rl_rev = rl_donate = 0

    for item in on_shelf:
        risk = _waste_risk(item)
        # Without RL
        if item.days_to_expiration <= 1: no_waste += 1
        elif random.random() < sell_rate: no_rev += item.base_price
        else: no_waste += 1
        # With RL
        if risk >= 80:   rl_donate += 1
        elif risk >= 40: rl_rev    += item.base_price * 0.5 * max(0.6, sell_rate)
        else:            rl_rev    += item.base_price * max(0.5, sell_rate)

    rl_waste = max(0, no_waste - rl_donate)
    return jsonify({
        "scenario":    {"demand_drop_pct": demand_drop_pct, "price_sensitivity": price_sens, "items": len(on_shelf)},
        "without_rl":  {"projected_waste": no_waste,  "projected_revenue": round(no_rev, 2),  "projected_donations": no_donate},
        "with_rl":     {"projected_waste": rl_waste,  "projected_revenue": round(rl_rev, 2),  "projected_donations": rl_donate,
                        "meals_saved": round(rl_donate * 2.5), "co2_saved_kg": round(rl_donate * 2.1, 1)},
        "delta":       {"waste_reduction": no_waste - rl_waste, "revenue_gain": round(rl_rev - no_rev, 2)},
    })

@app.route("/api/export")
def api_export():
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=["day","item_id","item_name","action","reward","revenue"])
    writer.writeheader()
    writer.writerows(_session_log)
    out.seek(0)
    fname = f"smart_food_rescue_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment;filename={fname}"})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
