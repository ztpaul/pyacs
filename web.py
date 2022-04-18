#!/usr/bin/env python3
# Author: ballzb


import logging
from flask import render_template

class Web:
    log = logging.getLogger('web')
        


    def handle_GET(self):
        return render_template('web/index.html')

    def handle_POST(self, form):
        self.log.info(f"method={form['method']}, path={form['path']}")
        return render_template('web/index.html')