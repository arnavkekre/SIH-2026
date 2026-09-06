"""Phase 6 RUL regression model for SIH PS54."""
from __future__ import annotations
from pathlib import Path
from typing import Iterable
import joblib, numpy as np, pandas as pd
from xgboost import XGBRegressor
TARGET="true_rul_seconds"
FORBIDDEN_EXACT={"engine_id","mission_id","true_fault_type","true_fault_active","true_severity","true_effective_severity","true_degradation_health","eol_timestamp_s","true_rul_seconds"}
MODEL_DEFAULTS={"objective":"reg:squarederror","n_estimators":500,"max_depth":6,"learning_rate":0.05,"subsample":0.90,"colsample_bytree":0.90,"min_child_weight":3,"reg_alpha":0.05,"reg_lambda":1.0,"random_state":42,"n_jobs":-1}

def get_rul_feature_columns(df:pd.DataFrame)->list[str]:
    cols=[]
    for c in df.columns:
        if c in FORBIDDEN_EXACT or c.startswith("true_") or c.startswith("eol_"): continue
        if pd.api.types.is_numeric_dtype(df[c]): cols.append(c)
    if not cols: raise ValueError("No numeric RUL features found.")
    return cols

def prepare_rul_training_data(df:pd.DataFrame,feature_columns:Iterable[str]|None=None):
    if TARGET not in df.columns: raise ValueError(f"Missing required target column: {TARGET}")
    yraw=pd.to_numeric(df[TARGET],errors="coerce")
    work=df.loc[np.isfinite(yraw)&(yraw>=0)].copy()
    if len(work)<10: raise ValueError(f"Only {len(work)} valid RUL rows found; need at least 10.")
    cols=list(feature_columns) if feature_columns is not None else get_rul_feature_columns(work)
    missing=[c for c in cols if c not in work.columns]
    if missing: raise ValueError(f"Missing RUL feature columns: {missing[:20]}")
    X=work[cols].apply(pd.to_numeric,errors="coerce").replace([np.inf,-np.inf],np.nan).fillna(0.0)
    y=pd.to_numeric(work[TARGET],errors="coerce").clip(lower=0).astype(float)
    return X,y,cols

class RULRegressor:
    def __init__(self,params:dict|None=None)->None:
        self.params=dict(MODEL_DEFAULTS); self.params.update(params or {}); self.model=XGBRegressor(**self.params); self.feature_columns_:list[str]=[]
    def fit(self,train_df:pd.DataFrame,feature_columns:Iterable[str]|None=None)->"RULRegressor":
        X,y,cols=prepare_rul_training_data(train_df,feature_columns); self.feature_columns_=cols; self.model.fit(X,y); return self
    def predict(self,df:pd.DataFrame)->np.ndarray:
        if not self.feature_columns_: raise RuntimeError("RULRegressor must be fitted before prediction.")
        missing=[c for c in self.feature_columns_ if c not in df.columns]
        if missing: raise ValueError(f"Missing RUL feature columns: {missing[:20]}")
        X=df[self.feature_columns_].apply(pd.to_numeric,errors="coerce").replace([np.inf,-np.inf],np.nan).fillna(0.0)
        return np.maximum(self.model.predict(X),0.0)
    def save(self,path:str|Path)->None:
        path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); joblib.dump({"model":self.model,"feature_columns":self.feature_columns_,"params":self.params},path)
    @classmethod
    def load(cls,path:str|Path)->"RULRegressor":
        p=joblib.load(path); obj=cls(params=p.get("params")); obj.model=p["model"]; obj.feature_columns_=list(p["feature_columns"]); return obj
