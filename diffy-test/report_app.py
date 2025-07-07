
import os
import json
from collections import defaultdict, Counter
from flask import Flask, render_template_string, send_from_directory, url_for
from dotenv import load_dotenv
import mysql.connector
from pymongo import MongoClient

load_dotenv()
app = Flask(__name__)

# --- Configuration ---
MYSQL_CFG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASS", "Shravani@12"),
    "database": os.getenv("MYSQL_DB", "diffy_metrics")
}

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB  = os.getenv("MONGO_DB", "diffy_metrics")
MONGO_COL = os.getenv("MONGO_COL", "differenceResult")


def get_db_connection():
    return mysql.connector.connect(**MYSQL_CFG)


@app.route('/report.css')
def serve_css():
    return send_from_directory('.', 'report.css', mimetype='text/css')


@app.route('/report/<run_id>')
def show_report(run_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM runs WHERE run_id = %s", (run_id,))
    run = cursor.fetchone()
    if not run:
        return f"Run ID '{run_id}' not found", 404

    cursor.execute(
        "SELECT request_id, total_differences, matched_fields, diff_details "
        "FROM request_diffs WHERE run_id = %s ORDER BY request_id",
        (run_id,)
    )
    raw_rows = cursor.fetchall()
    cursor.close()
    conn.close()

    per_request = []
    field_summary = defaultdict(Counter)
    field_details = defaultdict(lambda: defaultdict(list))

    for row in raw_rows:
        try:
            diffs_list = json.loads(row["diff_details"] or "[]")
        except:
            diffs_list = []

        type_ctr = Counter()
        type_groups = defaultdict(list)

        for entry in diffs_list:
            if not isinstance(entry, dict):
                continue
            try:
                diff_obj = json.loads(entry.get("difference", "{}"))
            except:
                continue
            if diff_obj.get("type") == "NoDifference":
                continue

            field = entry.get("field", "UnknownField")
            diff_type = diff_obj.get("type", "UnknownType")

            type_ctr[diff_type] += 1
            type_groups[diff_type].append({"field": field, "diff": diff_obj})
            field_summary[field][diff_type] += 1
            field_details[field][row["request_id"]].append(diff_obj)

        total_unmatched = sum(type_ctr.values())
        by_type = [
            {"type": t, "count": c,
             "percentage": round((c / total_unmatched) * 100, 1) if total_unmatched else 0,
             "entries": type_groups[t]}
            for t, c in type_ctr.items()
        ]

        per_request.append({
            "request_id": row["request_id"],
            "total_differences": row["total_differences"],
            "matched_fields": row["matched_fields"],
            "unmatched_differences": total_unmatched,
            "by_type": by_type
        })

    field_summary_list = []
    for field_name, ctr in field_summary.items():
        total = sum(ctr.values())
        breakdown = [{"type": t, "count": c,
                      "percentage": round((c / total) * 100, 1)}
                     for t, c in ctr.items()]
        field_summary_list.append({"field": field_name, "total": total, "breakdown": breakdown})
    field_summary_list.sort(key=lambda x: x["total"], reverse=True)

    field_request_diffs = []
    for field_name, req_map in field_details.items():
        req_list = [{"request_id": rid, "diffs": diffs} for rid, diffs in req_map.items()]
        field_request_diffs.append({"field": field_name, "requests": req_list})

    return render_template_string(HTML_TEMPLATE,
                                  run=run,
                                  requests=per_request,
                                  field_summary=field_summary_list,
                                  field_request_diffs=field_request_diffs)


@app.route('/request/<request_id>')
def show_request_detail(request_id):
    client = MongoClient(MONGO_URI)
    coll = client[MONGO_DB][MONGO_COL]
    try:
        doc = coll.find_one({"_id": request_id})
    except:
        return f"Invalid request_id: {request_id}", 400

    if not doc:
        return f"Request ID {request_id} not found", 404

    def safe_json(val):
        try:
            return json.loads(val) if isinstance(val, str) else val
        except:
            return val

    request_data = safe_json(doc.get("request", {}))
    run_id = request_data.get("run_id", "")

    responses = doc.get("responses", {})
    primary = safe_json(responses.get("primary", {}))
    candidate = safe_json(responses.get("candidate", {}))

    return render_template_string(REQUEST_DETAIL_TEMPLATE,
                                  request_id=request_id,
                                  run_id=run_id,
                                  request=request_data,
                                  primary=primary,
                                  candidate=candidate)



# At the end of your report_app.py — only showing the updated HTML_TEMPLATE part

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Diffy Run Report - {{ run.run_id }}</title>
  <link rel="stylesheet" href="{{ url_for('serve_css') }}">
  <script>
    function toggleSection(id, btn) {
      const el = document.getElementById(id);
      const show = el.style.display !== 'block';
      el.style.display = show ? 'block' : 'none';
      btn.innerText = show ? 'Hide' : 'Show';
    }
  </script>
  <style>
    body { font-family: sans-serif; background: #f0f0f0; padding: 20px; }
    h1, h2 { margin-top: 20px; }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; vertical-align: top; }
    th { background-color: #f8f8f8; }
    .toggle-button { padding: 4px 8px; margin-right: 6px; }
    .details-row { display: none; }
    .diff-json { background: #f5f5f5; padding: 6px; border-radius: 4px; margin: 4px 0; font-family: monospace; }
    .metadata span { display: inline-block; margin-right: 20px; }
    .request-block { margin: 8px 0; }
    .request-header { font-weight: bold; margin-bottom: 4px; }
  </style>
</head>
<body>
  <div class="container">
    <h1>Diffy Run Report</h1>
    <div class="metadata">
      <span>Run ID: {{ run.run_id }}</span>
      <span>Timestamp: {{ run.timestamp }}</span>
      <span>Total Requests: {{ run.total_requests }}</span>
      <span>Total Differences: {{ run.total_differences }}</span>
      <span>Passed Requests: {{ run.num_requests_passed }}</span>
      <span>Unmatched %: {{ run.pct_unmatched }}%</span>
      <span>Duration: {{ run.run_duration_ms }} ms</span>
    </div>

    <h2>Field‑wise Cumulative Summary</h2>
    {% if field_summary %}
    <table>
      <thead>
        <tr><th>Field</th><th>Total</th><th>Breakdown</th></tr>
      </thead>
      <tbody>
        {% for f in field_summary %}
        {% set fid = 'field_' ~ loop.index %}
        <tr>
          <td><button class="toggle-button" onclick="toggleSection('{{ fid }}', this)">Show</button> {{ f.field }}</td>
          <td>{{ f.total }}</td>
          <td>{% for b in f.breakdown %}<div>{{ b.type }}: {{ b.count }}</div>{% endfor %}</td>
        </tr>
        <tr id="{{ fid }}" class="details-row">
          <td colspan="3">
            {% for fr in field_request_diffs if fr.field == f.field %}
              {% for req in fr.requests %}
                <div class="request-block">
                  <div class="request-header">
                    Request <a href="/request/{{ req.request_id }}">{{ req.request_id }}</a>
                  </div>
                  {% for d in req.diffs %}
                    <pre class="diff-json">{ "left": "{{ d.left|default('') }}", "right": "{{ d.right|default('') }}", "type": "{{ d.type }}" }</pre>
                  {% endfor %}
                </div>
              {% endfor %}
            {% endfor %}
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
    {% else %}
      <p>No diffs.</p>
    {% endif %}

    <h2>Individual Request Diffs</h2>
    {% if requests %}
    <table>
      <thead><tr><th>Request ID</th><th>Total</th><th>Unmatched</th><th>By Type</th><th>Details</th></tr></thead>
      <tbody>
      {% for req in requests %}
        {% set rid = 'req_' ~ req.request_id %}
        <tr>
          <td>{{ req.request_id }}</td>
          <td>{{ req.total_differences }}</td>
          <td>{{ req.unmatched_differences }}</td>
          <td>
            {% for item in req.by_type %}
              <div>{{ item.type }} ({{ item.count }})</div>
            {% endfor %}
          </td>
          <td>
            <button class="toggle-button" onclick="toggleSection('{{ rid }}', this)">Show</button>
            <div id="{{ rid }}" class="details-row">
              {% for item in req.by_type %}
                <div class="detail-group">
                  <strong>{{ item.type }} ({{ item.count }})</strong>
                  {% for entry in item.entries %}
                    <pre class="diff-json">{ "field": "{{ entry.field }}", "left": "{{ entry.diff.left|default('') }}", "right": "{{ entry.diff.right|default('') }}" }</pre>
                  {% endfor %}
                </div>
              {% endfor %}
            </div>
          </td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
    {% else %}
      <p>No diff results found for this run.</p>
    {% endif %}
  </div>
</body>
</html>
"""

REQUEST_DETAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Request {{ request_id }}</title>
  <style>
    body { font-family: monospace; padding: 20px; background: #f9f9f9; }
    pre { background: #fff; padding: 10px; border-radius: 5px; box-shadow: 0 0 4px rgba(0,0,0,0.1); white-space: pre-wrap; word-wrap: break-word; }
    h2 { margin-top: 20px; }
    .split { display: flex; gap: 20px; }
    .column { flex: 1; }
    .back-button {
      display: inline-block;
      margin-bottom: 20px;
      padding: 8px 16px;
      background-color: #007bff;
      color: white;
      text-decoration: none;
      border-radius: 4px;
      font-size: 14px;
    }
  </style>
</head>
<body>
  <a href="{{ url_for('show_report', run_id=run_id) }}" class="back-button">Back</a>

  <h1>Details for Request ID: {{ request_id }}</h1>

  <h2>Request</h2>
  <pre>{{ request | tojson(indent=2) }}</pre>

  <div class="split">
    <div class="column">
      <h2>Primary Response</h2>
      <pre>{{ primary | tojson(indent=2) }}</pre>
    </div>
    <div class="column">
      <h2>Candidate Response</h2>
      <pre>{{ candidate | tojson(indent=2) }}</pre>
    </div>
  </div>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(debug=True, port=5000)
