#!./venv/bin/python

import os
import sys
import hashlib

from mcsesame import version
from mcsesame import persistence
from distutils.core import setup


def pass2hash(password):
    d = hashlib.sha1(password)
    return d.hexdigest()


conf_dir = os.path.join(os.environ.get("HOME"), ".mcsesame")

if len(sys.argv) >= 1 and sys.argv[1] in ["build", "install"]:

    print("Preparing for setup")

    with open("mcsesame/confdir.py", "w") as f:
        f.write("CONF_DIR = '%s'" % conf_dir)

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

    if not os.path.exists("ssl.key") or not os.path.exists("ssl.crt"):

        from werkzeug.serving import make_ssl_devcert

        host = os.environ.get("HOSTNAME", "localhost")
        print("Creating ssl devcert for: %s" % host)

        ret = make_ssl_devcert('ssl', host=host)

        print("Created: %s, %s" % ret)

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
          "pyOpenSSL (>=16.2.0)"
        ],
      packages=['mcsesame', 'SwiftApi'],
      package_data={'mcsesame': ['templates/*', 'files/*']},
      scripts=['alibaba', 'sesame'],
      data_files=[(conf_dir, ['alibaba.ini', 'sesame.ini', 'users.db', 'ssl.crt', 'ssl.key'])]
      )
