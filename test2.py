import torch
from torch._C import dtype

out = torch.eye(5)
print('out: ', out)

adj = torch.tensor([
    [0, 0, 1, 1],
    [0, 0, 1, 0],
    [1, 1, 0, 0],
    [1, 0, 0, 0]
], dtype=float)

diagonal = torch.diag(torch.sum(adj, 1))
print('diagonal: ', diagonal)
out = diagonal.inverse().sqrt()
print('out: ', out)

