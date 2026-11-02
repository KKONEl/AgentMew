class Registry:
    def __init__(self):
        self.items, self.active = {}, None
    def propose(self, version, source, scope):
        if version in self.items:
            raise ValueError('duplicate version')
        self.items[version] = dict(status='proposed', source=source, scope=scope)
    def evaluate(self, version, regression_ok, permission_ok):
        item = self.items[version]
        if item['status'] != 'proposed':
            raise ValueError('invalid evaluation transition')
        item['status'] = 'approved' if regression_ok and permission_ok else 'rejected'
    def activate(self, version):
        if self.items[version]['status'] != 'approved':
            raise ValueError('approval required')
        old = self.active
        if old is not None:
            self.items[old]['status'] = 'deprecated'
        self.items[version]['status'] = 'active'
        self.active = version
        return old
    def rollback(self, version):
        if self.items[version]['status'] != 'deprecated':
            raise ValueError('rollback target unavailable')
        self.items[self.active]['status'] = 'deprecated'
        self.items[version]['status'] = 'active'
        self.active = version

r = Registry()
r.propose('v1', 'run-001', 'repo-a')
try:
    r.activate('v1')
    raise AssertionError('unreviewed activation')
except ValueError:
    pass
r.evaluate('v1', True, True); r.activate('v1')
r.propose('v2-bad', 'run-002', 'repo-a')
r.evaluate('v2-bad', True, False)
try:
    r.activate('v2-bad')
    raise AssertionError('permission expansion')
except ValueError:
    pass
r.propose('v2', 'run-003', 'repo-a')
r.evaluate('v2', True, True)
assert r.activate('v2') == 'v1'
assert r.items['v1']['status'] == 'deprecated'
r.rollback('v1')
assert r.active == 'v1'
assert sum(i['status']=='active' for i in r.items.values()) == 1
assert r.items['v2-bad']['status'] == 'rejected'
print('active:', r.active)
print('states:', {k:v['status'] for k,v in r.items.items()})
print('blocked: unreviewed activation and permission expansion')
