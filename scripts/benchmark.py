from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (accuracy_score,precision_score,recall_score,f1_score,
                             average_precision_score,roc_auc_score,brier_score_loss,confusion_matrix)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from joblib import dump
from transitiq.archive import fetch_koi_table,prepare_training_data

def run(data_path=None):
    frame=fetch_koi_table(data_path or "data/koi_cumulative.csv")
    X,y,groups,features=prepare_training_data(frame)
    valid=X.notna().sum(axis=1)>0; X,y,groups=X.loc[valid],y.loc[valid],groups.loc[valid]
    split=GroupShuffleSplit(n_splits=1,test_size=.25,random_state=2026)
    train_idx,test_idx=next(split.split(X,y,groups))
    Xtr,Xte=X.iloc[train_idx],X.iloc[test_idx]; ytr,yte=y.iloc[train_idx],y.iloc[test_idx]
    models={
      "logistic_baseline":make_pipeline(SimpleImputer(strategy="median",add_indicator=True),StandardScaler(),LogisticRegression(class_weight="balanced",max_iter=2000,random_state=2026)),
      "random_forest":make_pipeline(SimpleImputer(strategy="median",add_indicator=True),RandomForestClassifier(n_estimators=400,min_samples_leaf=3,class_weight="balanced_subsample",max_features="sqrt",n_jobs=-1,random_state=2026))}
    metrics={"dataset":"NASA Exoplanet Archive cumulative KOI table","sample_rows":len(X),"positive_class":"CONFIRMED or CANDIDATE","negative_class":"FALSE POSITIVE","feature_columns":features,"group_key":"kepid","test_fraction":.25,"random_state":2026,"class_counts":y.value_counts().to_dict(),"test_class_counts":yte.value_counts().to_dict(),"models":{}}
    for name,pipe in models.items():
        pipe.fit(Xtr,ytr); pred=pipe.predict(Xte); prob=pipe.predict_proba(Xte)[:,1]
        metrics["models"][name]={"accuracy":accuracy_score(yte,pred),"precision":precision_score(yte,pred,zero_division=0),"recall":recall_score(yte,pred,zero_division=0),"f1":f1_score(yte,pred,zero_division=0),"pr_auc":average_precision_score(yte,prob),"roc_auc":roc_auc_score(yte,prob) if yte.nunique()>1 else None,"brier_score":brier_score_loss(yte,prob),"confusion_matrix_tn_fp_fn_tp":confusion_matrix(yte,pred,labels=[0,1]).ravel().tolist()}
    # A separate calibration hold-out comes from training groups only.
    inner=GroupShuffleSplit(n_splits=1,test_size=.2,random_state=2027)
    fit_i,cal_i=next(inner.split(Xtr,ytr,groups.iloc[train_idx]))
    calibrator=CalibratedClassifierCV(models["random_forest"],method="sigmoid",cv="prefit")
    calibrator.fit(Xtr.iloc[cal_i],ytr.iloc[cal_i])
    cp=calibrator.predict_proba(Xte)[:,1]
    metrics["calibrated_random_forest"]={"calibration":"sigmoid held-out subset from training stars","test_brier_score":brier_score_loss(yte,cp),"test_pr_auc":average_precision_score(yte,cp)}
    Path("models/artifacts").mkdir(parents=True,exist_ok=True); Path("outputs").mkdir(exist_ok=True)
    dump({"model":calibrator,"features":features,"provenance":metrics},"models/artifacts/koi_classifier.joblib")
    Path("outputs/benchmark_results.json").write_text(json.dumps(metrics,indent=2,default=float),encoding="utf-8")
    print(json.dumps(metrics,indent=2,default=float)); return metrics
if __name__=="__main__": run()

