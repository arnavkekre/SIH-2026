"""
Usage:
    python scripts/generate_demo_data.py --missions 20 --out data/synthetic
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.data.synthetic_generator import generate_dataset

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--missions", type=int, default=80,
                         help="More missions than before since each is now much shorter (60 rows vs ~500)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=str, default="data/synthetic")
    parser.add_argument("--duration", type=float, default=1.0, help="Mission length in minutes")
    parser.add_argument("--interval", type=float, default=1.0, help="Sample interval in seconds (1.0 = 1 Hz)")
    args = parser.parse_args()

    df = generate_dataset(
        n_missions=args.missions, seed=args.seed, out_dir=args.out,
        duration_min=args.duration, sample_interval_s=args.interval,
    )
    print(f"\nGenerated {df['mission_id'].nunique()} missions -> {len(df)} rows")
    print(f"Saved per-mission CSVs + combined_dataset.csv to: {args.out}/")
    print("\nFault type distribution (rows, not missions):")
    print(df["true_fault_type"].value_counts())
