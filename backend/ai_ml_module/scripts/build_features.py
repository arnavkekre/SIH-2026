"""
Usage:
    python scripts/build_features.py --in data/synthetic/combined_dataset.csv --out data/features
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.features.feature_pipeline import build_features, get_model_feature_columns
from src.data.splitter import split_missions, split_summary
import pandas as pd

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="input_path", type=str, default="data/synthetic/combined_dataset.csv")
    parser.add_argument("--out", type=str, default="data/features")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)

    print(f"Loading {args.input_path} ...")
    raw = pd.read_csv(args.input_path)
    print(f"Raw: {len(raw)} rows, {raw['mission_id'].nunique()} missions")

    print("Building features ...")
    featured = build_features(raw)
    feature_cols = get_model_feature_columns(featured)
    print(f"Featured: {len(featured)} rows, {len(feature_cols)} model-ready feature columns")

    print("Splitting by mission (stratified, no temporal leakage) ...")
    train_df, val_df, test_df = split_missions(featured, seed=args.seed)
    print(split_summary(train_df, val_df, test_df).to_string(index=False))

    train_df.to_csv(f"{args.out}/train.csv", index=False)
    val_df.to_csv(f"{args.out}/val.csv", index=False)
    test_df.to_csv(f"{args.out}/test.csv", index=False)

    with open(f"{args.out}/feature_columns.txt", "w") as f:
        f.write("\n".join(feature_cols))

    print(f"\nSaved train.csv / val.csv / test.csv / feature_columns.txt to {args.out}/")
