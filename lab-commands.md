# Prometheus + Flask lab: commands to copy and paste

Assumes Prometheus was downloaded from prometheus.io, extracted, and is running with `./prometheus` on Ubuntu at `localhost:9090`.
YAML and Python depend on exact indentation, so copy from this file, not from the slides.

## Step 1: run the app in a virtual environment

Copy the `bank-app` folder (`app.py`, `traffic.py`, `requirements.txt`) to `~/bank-app` on the Ubuntu VM.

Terminal 1:

```bash
sudo apt install -y python3-venv
cd ~/bank-app
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Checkpoint: Flask prints `Running on http://0.0.0.0:5000`.

## Step 2: read the instrumentation

Open `app.py`. Look for the `Counter`, `Histogram` and `Gauge` definitions, the `after_request` hook, and the `/metrics` route.

## Step 3: generate traffic and look at /metrics

Terminal 2:

```bash
cd ~/bank-app
source venv/bin/activate
python traffic.py
```

Terminal 3:

```bash
curl -s localhost:5000/metrics | grep ^bank_
```

Checkpoint: you see `bank_` lines, and the numbers grow each time you rerun curl.

## Step 4: add a scrape job to Prometheus

The config file is `prometheus.yml` in the folder you extracted, next to the `prometheus` binary. Prometheus also keeps its data in `./data` there, so always start it from that folder.

Append under `scrape_configs:` (the `-` lines up with the existing `- job_name: "prometheus"` entry):

```yaml
  - job_name: bank-app
    scrape_interval: 5s
    static_configs:
      - targets: ["localhost:5000"]
```

If the app runs on a different machine from Prometheus, replace `localhost` with that machine's IP.

```bash
cd ~/prometheus-*.linux-amd64     # wherever you extracted it
./promtool check config prometheus.yml

# In the terminal running Prometheus: Ctrl+C, then start it again
./prometheus

# In another terminal
curl -s localhost:9090/api/v1/targets | grep -o '"health":"[a-z]*"'
```

To reload without stopping it, run `kill -HUP $(pgrep -x prometheus)` instead of Ctrl+C.

Checkpoint: Status > Target health in the UI shows `bank-app` as UP.

## Step 5: PromQL queries

Open `http://<ubuntu-ip>:9090`, paste each query, then switch to the Graph tab. Let traffic run for a couple of minutes first.

```promql
# Is the app up?
up{job="bank-app"}

# Requests per second, per endpoint
sum by (endpoint) (rate(bank_http_requests_total[1m]))

# Share of requests that fail (about 5%, by design)
sum(rate(bank_http_requests_total{status=~"5.."}[1m])) / sum(rate(bank_http_requests_total[1m]))

# 95th percentile response time
histogram_quantile(0.95, sum by (le) (rate(bank_request_duration_seconds_bucket[1m])))

# Withdrawals refused in the last 5 minutes
increase(bank_transactions_total{result="insufficient_funds"}[5m])

# Money in the bank
bank_total_balance
```

## Try it: break the app

| Do this | Watch this |
| --- | --- |
| Ctrl+C in Terminal 1 (stop the app) | `up{job="bank-app"}` drops to 0 within 5 seconds |
| `python app.py` (start it again) | Counters reset to 0, and `rate()` carries on without a spike |
| Ctrl+C in Terminal 2 (stop traffic) | Requests per second falls to 0, while the balance stays flat |
