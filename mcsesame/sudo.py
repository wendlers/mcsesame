import os
import sys
import pwd
import grp


def running_as_root():

    return os.geteuid() == 0


def run_as_root():

    if not running_as_root():

        args = ['sudo', sys.executable] + sys.argv + [os.environ]

        try:
            os.execlpe('sudo', *args)

        except Exception as e:

            print(e)
            sys.exit(1)


def drop_privileges():

    if os.getuid() != 0:
        return

    user_name = os.getenv("SUDO_USER")
    pwnam = pwd.getpwnam(user_name)

    os.setgroups([])

    os.setgid(pwnam.pw_gid)
    os.setuid(pwnam.pw_uid)

    os.umask(0o22)
