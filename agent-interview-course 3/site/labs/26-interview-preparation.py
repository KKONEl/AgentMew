from dataclasses import dataclass

@dataclass(frozen=True)
class Record:
    topic: str
    score: int
    evidence: str
    revisit: str

records = [
    Record('architecture', 2, 'workflow comparison notes', '03,11,24'),
    Record('retrieval', 1, '', '07-10,24'),
    Record('recovery', 1, '', '15,16'),
    Record('security', 2, 'tenant isolation asserts', '18,20,24'),
    Record('collaboration', 2, 'gate stdout', '11,19,25'),
    Record('training', 1, '', '21'),
    Record('STAR', 2, 'project card with denominators', '24-26'),
    Record('failure', 2, 'before-after failure fixture', '19,20,25'),
]

def effective_score(record):
    if record.score not in range(4):
        raise ValueError('score must be 0..3')
    # A top score requires an evidence reference; this does not verify the evidence itself.
    return min(record.score, 2) if not record.evidence.strip() else record.score

scores = [effective_score(r) for r in records]
total = sum(scores)
critical_ok = all(effective_score(r)>=2 for r in records if r.topic in {'security','recovery'})
ready_for_next_mock = total >= 18 and critical_ok
weak = sorted((r for r in records if effective_score(r)<2), key=lambda r:(effective_score(r), r.topic))
assert total == 13 and not critical_ok and not ready_for_next_mock
assert effective_score(Record('test', 3, '', '21')) == 2
print(f'mock score={total}/24; critical topics ready={critical_ok}; next mock={ready_for_next_mock}')
for r in weak:
    print(f'revisit {r.topic}: lessons {r.revisit}; add one counterexample and evidence')
print('Teaching rubric only; no hiring probability is estimated.')
