from collections import defaultdict

def rrf(lists, c=60):
    scores = defaultdict(float)
    for ranking in lists:
        for rank, doc in enumerate(dict.fromkeys(ranking), 1):
            scores[doc] += 1 / (c + rank)
    return sorted(scores.items(), key=lambda x: (-x[1], x[0]))

result = rrf([["A","B","C"],["B","C","A"]])
assert result[0][0] == "B"
for doc, score in result:
    print(doc, f"{score:.6f}")
