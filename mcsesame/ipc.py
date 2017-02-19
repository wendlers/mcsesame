import config
import posix_ipc


class MessageQueue:

    def __init__(self, queue=config.MQ_SESAME, create=False, destroy=False):

        self.destroy = destroy

        if create:
            flags = posix_ipc.O_CREX
        else:
            flags = posix_ipc.O_CREAT

        self.mq = posix_ipc.MessageQueue(queue, flags=flags)

    def __del__(self):

        try:

            self.mq.close()

            if self.destroy:
                self.mq.unlink()

        except:
            pass

    def send_open(self, ip):

        try:
            self.mq.send("O!%s" % ip, 0)
        except posix_ipc.BusyError:
            pass

    def send_close(self, ip):
        try:
            self.mq.send("C!%s" % ip, 0)
        except posix_ipc.BusyError:
            pass

    def process_incoming(self, handler_open, handler_close):

        message, _ = self.mq.receive()

        if isinstance(message, str):
            if message.startswith("O!"):
                handler_open(message[2:])
            elif message.startswith("C!"):
                handler_close(message[2:])
