"""Query qTest API for real defect field IDs."""
import sys
import json
import requests
sys.path.insert(0, "Qtest_connection")
from Defect import QTEST_HOST, QTEST_TOKEN, QTEST_PROJECT_ID

url = f"https://{QTEST_HOST}/api/v3/projects/{QTEST_PROJECT_ID}/settings/defects/fields"
headers = {"Authorization": f"Bearer {QTEST_TOKEN}", "Accept": "application/json"}
r = requests.get(url, headers=headers, verify=False, timeout=10)
print(f"Status: {r.status_code}")
if r.ok:
    fields = r.json()
    print(f"Total fields: {len(fields)}")
    for f in fields:
        fid   = f.get("id", "?")
        label = f.get("label", "")
        dtype = f.get("data_type", "")
        req   = f.get("required", False)
        allowed = f.get("allowed_values", [])
        print(f"  id={str(fid):<6}  label={str(label):<30}  type={str(dtype):<15}  required={req}")
        for av in allowed[:5]:
            print(f"           option_id={av.get('value','?'):<8}  name={av.get('label','')}")
else:
    print(r.text[:1000])
