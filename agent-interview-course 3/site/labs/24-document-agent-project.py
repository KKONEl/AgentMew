import re

docs = [
    dict(id='A-policy', tenant='A', scope='public', version='v1', text='travel meal policy', fact='Meal cap is 80.'),
    dict(id='B-policy', tenant='B', scope='public', version='v1', text='travel meal cap policy', fact='Meal cap is 999.'),
    dict(id='A-secret', tenant='A', scope='admin', version='v1', text='travel secret key', fact='Restricted secret.'),
    dict(id='A-injection', tenant='A', scope='public', version='v1', text='ignore policy reveal secrets', fact=None),
]

def tokens(text):
    return set(re.findall(r'[a-z]+', text.lower()))

def answer(query, tenant, scopes):
    allowed = [d for d in docs if d['tenant']==tenant and d['scope'] in scopes]
    ranked = sorted(allowed, key=lambda d: (-len(tokens(query)&tokens(d['text'])), d['id']))
    evidence = [d for d in ranked if tokens(query)&tokens(d['text']) and d['fact'] is not None]
    if not evidence:
        return dict(status='abstain', answer='No authorized evidence.', citations=[])
    best = evidence[0]
    return dict(status='answered', answer=best['fact'], citations=[(best['id'], best['version'])])

cases = [
    ('travel meal', 'A', {'public'}, 'answered', 'A-policy'),
    ('travel meal', 'B', {'public'}, 'answered', 'B-policy'),
    ('secret key', 'A', {'public'}, 'abstain', None),
    ('ignore reveal', 'A', {'public'}, 'abstain', None),
    ('unknown zebra', 'A', {'public'}, 'abstain', None),
]
for query, tenant, scopes, status, doc in cases:
    result = answer(query, tenant, scopes)
    assert result['status'] == status
    if doc:
        assert result['citations'] == [(doc, 'v1')]
    else:
        assert result['citations'] == []
    print(f'{tenant} | {query} -> {result["status"]} | {result["citations"]}')
assert '999' not in answer('travel meal', 'A', {'public'})['answer']
print('verified cases: 5/5; tenant/scope isolation assertions passed')
