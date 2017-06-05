import logging

import threading
import time
import ipc

logger = logging.getLogger(__name__)


class GateKeeper(threading.Thread):

    def __init__(self, player_timeout=30):

        threading.Thread.__init__(self)

        self.player_timeout = player_timeout
        self.running = False

        self.sesame_open_for = {}

        self.mq = ipc.MessageQueue()
        self.daemon = True

    def open_sesame_for(self, remote_addr):

        if remote_addr not in self.sesame_open_for:

            self.mq.send_open(remote_addr)

        self.sesame_open_for[remote_addr] = {"timeout": self.player_timeout}
        logger.info("opened sesame for: %s" % remote_addr)

    def close_sesame_for(self, remote_addr):

        if remote_addr in self.sesame_open_for:

            self.mq.send_close(remote_addr)

            logger.info("sesame closed for: %s" % remote_addr)

            del self.sesame_open_for[remote_addr]

        else:
            logger.info("already closed for: %s" % remote_addr)

    def stop(self):

        self.running = False

    def run(self):

        self.running = True

        countdown = 0

        while self.running:

            if countdown > 0:
                countdown -= 1
                time.sleep(1)
                continue
            else:
                countdown = 10

            logger.info("wake-up for player check")

            for remote_addr, data in self.sesame_open_for.items():

                logger.info("checking: %s" % remote_addr)

                data["timeout"] -= 1

                logger.info("timeout for %s is now: %d" %
                            (remote_addr, data["timeout"]))

                if data["timeout"] == 0:
                    logger.info("%s has timed out" % remote_addr)
                    self.close_sesame_for(remote_addr)


if __name__ == "__main__":

    c = GateKeeper()
    c.start()

    raw_input("press ENTER to stop")

    c.stop()
    c.join()
