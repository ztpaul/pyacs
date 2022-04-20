#!/usr/bin/env python3
# Author: ballzb


import logging
from flask import render_template

class Web:       
    def __init__(self, cwmp):
        self.cwmp =cwmp

    def handle_GET(self):
        return render_template('web/index.html')

    def handle_POST(self, form):
        logging.info(f"method={form['method']}, path={form['path']}")
        self.cwmp.send_GET()
        return render_template('web/index.html')