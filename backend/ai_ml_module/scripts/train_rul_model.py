"""Train the Phase 6 RUL model."""
from __future__ import annotations
from pathlib import Path
import sys, numpy as np, pandas as pd
from sklearn.metrics import mean_absolute_error,mean_squared_error,r2_score
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from src.rul.rul_model import RULRegressor,get_rul_feature_columns
TRAIN_PATH=ROOT/"data/features/train.csv"; VAL_PATH=ROOT/"data/features/val.csv"; MODEL_PATH=ROOT/"models/rul/rul_regressor.joblib"
def main():
    if not TRAIN_PATH.exists(): raise FileNotFoundError(f"Training features not found: {TRAIN_PATH}\nRun scripts/build_features.py first.")
    if not VAL_PATH.exists(): raise FileNotFoundError(f"Validation features not found: {VAL_PATH}\nRun scripts/build_features.py first.")
    train_df=pd.read_csv(TRAIN_PATH); val_df=pd.read_csv(VAL_PATH); cols=get_rul_feature_columns(train_df)
    model=RULRegressor().fit(train_df,cols)
    yv=pd.to_numeric(val_df["true_rul_seconds"],errors="coerce"); mask=np.isfinite(yv)&(yv>=0)
    if not mask.any(): raise ValueError("Validation set contains no valid RUL rows.")
    val=val_df.loc[mask].copy(); y=yv.loc[mask].to_numpy(float); pred=model.predict(val); err=np.abs(y-pred)
    print("="*70); print("RUL MODEL — PHASE 6"); print("="*70); print(f"Train rows: {len(train_df):,}"); print(f"Validation RUL rows: {len(val):,}"); print(f"Features: {len(cols)}"); print(f"MAE seconds: {mean_absolute_error(y,pred):.3f}"); print(f"RMSE seconds: {np.sqrt(mean_squared_error(y,pred)):.3f}"); print(f"R²: {r2_score(y,pred):.4f}"); print(f"Median absolute error: {np.median(err):.3f}s"); print(f"90th percentile error: {np.percentile(err,90):.3f}s"); MODEL_PATH.parent.mkdir(parents=True,exist_ok=True); model.save(MODEL_PATH); print(f"Saved model: {MODEL_PATH}")
if __name__=="__main__": main()
