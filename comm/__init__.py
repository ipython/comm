"""Comm package.

Copyright (c) IPython Development Team.
Distributed under the terms of the Modified BSD License.

This package provides a way to register a Kernel Comm implementation, as per the Jupyter kernel protocol.
It also provides a base Comm implementation and a default CommManager for the IPython case.
"""

__version__ = "0.1.0"
__all__ = [
    "register_comm_classes",
    "create_comm",
    "create_comm_manager",
    "get_comm_manager",
    "__version__",
]

COMM_PROVIDER = None

CommCls = None
CommManagerCls = None

comm_manager = None


def register_comm_classes(comm_cls, comm_manager_cls):
    """Register Comm and CommManager classes.

    This allows kernels to provide their own Comm and CommManager implementations.
    """
    global CommCls
    global CommManagerCls

    CommCls = comm_cls
    CommManagerCls = comm_manager_cls


def create_comm(*args, **kwargs):
    """Create a comm."""
    if comm_manager is None:
        raise RuntimeError(
            "Cannot create a Comm if no Comm manager is currently registered."
        )

    return CommCls(*args, **kwargs)


def create_comm_manager(*args, **kwargs):
    """Register the current Comm manager."""
    if CommManagerCls is None:
        raise RuntimeError(
            "Cannot create a CommManager instance if no CommManager class is currently registered."
        )

    global comm_manager

    comm_manager = CommManagerCls(*args, **kwargs)

    return comm_manager


def get_comm_manager():
    """Get the current Comm manager, returns None if there is none."""
    global comm_manager

    return comm_manager
