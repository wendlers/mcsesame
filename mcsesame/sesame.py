import os
import logging
import ipc
import configargparse
import config
import version
import sudo

from subprocess import call
from daemons import daemonizer


logger = logging.getLogger(__name__)


class Sesame:

    def __init__(self):

        self.mq = ipc.MessageQueue(create=False)

    def iptables_setup(self):
        """
        iptables -N mc-sesame
        iptables -t filter -A INPUT -j mc-sesame
        iptables -A mc-sesame -p tcp --dport 25565 -j DROP
        """

        logger.info("setting up iptables filter chain")

        retcode = call(["/sbin/iptables", "-N", "mc-sesame"]) + \
                  call(["/sbin/iptables", "-t", "filter", "-I", "INPUT", "1", "-j", "mc-sesame"]) +\
                  call(["/sbin/iptables", "-A", "mc-sesame", "-p", "tcp", "--dport", "25565", "-j", "DROP"])

        if retcode:
            logger.warn("failed to setup iptables filter chain")

        return retcode == 0

    def iptables_destroy(self):
        """
        iptables -F mc-sesame
        iptables -D INPUT -j mc-sesame
        iptables -X mc-sesame
        """

        logger.info("removing iptables filter chain")

        retcode = call(["/sbin/iptables", "-F", "mc-sesame"]) +\
                  call(["/sbin/iptables", "-D", "INPUT", "-j", "mc-sesame"]) +\
                  call(["/sbin/iptables", "-X", "mc-sesame"])

        if retcode:
            logger.warn("failed to remove iptables filter chain")

        return retcode == 0

    def iptables_grant(self, ip):
        """
        iptables -I mc-sesame 1 -p tcp --dport 25565 -s 192.168.2.226 -j ACCEPT
        """

        logger.info("adding %s to filter chain" % ip)

        retcode = call(["/sbin/iptables", "-I", "mc-sesame", "1", "-p", "tcp", "--dport", "25565", "-s", ip, "-j",
                        "ACCEPT"])

        if retcode:
            logger.warn("failed to add %s to filter chain" % ip)

        return retcode == 0

    def iptables_revoke(self, ip):
        """
        iptables -D mc-sesame -p tcp --dport 25565 -s 192.168.2.226 -j ACCEPT
        """

        logger.info("removing %s from filter chain" % ip)

        retcode = call(["/sbin/iptables", "-D", "mc-sesame", "-p", "tcp", "--dport", "25565", "-s", ip, "-j",
                        "ACCEPT"])

        if retcode:
            logger.warn("failed to remove %s from filter chain" % ip)

        return retcode == 0

    def handle_open(self, ip):

        logger.info("sesame open for: %s" % ip)
        self.iptables_grant(ip)

    def handle_close(self, ip):
        logger.info("sesame close for: %s" % ip)
        self.iptables_revoke(ip)

    def run(self):

        while True:

            self.mq.process_incoming(self.handle_open, self.handle_close)


def foreground():

    logging.info('MCSesame - Sesame v%s started' % version.FULL)

    sesa = Sesame()
    sesa.iptables_setup()

    try:
        sesa.run()
    except Exception as e:
        logger.error(e.message)
    except KeyboardInterrupt:
        pass

    sesa.iptables_destroy()


@daemonizer.run(pidfile=config.PID_SESAME)
def daemon():

    foreground()


def main():

    sudo.run_as_root()

    '''
    if not sudo.running_as_root():
        print("Must be run with root privileges!")
        exit(1)
    '''

    parser = configargparse.ArgParser(default_config_files=[os.path.join(config.CONF_DIR, 'sesame.ini')])

    parser.add_argument("-f", help="run in foreground (don't become a daemon)",
                        action="store_true", default=False)

    parser.add_argument("-c", help="send control message to daemon",
                        choices=['stop', 'restart'], default=None)

    parser.add_argument('--config', is_config_file=True, help='path to config file')

    parser.add_argument("--logfile", help="write log to file",
                        default=os.path.join(config.CONF_DIR, 'sesame.log'))
    parser.add_argument("--loglevel", help="loglevel (CRITICAL, ERROR, WARNING, INFO, DEBUG)", default="INFO")

    args = parser.parse_args()

    # daemon ctrl
    if args.c is not None:

        if args.c == "stop":
            daemon.stop()
        elif args.c == "restart":
            daemon.restart()

        exit(0)

    # daemon needs logfile
    if not args.f and args.logfile is None:
        print("Logfile must be specified when run in background!")
        exit(1)

    if not args.f and args.logfile is not None:
        logging.basicConfig(format=config.LOG_FORMAT, filename=os.path.expanduser(args.logfile),level=args.loglevel)
    else:
        logging.basicConfig(format=config.LOG_FORMAT, level=args.loglevel)

    # daemon or foreground?
    if args.f:
        foreground()
    else:
        daemon()


if __name__ == "__main__":

    main()
