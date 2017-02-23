import logging

import threading
import time
import mcserver
import ipc

logger = logging.getLogger(__name__)


class GateKeeper(threading.Thread):

    def __init__(self, player_timeout=10):

        threading.Thread.__init__(self)

        self.player_timeout = player_timeout
        self.mcs = mcserver.McServer()
        self.running = False

        self.mcs_data = {"version": None, "players": []}
        self.sesame_open_for = {}

        self.mq = ipc.MessageQueue()
        self.daemon = True

    def open_sesame_for(self, mcuser, remote_addr, admin=False):

        if mcuser not in self.sesame_open_for:

            self.mcs.whitelist_add(mcuser)

            if admin:
                self.mcs.op_add(mcuser)
                logger.info("made %s an operator" % mcuser)

            self.mq.send_open(remote_addr)
            self.sesame_open_for[mcuser] = {"remote_addr": remote_addr, "timeout": self.player_timeout}

            logger.info("opened sesame for: %s (%s)" % (mcuser, remote_addr))

        else:
            logger.info("sesame already open for: %s (%s)" % (mcuser, remote_addr))

    def close_sesame_for(self, mcuser):

        if mcuser in self.sesame_open_for:

            self.mcs.whitelist_del(mcuser)
            self.mcs.op_del(mcuser)
            self.mcs.kick(mcuser)

            self.mq.send_close(self.sesame_open_for[mcuser]["remote_addr"])

            logger.info("sesame closed for: %s (%s)" % (mcuser, self.sesame_open_for[mcuser]["remote_addr"]))

            del self.sesame_open_for[mcuser]

        else:
            logger.info("already logged out: %s" % mcuser)

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

            try:

                if not self.mcs.is_connected:
                    logger.info("Trying to connect to MC server")

                    if self.mcs.open():
                        logger.info("Connected")

                if self.mcs.is_connected:

                    if self.mcs_data["version"] is None:
                        self.mcs_data["version"] = self.mcs.get_version()

                    p = self.mcs.get_players()

                    if p is None:
                        logger.warn("Lost connection to MC server")
                        self.mcs.close()
                        continue

                    self.mcs_data["players"] = p

            except:

                self.mcs_data = {"version": None, "players": []}
                self.mcs.close()

            remove_users = []

            for mcuser, data in self.sesame_open_for.items():

                logger.info("checking: %s (%s)" % (mcuser, data["remote_addr"]))

                user_is_player = False

                for player in self.mcs_data["players"]:

                    if mcuser == player.name:
                        user_is_player = True
                        break

                if not user_is_player:

                    data["timeout"] -= 1
                    logger.info("user %s (%s) is not a player, timeout is now: %d" %
                                (mcuser, data["remote_addr"], data["timeout"]))

                    if data["timeout"] == 0:
                        logger.info("user %s (%s) has timed out" % (mcuser, data["remote_addr"]))
                        remove_users.append(mcuser)

                else:

                    logger.info("user with %s (%s) passed check!" % (mcuser, data["remote_addr"]))
                    data["timeout"] = self.player_timeout

            for mcuser in remove_users:
                self.mcs.whitelist_del(mcuser)
                self.mq.send_close(self.sesame_open_for[mcuser]["remote_addr"])
                del self.sesame_open_for[mcuser]

        self.mcs.close()

if __name__ == "__main__":

    c = GateKeeper()
    c.start()

    raw_input("press ENTER to stop")

    c.stop()
    c.join()
