from collections import defaultdict, OrderedDict
import heapq

texts = ['agent tool policy', 'rag retrieval evidence', 'agent retrieval']
index = defaultdict(set)
for doc_id, text in enumerate(texts):
    for token in set(text.split()):
        index[token].add(doc_id)

def search(query, k):
    if k <= 0:
        return []
    scores = defaultdict(int)
    for token in set(query.split()):
        for doc_id in index.get(token, ()):
            scores[doc_id] += 1
    heap = []
    for doc_id, score in scores.items():
        item = (score, -doc_id)
        if len(heap) < k:
            heapq.heappush(heap, item)
        elif item > heap[0]:
            heapq.heapreplace(heap, item)
    return [-neg_id for score, neg_id in sorted(heap, reverse=True)]

class LRU:
    def __init__(self, capacity):
        if capacity < 0:
            raise ValueError('capacity must be nonnegative')
        self.capacity, self.data = capacity, OrderedDict()
    def get(self, key):
        if key not in self.data:
            raise KeyError(key)
        self.data.move_to_end(key)
        return self.data[key]
    def put(self, key, value):
        if self.capacity == 0:
            return
        self.data[key] = value
        self.data.move_to_end(key)
        while len(self.data) > self.capacity:
            self.data.popitem(last=False)

class Queue:
    def __init__(self, capacity):
        self.capacity, self.heap, self.seq, self.cancelled = capacity, [], 0, set()
    def push(self, task, priority):
        if len(self.heap) >= self.capacity:
            raise OverflowError('backpressure')
        heapq.heappush(self.heap, (priority, self.seq, task))
        self.seq += 1
    def pop(self):
        while self.heap:
            _, _, task = heapq.heappop(self.heap)
            if task not in self.cancelled:
                return task
        raise IndexError('empty')

assert search('agent retrieval', 2) == [2, 0]
assert search('missing', 4) == [] and search('agent', 0) == []
cache = LRU(2)
cache.put('a', 1); cache.put('b', 2)
assert cache.get('a') == 1
cache.put('c', 3)
assert list(cache.data) == ['a', 'c']
zero = LRU(0); zero.put('a', 1); assert not zero.data
q = Queue(3)
q.push('ordinary', 5); q.push('urgent-a', 1); q.push('urgent-b', 1)
try:
    q.push('overflow', 0)
    raise AssertionError('must reject')
except OverflowError:
    pass
q.cancelled.add('ordinary')
order = [q.pop(), q.pop()]
assert order == ['urgent-a', 'urgent-b']
try:
    q.pop()
    raise AssertionError('cancelled task ran')
except IndexError:
    pass
print('top2:', search('agent retrieval', 2))
print('LRU keys:', list(cache.data))
print('scheduled:', order)
print('edge checks: empty, zero-capacity, backpressure, cancellation passed')
