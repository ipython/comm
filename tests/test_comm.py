from comm.base_comm import CommManager, BaseComm


class MyComm(BaseComm):

    def publish_msg(self, msg_type, data=None, metadata=None, buffers=None, **keys):
        pass


def test_comm_manager():
    test = CommManager()
    assert test.targets == {}


def test_base_comm():
    test = MyComm()
    assert test.target_name == "comm"