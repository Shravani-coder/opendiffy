#!/usr/bin/env python3
import requests

url = "http://localhost:8880/test-diff"
headers = {"X-Run-ID": "simple_test_run"}

resp = requests.get(url, headers=headers, timeout=10)
print("Status:", resp.status_code)
print("Body:", resp.text)
