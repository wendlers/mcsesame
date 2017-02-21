#!./venv/bin/python

import os
import sys
import hashlib
import subprocess

from mcsesame import version
from distutils.core import setup


if os.getuid() == 0:
    conf_dir = os.path.join(os.path.sep, "etc", "mcsesame")
else:
    conf_dir = os.path.join(os.environ.get("HOME"), ".mcsesame")


def pass2hash(password):
    d = hashlib.sha1(password)
    return d.hexdigest()


def createini():

    with open("alibaba.ini", "w") as f:

        if os.getuid() == 0:
            f.write("logfile = /var/log/alibaba.log")
        else:
            f.write("logfile = %s/alibaba.log" % conf_dir)

    with open("sesame.ini", "w") as f:

        if os.getuid() == 0:
            f.write("logfile = /var/log/sesame.log")
        else:
            f.write("logfile = %s/sesame.log" % conf_dir)

    print("Created ini files")


def createcert():

    if not os.path.exists("ssl.key") or not os.path.exists("ssl.crt"):

        host = os.environ.get("HOSTNAME", "localhost")

        retcode = subprocess.call(['openssl', 'req', '-x509', '-newkey', 'rsa:4096', '-keyout', 'ssl.key',  '-out',
                                   'ssl.crt', '-days', '365',  '-nodes',  '-subj',  ""'/CN=%s'"" % host])

        if retcode != 0:
            print("Failed to create ssl devcert for %s!" % host)
            exit(retcode)

        print("Created ssl devcert for: %s" % host)


def createconfdir():

    with open("mcsesame/confdir.py", "w") as f:
        f.write("CONF_DIR = '%s'" % conf_dir)

    print("Created mcsesame/confdir.py")


def createdb():

    from mcsesame import persistence

    if not os.path.exists("users.db"):

        import csv

        pm = persistence.PersistenceManager("sqlite:///users.db")

        pm.create_all()

        with open('users.csv', 'rb') as csvfile:
            users = csv.reader(csvfile, delimiter=',', quotechar='"')
            for row in users:
                print("adding: %s" % str(row))
                pm.add_user(persistence.User(
                    login=row[0],
                    passwd=pass2hash(row[1]),
                    mcuser=row[2],
                    admin=int(row[3])))

        print("Created users db")


if len(sys.argv) >= 1 and sys.argv[1] in ["build", "install"]:

    print("Preparing for setup")

    createconfdir()
    createini()
    createdb()
    createcert()


setup(name='mcsesame',
      version=version.FULL,
      description='MC Sesame.',
      author='Stefan Wendler',
      author_email='sw@kaltpost.de',
      url='https://www.kaltpost.de/',
      requires=[
          "ConfigArgParse (>=0.11.0)",
          "daemons (>=1.3.0)",
          "Flask (>=0.12)",
          "Flask_Login (>=0.4.0)",
          "posix_ipc (>=1.0.0)",
          "SQLAlchemy (>=1.1.5)",
          "thrift (>=0.10.0)",
        ],
      packages=['mcsesame', 'SwiftApi'],
      package_data={'mcsesame': ['templates/*', 'files/*']},
      scripts=['alibaba', 'sesame'],
      data_files=[(conf_dir, ['alibaba.ini', 'sesame.ini', 'users.db', 'ssl.crt', 'ssl.key'])]
      )
