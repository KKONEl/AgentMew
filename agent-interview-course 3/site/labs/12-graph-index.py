edges = [
    ("张老师","指导","小李","doc1"),
    ("小李","参与","项目X","doc2"),
    ("项目X","资助方","研究所Y","doc3"),
]
students = {b for a,r,b,s in edges if a == "张老师" and r == "指导"}
funded = {a for a,r,b,s in edges if r == "资助方" and b == "研究所Y"}
hits = [(a,b,s) for a,r,b,s in edges if r == "参与" and a in students and b in funded]
assert hits == [("小李","项目X","doc2")]
print("小李 → 项目X → 研究所Y")
print("证据：doc1, doc2, doc3")
