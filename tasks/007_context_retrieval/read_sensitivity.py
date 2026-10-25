"""Display all sensitivity answers and only evidence not already read in main unions."""
import argparse
import json
import prepare as p

base=p.OUT/"zero_budget_sensitivity_001"
inputs=p.pilot.jsonl(base/"inputs.jsonl")
answers=p.pilot.jsonl(base/"normalized_responses.jsonl")
known={x["passage_id"]:x for path in (p.OUT/"run_001/review_001/reference_unions").glob("*.json") for x in json.loads(path.read_text(encoding="utf-8"))}
parser=argparse.ArgumentParser()
parser.add_argument("mode",choices=["outputs","evidence"])
parser.add_argument("--start",type=int,default=0)
parser.add_argument("--count",type=int,default=30)
args=parser.parse_args()
if args.mode=="outputs":
    for item in inputs:
        packet=json.loads((p.OUT/"run_001/review_001/packets"/(item["case_id"]+".json")).read_text(encoding="utf-8"))
        print(item["case_id"],"GT",packet["case"]["human_gt"],"CLAIM",item["text"])
        for answer in answers:
            if answer["proposition_id"]==item["proposition_id"]:
                print(answer["arm"]+": "+answer["output_text"])
else:
    new={}
    for item in inputs:
        for arm,result in item["retrieval"].items():
            for span in result["passages"]:
                pid=span["passage_id"]
                if pid in known and known[pid]["end_exclusive"]>=span["end_exclusive"]:
                    continue
                if pid not in new or new[pid]["end_exclusive"]<span["end_exclusive"]:
                    new[pid]=span
    ordered=sorted(new.values(),key=lambda x:(x["subject_id"],x["date"],x["time"],x["note_id"],x["start"]))
    for i,x in enumerate(ordered[args.start:args.start+args.count],args.start):
        print(f"[{i}] patient {x['subject_id']} note {x['note_id']} {x['date']} raw [{x['start']},{x['end_exclusive']}) {x['text']}")
    print("END",args.start,min(args.start+args.count,len(ordered)),"TOTAL ADDITIONAL",len(ordered))
