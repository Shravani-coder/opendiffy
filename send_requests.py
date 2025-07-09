
#!/usr/bin/env python3
import uuid
import json
import os
import time
import subprocess
import requests
from pymongo import MongoClient
from datetime import datetime, timedelta

# --- Configuration ---
DIFFY_PROXY_URL = os.getenv("DIFFY_PROXY_URL", "http://localhost:8880")
REQUESTS_FILE   = os.getenv("REQUESTS_FILE",    "./multiple_reqs2.json")
MONGO_URI       = os.getenv("MONGO_URI",        "mongodb://localhost:27017")
DB_NAME         = os.getenv("DB_NAME",          "diffy_metrics")
POLL_INTERVAL   = float(os.getenv("POLL_INTERVAL", "1"))    # seconds
IDLE_TIMEOUT    = float(os.getenv("IDLE_TIMEOUT",  "5"))    # idle threshold in seconds

# Send a single request
def send_request(req_def, run_id):
    name    = req_def.get("name", "Unnamed")
    path    = req_def["path"]
    method  = req_def.get("method", "GET").upper()
    headers = req_def.get("headers", {}).copy()
    headers["X-Run-Id"] = run_id
    body    = req_def.get("body")
    url     = f"{DIFFY_PROXY_URL}{path}"

    fn = getattr(requests, method.lower(), None)
    if fn is None:
        print(f"Unsupported method {method} for {name}")
        return

    try:
        resp = fn(url, headers=headers, json=body, timeout=10) #each request being sent
        print(f"[{resp.status_code}] {method} {path} ({name})")
    except Exception as e:
        print(f" Error {method} {path}: {e}")

def wait_for_diffs(diff_col, run_id, total_expected=None):
    prev_cnt    = 0
    last_change = datetime.utcnow()

    print(f" Waiting for diffs for run_id={run_id} (idle timeout = {IDLE_TIMEOUT}s)...")

    while True:
        cnt = diff_col.count_documents({"runId": run_id})
        now = datetime.utcnow()

        if cnt != prev_cnt:
            print(f" {cnt} diffs received (∆ {cnt - prev_cnt})")
            prev_cnt    = cnt
            last_change = now
        else:
            idle = (now - last_change).total_seconds()
            print(f" Idle for {idle:.1f}s — total diffs: {cnt}", end="\r")

            if idle >= IDLE_TIMEOUT:
                print(f"\n No new diffs for {IDLE_TIMEOUT}s. Run considered complete.")
                break

        time.sleep(POLL_INTERVAL)

    return cnt

def main():
    # Load requests
    if not os.path.exists(REQUESTS_FILE):
        print(f"{REQUESTS_FILE} not found")
        return

    with open(REQUESTS_FILE) as f:
        reqs = json.load(f)

    total = len(reqs)
    if total == 0:
        print("No requests to send.")
        return

    run_id = str(uuid.uuid4())
    print(f" run_id = {run_id}")

    # Send all requests with same run_id
    for r in reqs:
        send_request(r, run_id)
        time.sleep(0.05)  # avoid overload

    # Wait for diffs to be written
    client   = MongoClient(MONGO_URI)
    diff_col = client[DB_NAME]["differenceResult"]
    run_col  = client[DB_NAME]["runs_to_process"]

    diff_count = wait_for_diffs(diff_col, run_id, total_expected=total)
    pass_count = total - diff_count

    # Insert metadata into runs_to_process
    run_col.insert_one({
        "run_id":         run_id,
        "status":         "pending",
        "created_at":     datetime.utcnow(),
        "requested_by":   os.getenv("USER", "unknown"),
        "total_requests": total,
        "diff_count":     diff_count,
        "pass_count":     pass_count,
        "notes":          f"{diff_count}/{total} requests had diffs"
    })

    print(f" Run metadata saved. {diff_count} diffs, {pass_count} passed.")

    # Trigger ingestion
    print(" Launching ingest_stats.py")
    subprocess.run(["python3", "ingest_stats.py", run_id], check=True)
    print("Ingestion triggered.")

if __name__ == "__main__":
    main()
