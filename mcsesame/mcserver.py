import hashlib
import logging

from SwiftApi import SwiftApi
from thrift.transport import TSocket, TTransport
from thrift.protocol import TBinaryProtocol

logger = logging.getLogger(__name__)


class McServer:

    def __init__(self, host="localhost", port=21111, username="admin", password="password", salt="saltines"):

        self.is_connected = False

        self.host = host
        self.port = port
        self.socket = None
        self.transport = None
        self.protocol = None
        self.client = None

        self.username = username
        self.password = password
        self.salt = salt

    def __authstr(self, func):

        key = self.username + func + self.password + self.salt
        sha256 = hashlib.sha256(key)

        return sha256.hexdigest()

    def open(self):

        try:

            self.socket = TSocket.TSocket(self.host, self.port)
            self.transport = TTransport.TFramedTransport(self.socket)
            self.protocol = TBinaryProtocol.TBinaryProtocol(self.transport)
            self.client = SwiftApi.Client(self.protocol)
            self.transport.open()

            self.is_connected = True

        except TTransport.TTransportException:

            self.is_connected = False

            logger.warn("Failed to connect to MC server")

        return self.is_connected

    def close(self):

        if self.is_connected:
            self.transport.close()
            self.is_connected = False

    def get_version(self):

        try:

            ver = self.client.getBukkitVersion(self.__authstr("getBukkitVersion"))

        except:
            ver = None
            logger.warn("get version failed")

        return ver

    def get_players(self):

        online_players = []

        try:

            pl = self.client.getOfflinePlayers(self.__authstr("getOfflinePlayers"))

            for p in pl:
                if p.player is not None:
                    online_players.append(p.player)

        except:
            online_players = None
            logger.warn("get players failed")

        return online_players

    def whitelist_add(self, player):

        try:
            self.client.addToWhitelist(self.__authstr("addToWhitelist"), player)
        except:
            logger.warn("adding %s to whitelist failed" % player)

    def whitelist_del(self, player):

        try:
            self.client.removeFromWhitelist(self.__authstr("removeFromWhitelist"), player)
        except:
            logger.warn("removing %s from whitelist failed" % player)

    def op_add(self, player):

        try:
            self.client.op(self.__authstr("op"), player, True)
        except:
            logger.warn("op %s failed" % player)

    def op_del(self, player):

        try:
            self.client.deOp(self.__authstr("deOp"), player, False)
        except:
            logger.warn("deOp %s failed" % player)

    def kick(self, player):

        try:
            self.client.kick(self.__authstr("kick"), player, "You logged out from web-interface")
        except:
            logger.warn("kicking %s failed" % player)


if __name__ == "__main__":

    mcs = McServer()

    server_up = mcs.open()

    if server_up:

        ver = mcs.get_version()

        print("Server is up, running version %s" % ver)

        players = mcs.get_players()

        print("Players online:")

        for p in players:
            print(" - %s" % p.name)

        mcs.close()

    else:

        print("Server is down")
