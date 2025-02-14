import torch
from torch.distributed.distributed_c10d import (
    get_rank,
    ReduceOp,
    ProcessGroup,
    ProcessGroupGloo,
    ProcessGroupNCCL,
    _get_default_group
)

# autograd enabled collective
from torch.distributed.nn.functional import (
    _all_gather_base,
    all_reduce,
    broadcast,
    scatter
)

_global_device_mesh = None

def get_global_device_mesh():
    global _global_device_mesh
    return _global_device_mesh

def set_global_device_mesh(mesh):
    global _global_device_mesh
    _global_device_mesh = mesh

class DeviceMesh(object):
    '''
    Device Mesh object, can be used as a context manager.
    By default describes the device ids, layout and serves
    as a proxy for communication among the device lists.

    We use the default ProcessGroup in this DeviceMesh class
    to implement proper communications. Note that we also
    add collective wrappers in this class. This is used to
    decouple detailed communication backend with the underlying
    DistributedTensor implementation.
    '''
    device_type: str
    mesh: torch.Tensor
    # _world_pg: ProcessGroup

    def __init__(self, device_type, mesh):
        self.device_type = device_type
        self.mesh = torch.Tensor(mesh)

        default_pg = _get_default_group()
        if device_type == "cpu":
            assert isinstance(default_pg, ProcessGroupGloo), f"ProcessGroup {type(default_pg)} not supporting CPU!"
        elif device_type == "cuda":
            assert isinstance(default_pg, ProcessGroupNCCL) or isinstance(default_pg, ProcessGroupGloo)
        else:
            raise RuntimeError(f"DeviceMesh only support cpu or cuda device type, but got {device_type}")

        # TODO: support multi-dimensional device mesh
        assert self.mesh.ndim == 1, "Only support 1-d device mesh for now"

    def __enter__(self):
        # set global device_mesh to this instance
        set_global_device_mesh(self)
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        # unset global device mesh
        set_global_device_mesh(None)

    def __repr__(self):
        return f"DeviceMesh:({self.mesh})"

    def size(self, dim=0):
        return self.mesh.size(dim)

    @property
    def ndim(self):
        return self.mesh.ndim

    def get_rank(self):
        return get_rank()

    def scatter(self, tensors, src=0) -> torch.Tensor:
        current_rank = get_rank()
        return scatter(tensors, src=src)

    def broadcast(self, tensor, src=0):
        return broadcast(tensor, src=src)

    # def all_gather(self, tensor_list, tensor):
    #     return all_gather(tensor_list, tensor)

    def all_gather_base(self, output_tensor, tensor):
        return _all_gather_base(output_tensor, tensor)

    def all_reduce(self, tensor, op=ReduceOp.SUM):
        return all_reduce(tensor, op=op)
