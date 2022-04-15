#!/usr/bin/env python3
# Author: Alexander Couzens <lynxis@fe80.eu>
# (C) 2021 by sysmocom - s.f.m.c. GmbH <info@sysmocom.de>

import configparser
import logging
import coloredlogs

from cwmp import Cwmp
from flask import *
from flask_httpauth import *
from flask_kvsession import KVSessionExtension
from simplekv.fs import FilesystemStore

DESCRIPTION = 'pyacs is a tr069 acs written by python'
app = Flask("pyacs")
basic_auth = HTTPBasicAuth()
digest_auth = HTTPDigestAuth()
multi_auth = MultiAuth(basic_auth,  digest_auth)
cwmp=Cwmp(app)
config = configparser.ConfigParser()


def main():
    config.read("./config/pyacs.ini")

    coloredlogs.install(level='INFO')

    app.config.from_pyfile('./config/flask.py')
    STORE = FilesystemStore('./data')
    KVSessionExtension(STORE, app)
    app.run(host='0.0.0.0',port=80)


@app.route('/', methods=['GET', 'POST'])
def root():
    logging.info(request)
    return DESCRIPTION

@basic_auth.verify_password
def verify_password(username, password):
    #app.logger.error(f"username={username}, password={password}")
    if username==config['local']['username'] and password==config['local']['password']:
        return username
    else:
        g.current_user = username
        return False #username or password error

@basic_auth.error_handler
def auth_error(status_code):
    #app.logger.error(f"status_code={status_code}, username={g.current_user}")
    if status_code == 401:
        if g.current_user:
            return cwmp.generate_forbidden()
        else:
            return cwmp.generate_unauthorized(config['local']['authentication'])
    # return "Access Denied", status_code


@app.route('/acs', methods=['GET', 'POST'])
@multi_auth.login_required
def acs():
    """ main tr069/acs entry point """
    if request.method == 'GET':
        return DESCRIPTION

    if request.method != 'POST':
        return 'There is nothing to show'

    #app.logger.error(request.headers)


    # POST requests
    if request.content_type.find('text/xml')==-1:
        app.logger.error(f"request.content_type={request.content_type}")
        return 'Wrong content type'

    result = cwmp.handle_request(request)
    if result:
        return result
    else:
        return DESCRIPTION



if __name__ == '__main__':
    main()
