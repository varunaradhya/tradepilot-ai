from __future__ import annotations
import json, hashlib
from sqlalchemy.orm import Session
from app.models.research_experiment import ResearchExperiment

def experiment_key(dataset_id: str, strategy_version: str, parameters: dict) -> str:
    payload=json.dumps({"dataset":dataset_id,"strategy":strategy_version,"parameters":parameters},sort_keys=True,separators=(",",":"))
    return hashlib.sha256(payload.encode()).hexdigest()[:48]

def record_experiment(db: Session, user_id: int, dataset_id: str, strategy_version: str, parameters: dict, result: dict) -> ResearchExperiment:
    key=experiment_key(dataset_id,strategy_version,parameters)
    row=db.query(ResearchExperiment).filter(ResearchExperiment.user_id==user_id,ResearchExperiment.experiment_key==key).first()
    if row is None:
        row=ResearchExperiment(user_id=user_id,experiment_key=key,dataset_id=dataset_id,strategy_version=strategy_version,parameters_json=json.dumps(parameters,sort_keys=True),result_json=json.dumps(result,sort_keys=True))
        db.add(row)
    else:
        row.result_json=json.dumps(result,sort_keys=True)
    db.commit(); db.refresh(row)
    return row

def list_experiments(db: Session, user_id: int, limit: int=50) -> list[dict]:
    rows=db.query(ResearchExperiment).filter(ResearchExperiment.user_id==user_id).order_by(ResearchExperiment.created_at.desc()).limit(limit).all()
    return [{"id":r.id,"experiment_key":r.experiment_key,"dataset_id":r.dataset_id,"strategy_version":r.strategy_version,"parameters":json.loads(r.parameters_json),"result":json.loads(r.result_json),"created_at":r.created_at} for r in rows]
