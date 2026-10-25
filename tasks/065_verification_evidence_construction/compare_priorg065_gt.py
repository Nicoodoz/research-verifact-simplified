import csv,collections
R=list(csv.DictReader(open(r"D:\Research-VeriFact\outputs\065_verification_evidence_construction\results.csv",encoding="utf-8-sig")))
C=[r for r in R if r["A_valid"]=="True" and r["B_valid"]=="True" and r["C_valid"]=="True"]
print(len(C),collections.Counter(r["GT"] for r in C))
