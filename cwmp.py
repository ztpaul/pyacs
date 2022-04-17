#!/usr/bin/env python3
# Author: Alexander Couzens <lynxis@fe80.eu>
# (C) 2021 by sysmocom - s.f.m.c. GmbH <info@sysmocom.de>

import configparser
import logging
from xml.etree.ElementTree import fromstring

from flask import make_response, render_template, session
from flask_caching import Cache
from soap import *

class Cwmp:
    m_common_header = \
'<?xml version="1.0" encoding="UTF-8"?>\n\
<soap-env:Envelope\n\
    xmlns:soap-enc="http://schemas.xmlsoap.org/soap/encoding/"\n\
    xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/"\n\
    xmlns:xsd="http://www.w3.org/2001/XMLSchema"\n\
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n\
    xmlns:cwmp="urn:dslforum-org:cwmp-1-2">\n'

    def __init__(self, app):
        self.soap = Soap()
        cache = Cache()
        cache.init_app(app=app, config={"CACHE_TYPE": 'FileSystemCache', "CACHE_DIR": "./cache"})
        cache.clear()
        self.cache = cache

    def send_configuration(self, sn, push):
        """ write to the 'database' if this sn needs a configuration """
        self.cache.set(sn, push)

    def need_configuration(self, sn):
        """ does this device needs a new configuration? """
        need = self.cache.get(sn)
        if need is None:
            self.cache.set(sn, True)
            return True
        return need

    def generate_config(self, params=None, sn=None, config_file='./config/tr098.ini'):
        """ return a params dict for setparams from the config file """
        if params is None:
            params = {}

        config = configparser.ConfigParser()
        config.optionxform=str
        config.read(config_file)

        def read_config_to_params(section):
            for key in config[section]:
                try:
                    val, xmltype = config[section][key].split('|')
                    params[key] = {'value': val, 'xmltype': xmltype}
                except:
                    logging.error("Failed to parse %s key %s with value %s", section, key, config[section][key])

        read_config_to_params('Common')

        if sn and sn in config:
            read_config_to_params(sn)
        return params

    def make_401_response(self, authentication):
        response = make_response()
        response.status_code = 401
        response.headers['Content-Type'] = 'text/xml; charset="utf-8"'
        response.set_cookie('pyacs', 'pyacs_cookie')
        if authentication == 'Basic':
            response.headers['WWW-Authenticate'] = 'Basic realm="pyacs"'
        return response


    def make_403_response(self):
        response = make_response()
        response.status_code = 403
        response.headers['Content-Type'] = 'text/xml; charset="utf-8"'
        return response

    def handle_Inform(self, tree, node):
        """ handle a device Inform request """
        cwmpid = self.soap.get_cwmp_id(tree)
        sn = self.soap.get_cwmp_inform_sn(node)
        events = self.soap.get_cwmp_inform_events(node)

        session['sn'] = sn
        if '0 BOOTSTRAP' in events or '1 BOOT' in events:
            self.send_configuration(sn, True)
            logging.error("Device %s booted", sn)

        logging.info("Receive Inform form Device %s. cwmpipd=%s. Events=%s", sn, cwmpid, ", ".join(events))
        response = make_response(Cwmp.m_common_header+render_template('InformResponse.jinja.xml', cwmpid=cwmpid))
        response.headers['Content-Type'] = 'text/xml; charset="utf-8"'
        return response


    # description: handle a device GetRPCMethods request
    # input: tree
    #
    def handle_GetRPCMethods(self, tree):
        cwmpid = self.soap.get_cwmp_id(tree)

        logging.info("Receive GetRPCMethods")
        response = make_response(Cwmp.m_common_header+render_template('GetRPCMethodsResponse.jinja.xml', cwmpid=cwmpid, method_list=Soap.m_methods, length=len(Soap.m_methods)))
        response.headers['Content-Type'] = 'text/xml; charset="utf-8"'
        return response

    def make_SetParameterValues_response(self):
        """ request a setparams """
        # e.g. params are {name: "arfcn", xmltype: "xsd:int", value: "23"}
        sn = session['sn']

        params = {}
        params = self.generate_config(params, sn)

        # keep track if we already sent out a response
        logging.info("Device %s sending configuration", sn)
        self.send_configuration(sn, True)
        response = make_response(Cwmp.m_common_header+render_template('SetParameterValues.jinja.xml',
                                                cwmpid=23, params=params, length_params=len(params)))
        response.headers['Content-Type'] = 'text/xml; charset="utf-8"'
        return response

    def handle_SetParameterValuesResponse(self, tree, node):
        """ handle the setparams response """
        sn = session['sn']
        status = self.soap.get_cwmp_setresponse_status(node)
        if status is not None:
            if status == '0':
                logging.info("Device %s applied configuration changes without reboot", sn)
            elif status == '1':
                logging.info("Device %s applied configuration changes but require a reboot", sn)
            else:
                logging.error("Device %s returned unknown status value (%s)", sn)
        self.send_configuration(sn, False)
        response = make_response()
        response.headers['Content-Type'] = 'text/xml; charset="utf-8"'
        return response

    def handle_request(self, request):
        # when the client doesn't send us any data, it's ready for our request
        if not request.content_length:
            if 'sn' not in session:
                logging.error("Received an empty request from an unknown device. Can not generate configuration!")
                return make_response()
            if self.need_configuration(session['sn']):
                return self.make_SetParameterValues_response()

            logging.info("Device %s already configured", session['sn'])
            return make_response()

        # some request content data
        try:
            tree = fromstring(request.data)
        except:
            return 'Could not parse the request as XML'

        method = self.soap.get_cwmp_method(tree) #here method is a tuple of "method string" and related "xml.etree.ElementTree.Element"
        if not method:
            return 'Failed to get the cwmp method'

        method, node = method

        match method:
            case "GetRPCMethods":
                return self.handle_GetRPCMethods(tree)
            case "Inform":
                return self.handle_Inform(tree, node)
            case "SetParameterValuesResponse":
                return self.handle_SetParameterValuesResponse(tree, node)



