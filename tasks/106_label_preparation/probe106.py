"""One fixed claim-only TF-IDF/logistic probe, patient-grouped CV; local text only.

The classifier, vocabulary and clinical strings are never printed or published.
This diagnoses shortcut availability and screening associations, not 9B quality.
"""
from collections import Counter
import argparse
import json
from pathlib import Path
import sys

import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, matthews_corrcoef, precision_recall_fscore_support
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline

from data106 import ROOT, OUT, PRIVATE, LABELS, digest, put, putl, read, rows, sha


def metrics(records, field="prediction"):
    truth=[r["GT"] for r in records]
    pred=[r[field] for r in records]
    p,r,f,n=precision_recall_fscore_support(truth,pred,labels=list(LABELS),zero_division=0)
    nonS=sum(t!=LABELS[0] for t in truth)
    falseS=sum(t!=LABELS[0] and h==LABELS[0] for t,h in zip(truth,pred))
    mcc=0. if len(set(truth))<2 else float(matthews_corrcoef(truth,pred))
    return dict(N=len(records),patients=len({r["sid"] for r in records}),MCC=mcc,
        PA=float(accuracy_score(truth,pred)),Macro_F1=float(f1_score(truth,pred,labels=list(LABELS),average="macro",zero_division=0)),
        false_S=falseS,nonS=nonS,false_S_rate=falseS/nonS if nonS else None,
        predicted_counts=dict(Counter(pred)),confusion_matrix=confusion_matrix(truth,pred,labels=list(LABELS)).tolist(),
        classes={lab:dict(precision=float(p[i]),recall=float(r[i]),F1=float(f[i]),N=int(n[i])) for i,lab in enumerate(LABELS)})


