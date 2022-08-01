# Comm

It provides a way to register a Kernel Comm implementation, as per the Jupyter kernel protocol.
It also provides a base Comm implementation and a default CommManager that can be used.

## Register a comm implementation in the kernel:

### Case 1: Using the default CommManager and the BaseComm implementations

We provide default implementations for usage in IPython:

```python
from comm.base_comm import BaseComm, CommManager
from comm import register_comm_classes


class MyCustomComm(BaseComm):

    def publish_msg(self, msg_type, data=None, metadata=None, buffers=None, **keys):
        # TODO implement the logic for sending comm messages through the iopub channel
        pass


register_comm_classes(MyCustomComm, CommManager)
```

This is typically what ipykernel and JupyterLite's pyolite will do.

### Case 2: Providing your own comms implementation

You can register your own ``Comm`` and ``CommManager`` class implementations:

```python
from comm import register_comm_classes

register_comm_classes(MyCustomComm, MyCustomCommManager)
```

This is typically what xeus-python does (it has its own implementation using xeus's C++ messaging logic).

## Comm users

Libraries like ipywidgets can then use the comms implementation that has been registered by the kernel:

```python
from comm import create_comm

# Create a comm
comm = create_comm()
```
