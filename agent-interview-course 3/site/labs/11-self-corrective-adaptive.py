def decide(scores):
    if all(s >= 0.8 for s in scores) and scores:
        return "refine"
    if not scores or max(scores) < 0.3:
        return "fallback"
    return "combine"

for scores in ([0.9,0.85], [0.1,0.2], [0.9,0.2], []):
    print(decide(scores))
assert decide([0.9,0.2]) == "combine"
assert decide([]) == "fallback"
