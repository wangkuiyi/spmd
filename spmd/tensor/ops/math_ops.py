import torch
from torch.distributed.distributed_c10d import (
    ReduceOp
)
from spmd.tensor.api import Tensor
from spmd.tensor.placement_types import Shard, Replicate, _Partial
from spmd.tensor.ops.utils import register_impl

@register_impl("aten.sum.default")
def dist_sum(types, args=(), kwargs=None):
    input = args[0]
    local_input = input.local_tensor()
    input_placement = input.placements[0]
    device_mesh = input.device_mesh

    local_sum = local_input.sum()

    if isinstance(input_placement, Shard) or isinstance(input_placement, _Partial):
        placements = [_Partial(ReduceOp.SUM)]
        # partial reduce
        partial_sum = Tensor.from_local(local_sum, device_mesh, placements)
        # all_reduce across device
        placements[0] = Replicate()
        return partial_sum.redistribute(device_mesh, placements)
    elif isinstance(input_placement, Replicate):
        return Tensor.from_local(local_sum, device_mesh=device_mesh, placements=input.placements)
    else:
        raise RuntimeError("Not supported!")
