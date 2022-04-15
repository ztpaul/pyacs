#!/usr/bin/env python3
# Author: Alexander Couzens <lynxis@fe80.eu>
# (C) 2021 by sysmocom - s.f.m.c. GmbH <info@sysmocom.de>

import configparser
import logging
import coloredlogs

from cwmp import Cwmp
from flask import Flask, request
from flask_kvsession import KVSessionExtension
from simplekv.fs import FilesystemStore

app = Flask("pyacs")
cwmp=Cwmp(app)
DESCRIPTION = 'pyacs is a tr069 acs written by python'


def main():
    coloredlogs.install(level='INFO')

    app.config.from_pyfile('./config/flask.py')
    STORE = FilesystemStore('./data')
    KVSessionExtension(STORE, app)
    app.run(host='0.0.0.0',port=80)


@app.route('/', methods=['GET', 'POST'])
def root():
    logging.info(request)
    return DESCRIPTION

@app.route('/acs', methods=['GET', 'POST'])
def acs():
    """ main tr069/acs entry point """
    if request.method == 'GET':
        return DESCRIPTION

    if request.method != 'POST':
        return 'There is nothing to show'

    # POST requests
    if request.content_type.find('text/xml')==-1:
        logging.error(f"request.content_type={request.content_type}")
        return 'Wrong content type'

    result = cwmp.handle_request(request)
    if result:
        return result
    else:
        return DESCRIPTION

if __name__ == '__main__':
    main()
