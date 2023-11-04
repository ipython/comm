from typing import Any
from comm.base_comm import BaseComm, CommManager


class MyComm(BaseComm):
    def publish_msg(self, msg_type:str, data:Any=None, metadata:Any=None, buffers:Any=None, **keys:Any) ->None:
        pass


def test_comm_manager() -> None:
    test = CommManager()
    assert test.targets == {}


def test_base_comm() -> None:
    test = MyComm()
    assert test.target_name == "comm"
