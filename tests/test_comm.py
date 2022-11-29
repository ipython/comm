from comm.base_comm import CommManager, BaseComm
from traitlets import HasTraits


class MyComm(BaseComm):

    def publish_msg(self, msg_type, data=None, metadata=None, buffers=None, **keys):
        pass


def test_comm_manager():
    test = CommManager()
    assert isinstance(test, HasTraits)
    assert test.targets == {}


def test_base_comm():
    test = MyComm()
    assert test.target_name == "comm"