def cv(scope, pool, fold_of_patient):
    result=[]
    diagnostics=[]
    for fold in range(5):
        train=[r for r in pool if fold_of_patient[r["sid"]]!=fold]
        test=[r for r in pool if fold_of_patient[r["sid"]]==fold]
        assert {r["sid"] for r in train}.isdisjoint({r["sid"] for r in test})
        model=make_pipeline(TfidfVectorizer(lowercase=True,ngram_range=(1,2),min_df=2,max_features=30000,sublinear_tf=True),
            LogisticRegression(C=1.,max_iter=1000,solver="lbfgs",random_state=106))
        model.fit([r["claim"] for r in train],[r["GT"] for r in train])
        pred=model.predict([r["claim"] for r in test]).tolist()
        dummy=DummyClassifier(strategy="most_frequent")
        dummy.fit(np.zeros((len(train),1)),[r["GT"] for r in train])
        majority=dummy.predict(np.zeros((len(test),1))).tolist()
        seen_claims={digest(" ".join(r["claim"].lower().split())) for r in train}
        diagnostics.append(dict(fold=fold,train_N=len(train),test_N=len(test),train_patients=len({r["sid"] for r in train}),
            test_patients=len({r["sid"] for r in test}),normalized_exact_claim_seen_in_other_patient_train=sum(digest(" ".join(r["claim"].lower().split())) in seen_claims for r in test),
            vocabulary_size=len(model[0].vocabulary_),GT_train=dict(Counter(r["GT"] for r in train)),GT_test=dict(Counter(r["GT"] for r in test))))
        for row,guess,baseline in zip(test,pred,majority):
            result.append(dict(scope=scope,id=row["id"],sid=row["sid"],GT=row["GT"],author=row["author"],
                prediction=guess,majority_prediction=baseline,fold=fold))
    assert len(result)==len(pool) and len({r["id"] for r in result})==len(result)
    return result,diagnostics


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summarize-existing',action='store_true',help='Reuse fixed OOF predictions; fit no models')
    args=parser.parse_args()
    pool=rows(PRIVATE/"training_pool.jsonl")
    allowed=set(read(ROOT/"outputs/103_lora_selection/patient_roles.json")["patients"]["train"])
    assert len(pool)==3675 and {r["sid"] for r in pool}==allowed
    index=rows(OUT/"data_pool_index.jsonl")
    byid={r["id"]:r for r in index}
    split=StratifiedGroupKFold(n_splits=5,shuffle=True,random_state=106)
    folds={}
    for fold,(_,test) in enumerate(split.split(np.zeros(len(pool)),[r["GT"] for r in pool],[r["sid"] for r in pool])):
        for i in test:
            sid=pool[int(i)]["sid"]
            assert sid not in folds or folds[sid]==fold
            folds[sid]=fold
    existing=rows(OUT/'probe_predictions.jsonl') if args.summarize_existing else None
    if existing is not None:
        prior=read(OUT/'probe_results.json')
        assert prior['source_files']['training_pool.jsonl']==sha(PRIVATE/'training_pool.jsonl')
        original={r['id']:r for r in pool}
        assert all(all(r[k]==original[r['id']][k] for k in ('GT','sid','author')) for r in existing)
    all_predictions=[]
    experiments={}
    for scope,subset in (("full_pool3675",pool),("retained104_196",[r for r in pool if byid[r["id"]]["retained104"]])):
        if existing is None:
            predictions,diagnostics=cv(scope,subset,folds)
        else:
            predictions=[r for r in existing if r['scope']==scope]
            assert {r['id'] for r in predictions}=={r['id'] for r in subset}
            diagnostics=prior['experiments'][scope]['folds']
        all_predictions+=predictions
        experiments[scope]=dict(probe=metrics(predictions),majority=metrics(predictions,"majority_prediction"),folds=diagnostics)
        if scope=="full_pool3675":
            candidate_ids={arm:{r['id'] for r in rows(PRIVATE/f'{arm}.jsonl')} for arm in ('ordinary_sample','boundary_cover')}
            groups=dict(retained104_196=lambda r:byid[r["id"]]["retained104"],
                isolated104=lambda r:byid[r["id"]]["semantic104_status"] in ("unresolved","reference_gap"),
                unresolved104=lambda r:byid[r['id']]['semantic104_status']=='unresolved',
                original103_512=lambda r:byid[r["id"]]["original103_512"],
                unreviewed104_224S=lambda r:byid[r["id"]]["original103_512"] and byid[r["id"]]["semantic104_status"]=="not_reviewed104",
                human=lambda r:r["author"]=="human",llm=lambda r:r["author"]=="llm")
            groups.update({arm:(lambda r,arm=arm:r['id'] in candidate_ids[arm]) for arm in candidate_ids})
            experiments[scope]["same_OOF_predictions_subset_metrics"]={name:dict(probe=metrics([r for r in predictions if rule(r)]),majority=metrics([r for r in predictions if rule(r)],"majority_prediction")) for name,rule in groups.items()}
            experiments[scope]['same_OOF_subset_by_GT']={name:{gt:dict(N=sum(rule(r) and r['GT']==gt for r in predictions),
                correct=sum(rule(r) and r['GT']==gt and r['prediction']==gt for r in predictions),
                false_S=sum(rule(r) and r['GT']==gt and gt!=LABELS[0] and r['prediction']==LABELS[0] for r in predictions),
                prediction_counts=dict(Counter(r['prediction'] for r in predictions if rule(r) and r['GT']==gt))) for gt in LABELS} for name,rule in groups.items()}
    putl(OUT/"probe_predictions.jsonl",all_predictions)
    put(OUT/"probe_results.json",dict(task=106,fixed_probe=dict(vectorizer="TF-IDF word unigrams+bigrams",min_df=2,max_features=30000,sublinear_tf=True,
        classifier="LogisticRegression",C=1.,solver="lbfgs",max_iter=1000,class_weight=None,random_state=106,
        split="StratifiedGroupKFold5; mapping fixed from full training pool then reused for 196",vocabulary_fit_within_training_fold=True,
        parameters_searched=0),patient_folds=folds,experiments=experiments,
        existing_OOF_reused_without_refitting=args.summarize_existing,
        conclusions_allowed="Availability of claim-only signals and screening association under patient-grouped CV; 196 training-size comparison is confounded by smaller data and class mix",
        conclusions_forbidden=["9B fine-tuning performance prediction","clinical effectiveness","proof of causal selection bias","evidence-understanding ability"],
        source_files={"training_pool.jsonl":sha(PRIVATE/"training_pool.jsonl"),"data_pool_index.jsonl":sha(OUT/"data_pool_index.jsonl"),"probe106.py":sha(Path(__file__))},
        clinical_text_printed=False,confirmation_text_labels_predictions_read=False,new_API_calls=0,model_weights_loaded=False,GPU_calls=0))
    print(json.dumps({scope:{name:dict(MCC=values[name]["MCC"],PA=values[name]["PA"],false_S=values[name]["false_S"]) for name in ("probe","majority")} for scope,values in experiments.items()}))


if __name__=="__main__":main()
