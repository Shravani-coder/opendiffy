
#!/usr/bin/env python3
import os, sys, json, socket, subprocess, webbrowser
from datetime import datetime
from collections import Counter
from pymongo import MongoClient
import mysql.connector
from dotenv import load_dotenv
from dateutil.parser import parse as parse_date

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB  = os.getenv("MONGO_DB", "diffy_metrics")
MONGO_COL = os.getenv("MONGO_COL", "differenceResult")

MYSQL_CFG = {
    "host":     os.getenv("MYSQL_HOST", "localhost"),
    "user":     os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASS", "Shravani@12"),
    "database": os.getenv("MYSQL_DB", "diffy_metrics")
}

# --- Check if Flask app is running on port 5000 ---
def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0

if not is_port_open(5000):
    flask_path = os.path.join("diffy-test", "report_app.py")  
    subprocess.Popen(["python3", flask_path],
                     stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL)
    print(f"[{datetime.now()}] Launched report_app.py")
else:
    print(f"[{datetime.now()}] report_app.py already running.")

mongo = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
mongo.admin.command("ping")
coll = mongo[MONGO_DB][MONGO_COL]
runs_coll = mongo[MONGO_DB]["runs_to_process"]

db = mysql.connector.connect(**MYSQL_CFG)
db.autocommit = False
cur = db.cursor()

run_id = os.getenv("RUN_ID") or (sys.argv[1] if len(sys.argv) > 1 else None)
if not run_id:
    print("ERROR: run_id must be provided as an environment variable or command-line argument")
    sys.exit(1)

print(f"[{datetime.now()}] Ingesting run_id = {run_id}")

docs = list(coll.find({"runId": run_id}))
if not docs:
    print(f"No documents found for run_id: {run_id}")
    runs_coll.update_one(
        {"run_id": run_id},
        {"$set": {"status": "done", "completed_at": datetime.utcnow()}} 
    )
    sys.exit(0) 

IGNORABLE_FIELDS = {"timestamp", "request_id", "req_id", "created_at", "updated_at"}

total_reqs = len(docs)
total_diffs = 0
matched_fields = 0
num_requests_passed = 0
diff_types = Counter()
request_details = []


#duration between the first and last diff created during a run 
timestamps = []
for d in docs:
    ts = d.get("timestampMsec")
    if ts:
        try:
            timestamps.append(datetime.fromtimestamp(ts / 1000))
        except:
            continue

if timestamps:
    start = min(timestamps)
    end = max(timestamps)
    duration_ms = int((end - start).total_seconds() * 1000)
else:
    duration_ms = 0


# --- Analyze each diff doc ---
for d in docs: 
    diffs = d.get("differences") or []
    count = len(diffs)
    total_diffs += count 

    match_count = sum(
        1 for entry in diffs
        if isinstance(entry, dict) and json.loads(entry.get("difference", "{}")).get("type") == "NoDifference"
    )
    matched_fields += match_count

    type_count = Counter()
    for entry in diffs:
        if not isinstance(entry, dict):
            continue
        raw = entry.get("difference")
        try:
            p = json.loads(raw) if isinstance(raw, str) else raw
            t = p.get("type")
            if t:
                type_count[t] += 1
                diff_types[t] += 1
        except:
            continue

    if count == 0 or all(
        json.loads(entry.get("difference", "{}")).get("field", "").split(".")[-1] in IGNORABLE_FIELDS
        for entry in diffs if isinstance(entry, dict)
    ):
        num_requests_passed += 1

    request_details.append({
        "run_id": run_id,
        "request_id": str(d.get("_id")),
        "total_differences": count,
        "matched_fields": match_count,
        "diff_type_counts": dict(type_count),
        "diff_details": diffs
    })

unmatched_fields = total_diffs - matched_fields
pct_unmatched = round((unmatched_fields / total_diffs) * 100, 2) if total_diffs else 0.0

# --- Insert summary into 'runs' table ---
cur.execute("""
INSERT INTO runs (
  run_id, timestamp, total_requests, total_differences,
  matched_requests, num_requests_passed, pct_unmatched,
  diff_type_counts, diffs_json, run_duration_ms
) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
ON DUPLICATE KEY UPDATE  
  timestamp            = VALUES(timestamp),
  total_requests       = VALUES(total_requests),
  total_differences    = VALUES(total_differences),
  matched_requests     = VALUES(matched_requests),
  num_requests_passed  = VALUES(num_requests_passed),
  pct_unmatched        = VALUES(pct_unmatched),
  diff_type_counts     = VALUES(diff_type_counts),
  diffs_json           = VALUES(diffs_json),
  run_duration_ms      = VALUES(run_duration_ms);
""", (
    run_id,
    datetime.now(),
    total_reqs,
    total_diffs,
    matched_fields,
    num_requests_passed,
    pct_unmatched,
    json.dumps(diff_types),
    json.dumps([{"request_id": rd["request_id"], "total_differences": rd["total_differences"]} for rd in request_details]),
    duration_ms
))

# --- Insert individual diffs into 'request_diffs' table ---
for rd in request_details:
    cur.execute("""
    INSERT INTO request_diffs (
      run_id, request_id, total_differences, matched_fields, diff_details
    ) VALUES (%s,%s,%s,%s,%s)
    ON DUPLICATE KEY UPDATE
      total_differences = VALUES(total_differences),
      matched_fields    = VALUES(matched_fields),
      diff_details      = VALUES(diff_details);
    """, (
        rd["run_id"],
        rd["request_id"],
        rd["total_differences"],
        rd["matched_fields"],
        json.dumps(rd["diff_details"])
    ))

db.commit()

# --- Update Mongo run metadata ---
runs_coll.update_one(
    {"run_id": run_id},
    {"$set": {"status": "done", "completed_at": datetime.utcnow()}}
)

print(f"[{datetime.now()}]  Done run_id {run_id}: {total_reqs} requests, {total_diffs} diffs, {matched_fields} matched ({pct_unmatched}% unmatched)")
report_url = f"http://localhost:5000/report/{run_id}"
print(f"[{datetime.now()}] 📄 Opening report: {report_url}")
webbrowser.open_new_tab(report_url)
