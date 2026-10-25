"""Display locally matched reference spans for diagnostic reading only."""
import json
import re
from pathlib import Path

path = Path(__file__).resolve().parents[2] / "outputs/070_fixed_evidence_reasoning_diagnosis/casebook_full.jsonl"
terms = {
    "024c4356": r"6 units|4 units|hct 23|hct 21",
    "07bc350d": r"ortho|trauma|TSICU|radiology suite",
    "77f77737": r"retention|urine|u/o|foley",
    "29d4ddd3": r"transfus|PRBC|POD|low u|decreased urine|bolus",
    "906828d7": r"discharg|post.?op|POD|Admission End",
    "38a920f8": r"10-18|10-15|effusion|lobe",
    "434bed80": r"24 hour|24hr|24 h|stuttering|troponin|transfer",
    "ccb46441": r"renally dos|renal dose|dose medication",
    "9f1073c2": r"multidisciplin|discuss|surgeon|son",
    "fa9a579f": r"nephrostomy|large|adequate output|pink",
    "0ad8dc66": r"stent|angioplast|balloon",
    "4c537558": r"altered mental|presented|A&O",
    "a9f518eb": r"B-Blocker|Beta-blocker|initiated|Cont ASA",
    "a52e6343": r"VA ICU|transfer|return",
}
for line in path.open(encoding="utf-8"):
    row = json.loads(line)
    short = row["id"][:8]
    print("\nCASE", short, row["claim"])
    pattern = re.compile(terms[short], re.IGNORECASE)
    ref = row["reference"].replace("\n", " ")
    spans = []
    for match in pattern.finditer(ref):
        a, b = max(0, match.start() - 85), min(len(ref), match.end() + 130)
        if spans and a <= spans[-1][1]:
            spans[-1] = (spans[-1][0], max(b, spans[-1][1]))
        else:
            spans.append((a, b))
    for a, b in spans[:16]:
        print(" ", ref[a:b])
    print("MATCHES", len(spans))
