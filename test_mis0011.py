import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend" / "src"))

from backend.pipeline import run_aiml

p = ROOT / "backend/data/generated/telemetry_20260905_024648_905564.csv"

df = pd.read_csv(p)
x = df[df["mission_id"] == "MIS-0011"]

print(
    "t | true_active | anomaly | fault_prob | health | RUL_s | status"
)
print("-" * 90)

for _, r in x.iterrows():

    result = run_aiml(r.to_dict())

    print(
        f"{int(r['timestamp_s']):2} | "
        f"{int(r['true_fault_active']):11} | "
        f"{float(result.get('anomaly_score') or 0):.3f} | "
        f"{float(result.get('fault_probability') or 0):.3f} | "
        f"{result.get('health_score')} | "
        f"{result.get('predicted_rul_seconds')} | "
        f"{result.get('rul_status')}"
    )