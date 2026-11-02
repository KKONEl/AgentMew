import math

def matmul(a, b):
    assert a and b and len(a[0]) == len(b)
    return [[sum(x*y for x,y in zip(row,col)) for col in zip(*b)] for row in a]

w = [[1, 0], [0, 1]]
a, b, x = [[1, 2]], [[1], [-1]], [[2], [3]]
base = matmul(w, x)
delta = matmul(b, matmul(a, x))
y = [[p[0]+q[0]] for p,q in zip(base, delta)]
assert y == [[10], [-5]]
d = k = 4096
rank = 8
full, lora = d*k, rank*(d+k)
assert lora == 65536 and lora < full
n = 7_000_000_000
static = n*(2+2+8+4)
quantized_weight_lower_bound = n/2
assert static == 112_000_000_000
chosen_logp, rejected_logp = -2.0, -4.0
ref_chosen, ref_rejected, beta = -3.0, -3.0, 0.1
margin = beta*((chosen_logp-rejected_logp)-(ref_chosen-ref_rejected))
loss = math.log1p(math.exp(-margin))
assert loss < math.log(2)
print('rank1 forward:', y)
print(f'full={full} lora={lora} ratio={100*lora/full:.6f}%')
print(f'assumed static training={static/1e9:.1f} GB; no activations included')
print(f'4-bit raw weights lower bound={quantized_weight_lower_bound/1e9:.1f} GB')
print(f'DPO pair loss={loss:.6f}; baseline={math.log(2):.6f}')
