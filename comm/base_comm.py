"""Default classes for Comm and CommManager, for usage in IPython.
"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

import uuid

import logging

from IPython import get_ipython

from traitlets.config import LoggingConfigurable
from traitlets.utils.importstring import import_item
from traitlets import Any, Unicode, Bytes, Bool, Dict, Any, default

from comm import get_comm_manager


class BaseComm(LoggingConfigurable):
    """Class for communicating between a Frontend and a Kernel

    Must be subclassed with a publish_msg method implementation which
    sends comm messages through the iopub channel.
    """

    comm_id = Unicode()

    @default("comm_id")
    def _default_comm_id(self):
        return uuid.uuid4().hex

    primary = Bool(True, help="Am I the primary or secondary Comm?")

    target_name = Unicode("comm")
    target_module = Unicode(
        None,
        allow_none=True,
        help="""requirejs module from
        which to load comm target.""",
    )

    topic = Bytes()

    @default("topic")
    def _default_topic(self):
        return ("comm-%s" % self.comm_id).encode("ascii")

    _open_data = Dict(help="data dict, if any, to be included in comm_open")
    _close_data = Dict(help="data dict, if any, to be included in comm_close")

    _msg_callback = Any()
    _close_callback = Any()

    _closed = Bool(True)

    def __init__(
        self, target_name="", data=None, metadata=None, buffers=None, **kwargs
    ):
        if target_name:
            kwargs["target_name"] = target_name
        super(BaseComm, self).__init__(**kwargs)

        if self.primary:
            # I am primary, open my peer.
            self.open(data=data, metadata=metadata, buffers=buffers)
        else:
            self._closed = False

    def publish_msg(self, msg_type, data=None, metadata=None, buffers=None, **keys):
        raise NotImplementedError("publish_msg Comm method is not implemented")

    def __del__(self):
        """trigger close on gc"""
        self.close(deleting=True)

    # publishing messages

    def open(self, data=None, metadata=None, buffers=None):
        """Open the frontend-side version of this comm"""
        if data is None:
            data = self._open_data
        comm_manager = get_comm_manager()
        if comm_manager is None:
            raise RuntimeError("Comms cannot be opened without a comm_manager.")

        comm_manager.register_comm(self)
        try:
            self.publish_msg(
                "comm_open",
                data=data,
                metadata=metadata,
                buffers=buffers,
                target_name=self.target_name,
                target_module=self.target_module,
            )
            self._closed = False
        except Exception:
            comm_manager.unregister_comm(self)
            raise

    def close(self, data=None, metadata=None, buffers=None, deleting=False):
        """Close the frontend-side version of this comm"""
        if self._closed:
            # only close once
            return
        self._closed = True
        if data is None:
            data = self._close_data
        self.publish_msg(
            "comm_close",
            data=data,
            metadata=metadata,
            buffers=buffers,
        )
        if not deleting:
            # If deleting, the comm can't be registered
            get_comm_manager().unregister_comm(self)

    def send(self, data=None, metadata=None, buffers=None):
        """Send a message to the frontend-side version of this comm"""
        self.publish_msg(
            "comm_msg",
            data=data,
            metadata=metadata,
            buffers=buffers,
        )

    # registering callbacks

    def on_close(self, callback):
        """Register a callback for comm_close

        Will be called with the `data` of the close message.

        Call `on_close(None)` to disable an existing callback.
        """
        self._close_callback = callback

    def on_msg(self, callback):
        """Register a callback for comm_msg

        Will be called with the `data` of any comm_msg messages.

        Call `on_msg(None)` to disable an existing callback.
        """
        self._msg_callback = callback

    # handling of incoming messages

    def handle_close(self, msg):
        """Handle a comm_close message"""
        self.log.debug("handle_close[%s](%s)", self.comm_id, msg)
        if self._close_callback:
            self._close_callback(msg)

    def handle_msg(self, msg):
        """Handle a comm_msg message"""
        self.log.debug("handle_msg[%s](%s)", self.comm_id, msg)
        if self._msg_callback:
            shell = get_ipython()
            if shell:
                shell.events.trigger("pre_execute")
            self._msg_callback(msg)
            if shell:
                shell.events.trigger("post_execute")


class CommManager(LoggingConfigurable):
    """Default CommManager singleton implementation for Comms in the Kernel"""

    comms = Dict()
    targets = Dict()

    # Public APIs

    def register_target(self, target_name, f):
        """Register a callable f for a given target name

        f will be called with two arguments when a comm_open message is received with `target`:

        - the Comm instance
        - the `comm_open` message itself.

        f can be a Python callable or an import string for one.
        """
        if isinstance(f, str):
            f = import_item(f)

        self.targets[target_name] = f

    def unregister_target(self, target_name, f):
        """Unregister a callable registered with register_target"""
        return self.targets.pop(target_name)

    def register_comm(self, comm):
        """Register a new comm"""
        comm_id = comm.comm_id
        self.comms[comm_id] = comm
        return comm_id

    def unregister_comm(self, comm):
        """Unregister a comm, and close its counterpart"""
        # unlike get_comm, this should raise a KeyError
        comm = self.comms.pop(comm.comm_id)

    def get_comm(self, comm_id):
        """Get a comm with a particular id

        Returns the comm if found, otherwise None.

        This will not raise an error,
        it will log messages if the comm cannot be found.
        """
        try:
            return self.comms[comm_id]
        except KeyError:
            self.log.warning("No such comm: %s", comm_id)
            if self.log.isEnabledFor(logging.DEBUG):
                # don't create the list of keys if debug messages aren't enabled
                self.log.debug("Current comms: %s", list(self.comms.keys()))

    # Message handlers

    def comm_open(self, stream, ident, msg):
        """Handler for comm_open messages"""
        from comm import create_comm

        content = msg["content"]
        comm_id = content["comm_id"]
        target_name = content["target_name"]
        f = self.targets.get(target_name, None)
        comm = create_comm(
            comm_id=comm_id,
            primary=False,
            target_name=target_name,
        )
        self.register_comm(comm)
        if f is None:
            self.log.error("No such comm target registered: %s", target_name)
        else:
            try:
                f(comm, msg)
                return
            except Exception:
                self.log.error(
                    "Exception opening comm with target: %s", target_name, exc_info=True
                )

        # Failure.
        try:
            comm.close()
        except Exception:
            self.log.error(
                """Could not close comm during `comm_open` failure
                clean-up.  The comm may not have been opened yet.""",
                exc_info=True,
            )

    def comm_msg(self, stream, ident, msg):
        """Handler for comm_msg messages"""
        content = msg["content"]
        comm_id = content["comm_id"]
        comm = self.get_comm(comm_id)
        if comm is None:
            return

        try:
            comm.handle_msg(msg)
        except Exception:
            self.log.error("Exception in comm_msg for %s", comm_id, exc_info=True)

    def comm_close(self, stream, ident, msg):
        """Handler for comm_close messages"""
        content = msg["content"]
        comm_id = content["comm_id"]
        comm = self.get_comm(comm_id)
        if comm is None:
            return

        self.comms[comm_id]._closed = True
        del self.comms[comm_id]

        try:
            comm.handle_close(msg)
        except Exception:
            self.log.error("Exception in comm_close for %s", comm_id, exc_info=True)


__all__ = ["CommManager", "BaseComm"]
