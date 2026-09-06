"""Runtime RUL predictor for SIH PS54."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import numpy as np, pandas as pd
from .rul_model import RULRegressor
@dataclass
class RULPrediction:
    rul_seconds:float; rul_minutes:float; status:str
class RULPredictor:
    def __init__(self,model_path:str|Path)->None: self.model=RULRegressor.load(model_path)
    def predict_row(self,row:dict)->RULPrediction:
        value=max(0.0,float(self.model.predict(pd.DataFrame([row]))[0]))
        status="CRITICAL" if value<=10 else ("WARNING" if value<=30 else "NORMAL")
        return RULPrediction(round(value,2),round(value/60,2),status)
    def predict_dataframe(self,df:pd.DataFrame)->pd.DataFrame:
        v=self.model.predict(df); return pd.DataFrame({"predicted_rul_seconds":np.round(v,2),"predicted_rul_minutes":np.round(v/60,2)},index=df.index)
