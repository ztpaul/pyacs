#!/usr/bin/env python3
# Author: Alexander Couzens <lynxis@fe80.eu>
# (C) 2021 by sysmocom - s.f.m.c. GmbH <info@sysmocom.de>

import configparser
import logging
from cwmp import Cwmp

from flask import Flask, request
from flask_kvsession import KVSessionExtension
from simplekv.fs import FilesystemStore


LOG = logging.getLogger("pyacs")
STORE = FilesystemStore('./data')
app = Flask("pyacs")
cwmp=Cwmp(app)

KVSessionExtension(STORE, app)
app.config.from_pyfile('./config/flask.py')


@app.route('/', methods=['GET', 'POST'])
def root():
    return 'This is a tr069 acs'

@app.route('/acs', methods=['GET', 'POST'])
def acs():
    """ main tr069/acs entry point """
    if request.method == 'GET':
        return 'This is a tr069 acs'

    if request.method != 'POST':
        return 'There is nothing to show'

    # POST requests
    if request.content_type.find('text/xml')==-1:
        LOG.error(f"request.content_type={request.content_type}")
        return 'Wrong content type'

    result = cwmp.handle_request(request)
    if not result:
        return result

    return 'This is a tr069 acs written by python'

if __name__ == '__main__':
    app.run()
