"""A tiny dummy bank app, instrumented for Prometheus.

Run:  python app.py      then open http://localhost:5000/metrics
"""
import random
import time

from flask import Flask, Response, g, jsonify, request
from prometheus_client import (CONTENT_TYPE_LATEST, Counter, Gauge, Histogram,
                               disable_created_metrics, generate_latest)

disable_created_metrics()  # hide the extra *_created series to keep /metrics readable

app = Flask(__name__)

# In-memory "database"
accounts = {"alice": 1000.0, "bob": 500.0, "carol": 250.0}

# ---- Prometheus metrics -------------------------------------------------
# Counter: only goes up. Read it with rate().
REQUESTS = Counter(
    "bank_http_requests_total", "HTTP requests received",
    ["method", "endpoint", "status"],
)
# Histogram: counts request durations into buckets. Read it with histogram_quantile().
LATENCY = Histogram(
    "bank_request_duration_seconds", "Request duration in seconds",
    ["endpoint"],
)
# Counter with a business label: how many deposits/withdrawals happened.
TRANSACTIONS = Counter(
    "bank_transactions_total", "Banking transactions",
    ["type", "result"],
)
# Gauge: goes up and down. Read the raw value.
TOTAL_BALANCE = Gauge("bank_total_balance", "Sum of all account balances")
TOTAL_BALANCE.set_function(lambda: sum(accounts.values()))


@app.before_request
def start_timer():
    g.start_time = time.time()


@app.after_request
def record_metrics(response):
    if request.path != "/metrics":
        endpoint = request.url_rule.rule if request.url_rule else "unknown"
        LATENCY.labels(endpoint).observe(time.time() - g.start_time)
        REQUESTS.labels(request.method, endpoint, response.status_code).inc()
    return response


def fake_work():
    """Simulate a slow database call and the occasional crash."""
    time.sleep(random.uniform(0.01, 0.3))
    if random.random() < 0.05:
        raise RuntimeError("database timeout")


# ---- Bank endpoints -----------------------------------------------------
@app.route("/")
def home():
    return jsonify(app="dummy bank", endpoints=["/balance/<name>", "/deposit", "/withdraw", "/metrics"])


@app.route("/balance/<name>")
def balance(name):
    fake_work()
    if name not in accounts:
        return jsonify(error="no such account"), 404
    return jsonify(account=name, balance=accounts[name])


@app.route("/deposit", methods=["POST"])
def deposit():
    fake_work()
    data = request.get_json(force=True)
    name, amount = data["account"], float(data["amount"])
    accounts[name] = accounts.get(name, 0) + amount
    TRANSACTIONS.labels("deposit", "ok").inc()
    return jsonify(account=name, balance=accounts[name])


@app.route("/withdraw", methods=["POST"])
def withdraw():
    fake_work()
    data = request.get_json(force=True)
    name, amount = data["account"], float(data["amount"])
    if accounts.get(name, 0) < amount:
        TRANSACTIONS.labels("withdraw", "insufficient_funds").inc()
        return jsonify(error="insufficient funds"), 400
    accounts[name] -= amount
    TRANSACTIONS.labels("withdraw", "ok").inc()
    return jsonify(account=name, balance=accounts[name])


@app.errorhandler(RuntimeError)
def server_error(err):
    return jsonify(error=str(err)), 500


# ---- The endpoint Prometheus scrapes ------------------------------------
@app.route("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
