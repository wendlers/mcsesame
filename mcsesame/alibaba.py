import os
import logging
import flask_login
import flask
import configargparse
import hashlib

import sudo
import config
import version
import persistence
import gatekeeper

from flask import Flask, render_template, send_from_directory
from daemons import daemonizer

logger = logging.getLogger(__name__)


def pass2hash(password):
    d = hashlib.sha1(password)
    return d.hexdigest().decode('utf-8')


class App:

    class LoginUser(flask_login.UserMixin):
        pass

    def __init__(self, httpport, nossl, ssl_cert, ssl_key, database, user_name, player_timeout):

        self.database = database
        self.user_name = user_name
        self.httpport = httpport
        self.nossl = nossl
        self.ssl_cert = ssl_cert
        self.ssl_key = ssl_key

        try:

            flist = [self.ssl_cert, self.ssl_key]

            if self.database.startswith("sqlite:///"):

                dbpath = self.database[len("sqlite:///"):]
                dbdir = os.path.dirname(dbpath)

                flist.append(dbpath)
                flist.append(dbdir)

            sudo.drop_privileges(self.user_name, flist)

            logging.info("Dropped privileges to user '%s'" % self.user_name)

        except KeyError:

            logger.warn("User '%s' not found - not dropping privileges!" % self.user_name)

        self.pm = persistence.PersistenceManager(self.database)
        self.gk = gatekeeper.GateKeeper(player_timeout)

        self.app = Flask(__name__)
        self.app.secret_key = '98s7ad=)$Djguiu87g'

        self.app.add_url_rule("/login", view_func=self.login, methods=['GET', 'POST'])
        self.app.add_url_rule("/logout", view_func=self.logout)
        self.app.add_url_rule("/admin", view_func=self.admin, methods=['GET', 'POST'])
        self.app.add_url_rule("/passwd", view_func=self.passwd, methods=['GET', 'POST'])
        self.app.add_url_rule("/renew", view_func=self.renew)
        self.app.add_url_rule("/", view_func=self.root)

        self.app.add_url_rule("/files/<path:path>", view_func=self.files)

        self.login_manager = flask_login.LoginManager()
        self.login_manager.init_app(self.app)

        self.login_manager.user_loader(self.user_loader)
        self.login_manager.request_loader(self.request_loader)
        self.login_manager.unauthorized_handler(self.unauthorized_handler)

    def user_loader(self, login):

        user = self.pm.get_user(login)

        if user is None:
            return

        login_user = App.LoginUser()
        login_user.id = login
        login_user.admin = user.admin

        return login_user

    def request_loader(self, request):

        login = request.form.get('login')

        if login is None:
            return

        user = self.pm.get_user(login)

        if user is None or pass2hash(request.form['pw']) != user.passwd:
            return

        login_user = App.LoginUser()
        login_user.id = login
        login_user.admin = user.admin

        return login_user

    def unauthorized_handler(self):

        return flask.redirect('/login')

    def run(self):

        self.gk.start()

        if self.nossl:
            context = None
        else:
            context = (self.ssl_cert, self.ssl_key)

        self.app.run(host='0.0.0.0', port=self.httpport, ssl_context=context, threaded=True, debug=False)

        self.gk.stop()

    def login(self):

        if flask.request.method == 'GET':
            return render_template('login.html')

        login = flask.request.form['login']

        user = self.pm.get_user(login)

        if user is not None and pass2hash(flask.request.form['pw']) == user.passwd:

            login_user = App.LoginUser()
            login_user.id = login
            login_user.admin = user.admin

            flask_login.login_user(login_user)

            return flask.redirect('/')

        return render_template('message.html', message='Anmeldung fehlgeschlagen')

    def logout(self):

        # we don't know if someone else from same IP is connected
        # thus, the ip is not closed
        # timeout will take care of that later
        '''
        try:
            self.gk.close_sesame_for(flask.request.remote_addr)
        except AttributeError:
            pass
        '''

        flask_login.logout_user()

        return render_template('message.html', message='Du wurdest abgemeldet!')

    @flask_login.login_required
    def root(self):

        self.gk.open_sesame_for(flask.request.remote_addr)

        return render_template('root.html',
                               remote_addr=flask.request.remote_addr,
                               login=flask_login.current_user.id,
                               is_auth=True,
                               is_admin=flask_login.current_user.admin)

    @flask_login.login_required
    def renew(self):

        self.gk.open_sesame_for(flask.request.remote_addr)

        return "OK"

    @flask_login.login_required
    def passwd(self):

        error = None
        success = False

        if flask.request.method == 'POST':

            login = flask.request.form["login"]
            password = flask.request.form["password"]

            user = self.pm.get_user(login)

            if len(password) == 0:

                error = "Passwort darf nicht leer sein!"

            else:

                user.passwd = pass2hash(password)
                self.pm.commit()
                success = True

        return render_template('passwd.html',
                               message=True,
                               login=flask_login.current_user.id,
                               is_auth=True,
                               is_admin=flask_login.current_user.admin,
                               success=success,
                               error=error)

    @flask_login.login_required
    def admin(self):

        error = None

        if not flask_login.current_user.admin:
            return render_template('message.html', message='Du hast keine Adminrechte!')

        edit_user = None
        new_user = None
        new_ip = None

        if flask.request.method == 'GET':

            target = flask.request.args.get("t")
            action = flask.request.args.get("a")

            if target == "us":

                login = flask.request.args.get("l")

                if action == "ed":

                    edit_user = self.pm.get_user(login)

                elif action == "dl":

                    self.pm.del_user(self.pm.get_user(login))

                elif action == "nw":

                    new_user = persistence.User()
                    new_user.login = ""
                    new_user.passwd = ""
                    new_user.admin = 0

            elif target == "ip":

                if action == "dl":

                    ip = flask.request.args.get("i")

                    try:
                        self.gk.close_sesame_for(ip)
                    except AttributeError:
                        pass

                elif action == "nw":
                    new_ip = {
                    "ip": flask.request.remote_addr,
                    "timeout": self.gk.player_timeout * 10}

        else:

            target = flask.request.form["target"]

            if target == "us":

                login = flask.request.form["login"]
                password = flask.request.form["password"]

                if "admin" in flask.request.form:
                    admin = 1
                else:
                    admin = 0

                user = self.pm.get_user(login)

                if user is None:

                    user = persistence.User()
                    user.login = login
                    user.passwd = pass2hash(password)

                    if len(login) == 0:
                        error = "Login muss angegeben werden!"
                    elif len(password) == 0:
                        error = "Passwort muss angegeben werden!"
                    else:
                        self.pm.add_user(user)

                    if error:
                        new_user = user

                else:

                    if len(password):
                        user.passwd = pass2hash(password)

                user.admin = admin

                if not error:
                    self.pm.commit()

            elif target == "ip":

                ip = flask.request.form["ip"]
                timeout = flask.request.form["timeout"]

                if len(ip) == 0:
                    error = "IP muss angegeben werden!"
                elif len(timeout) == 0:
                    error = "Timeout muss angegeben werden!"
                else:
                    try:
                        timeout = int(timeout)
                    except:
                        error = "Timout muss eine Zahl sein!"

                if error:
                    new_ip = {
                        "ip": ip,
                        "timeout": timeout}
                else:
                    self.gk.open_sesame_for(ip, timeout // 10)

        users = self.pm.get_all_users()

        return render_template('admin.html',
                               message=True,
                               is_auth=True,
                               is_admin=flask_login.current_user.admin,
                               users=users,
                               addrs=self.gk.sesame_open_for,
                               edit_user=edit_user,
                               new_user=new_user,
                               new_ip=new_ip,
                               error=error)

    def files(self, path):
        return send_from_directory('files', path)


def foreground(httpport, nossl, ssl_cert, ssl_key, database, user, player_timeout):

    logger.info('MCSesame - Alibaba v%s started' % version.FULL)

    try:

        ali = App(httpport, nossl, ssl_cert, ssl_key, database, user, player_timeout)
        ali.run()

    except OSError as e:
        logger.warning(e)
        exit(1)
    except Exception as e:
        logger.critical(e)
        exit(1)

@daemonizer.run(pidfile=config.PID_ALIBABA)
def daemon(httpport, nosssl, ssl_cert, ssl_key, database, user, player_timeout):

    foreground(httpport, nosssl, ssl_cert, ssl_key, database, user, player_timeout)


def main():

    # sudo.run_as_root()

    parser = configargparse.ArgParser(default_config_files=[
        os.path.join(config.CONF_DIR, 'alibaba.ini')])

    parser.add_argument("-f", help="run in foreground (don't become a daemon)",
                        action="store_true", default=False)

    parser.add_argument("-c", help="send control message to daemon",
                        choices=['stop', 'restart'], default=None)

    parser.add_argument("--logfile", help="write log to file (if not in foreground)",
                        default=os.path.join(config.CONF_DIR, 'alibaba.log'))
    parser.add_argument("--loglevel", help="loglevel (CRITICAL, ERROR, WARNING, INFO, DEBUG)", default="INFO")

    parser.add_argument('--config', is_config_file=True, help='path to config file')

    parser.add_argument("--sslcert", help="SSL cert file", default=os.path.join(config.CONF_DIR, 'ssl.crt'))
    parser.add_argument("--sslkey", help="SSL key file", default=os.path.join(config.CONF_DIR, 'ssl.key'))

    parser.add_argument("--database", help="User database",
                        default="sqlite:///" + os.path.join(config.CONF_DIR, 'users.db'))

    parser.add_argument("--httpport", help="HTTP port", type=int, default=8088)

    parser.add_argument("--nossl", help="don't use SSL",
                        action="store_true", default=False)

    parser.add_argument("--user", help="User under which to run this app", default="mcserver")

    parser.add_argument("--playertimeout", help="Player inactivity timeout (will be multiplied by 10sec)",
                        type=int, default=60)

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
        logging.basicConfig(format=config.LOG_FORMAT, filename=os.path.join(config.CONF_DIR, args.logfile),
                            level=args.loglevel)
    else:
        logging.basicConfig(format=config.LOG_FORMAT, level=args.loglevel)

    # daemon or foreground?
    if args.f:
        foreground(args.httpport,
                   args.nossl,
                   args.sslcert,
                   args.sslkey,
                   args.database,
                   args.user,
                   args.playertimeout)
    else:
        daemon(args.httpport,
               args.nossl,
               args.sslcert,
               args.sslkey,
               args.database,
               args.user,
               args.playertimeout)


if __name__ == "__main__":

    main()
