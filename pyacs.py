#!/usr/bin/env python3
# Author: Alexander Couzens <lynxis@fe80.eu>
# (C) 2021 by sysmocom - s.f.m.c. GmbH <info@sysmocom.de>

import configparser

#from requests import request
import coloredlogs
from waitress import serve
from flask import *
from flask_httpauth import *
from flask_kvsession import KVSessionExtension
from flask_caching import Cache
from simplekv.fs import FilesystemStore
from cwmp import Cwmp
from web import Web

DESCRIPTION = 'pyacs is a tr069 acs written by python'
APP_NAME = 'pyacs'
app = Flask(APP_NAME, static_folder='templates/web/')
basic_auth = HTTPBasicAuth(realm=APP_NAME)
digest_auth = HTTPDigestAuth(realm=APP_NAME, qop='auth')
multi_auth = MultiAuth(basic_auth,  digest_auth) # assume basic auth is the main auth
cwmp=Cwmp()
web=Web(cwmp)
config = configparser.ConfigParser()


def main():
    coloredlogs.install(level='INFO', fmt="%(asctime)s [%(name)s] [%(levelname)s] [%(funcName)s(%(lineno)d)] %(message)s")

    cache = Cache()
    cache.init_app(app=app, config={"CACHE_TYPE": 'FileSystemCache', "CACHE_DIR": "./cache"})
    cache.clear()
    cwmp.set_cache(cache)

    config.read("./config/pyacs.ini")

    app.config.from_pyfile('./config/flask.py')
    STORE = FilesystemStore('./data')
    KVSessionExtension(STORE, app)
    #app.run(host='0.0.0.0',port=80) #keep this if we need set 'Connection' of HTTP header
    serve(app, host='0.0.0.0', port=80)


#
@app.route('/', methods=['GET', 'POST'])
def root():
    app.logger.info(request)
    if request.method == 'GET':
        return web.handle_GET()
    elif request.method == 'POST':
        return web.handle_POST(request.form)
        
            


@app.route('/acs', methods=['GET', 'POST'])
@multi_auth.login_required
def acs():
    """ main tr069/acs entry point """
    app.logger.debug(f"method={request.method},headers={request.headers}")

    if request.method == 'GET':
        return DESCRIPTION

    if request.method != 'POST':
        return 'There is nothing to show'

    app.logger.debug(f"request.headers={request.headers}")


    # POST requests
    if request.content_type.find('text/xml')==-1:
        app.logger.error(f"request.content_type={request.content_type}")
        return 'Wrong content type'

    result = cwmp.handle_POST(request)
    if result:
        return result
    else:
        return DESCRIPTION


@basic_auth.verify_password
def basic_verify_password(username, password):
    g.username = username # use g.username to indicate no 'Www-Authenticate' header or wrong 'Www-Authenticate' header

    app.logger.debug(f"username={username}, password={password}")
    if username==config['local']['username'] and password==config['local']['password']:
        return username
    else:
        return False #username or password error


@basic_auth.error_handler
def basic_auth_error(status_code):
    app.logger.warning(f"status_code={status_code}, g.username={g.username}")
    if status_code == 401:
        if g.username:
            return cwmp.make_403_response()
        else:
            if(config['local']['authentication'] == 'Basic'):
                return cwmp.make_401_response(basic_auth.authenticate_header())
            else:
                return cwmp.make_401_response(digest_auth.authenticate_header())


@digest_auth.get_password
def digest_get_password(username):
    app.logger.debug(f"username={username}")
    if username == config['local']['username']:
        return config['local']['password']
    
    app.logger.warning(f"get password failed, username={username}")
    return None


@digest_auth.error_handler
def digest_auth_error(status_code):
    app.logger.warning(f"status_code={status_code}")

    if status_code == 401:
        return cwmp.make_403_response()


if __name__ == '__main__':
    main()
