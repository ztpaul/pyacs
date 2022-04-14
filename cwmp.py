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
    log = logging.getLogger('Cwmp')
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

    def send_configuration(self, serial, push):
        """ write to the 'database' if this serial needs a configuration """
        self.cache.set(serial, push)

    def need_configuration(self, serial):
        """ does this device needs a new configuration? """
        need = self.cache.get(serial)
        if need is None:
            self.cache.set(serial, True)
            return True
        return need

    def generate_config(self, params=None, serial=None, config_file='./config/tr098.ini'):
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
                    Cwmp.log.error("Failed to parse %s key %s with value %s", section, key, config[section][key])

        read_config_to_params('Common')

        if serial and serial in config:
            read_config_to_params(serial)
        return params

    def handle_inform(self, tree, node):
        """ handle a device Inform request """
        cwmpid = self.soap.get_cwmp_id(tree)
        serial = self.soap.get_cwmp_inform_serial(node)
        events = self.soap.get_cwmp_inform_events(node)

        session['serial'] = serial
        if '0 BOOTSTRAP' in events or '1 BOOT' in events:
            self.send_configuration(serial, True)
            Cwmp.log.error("Device %s booted", serial)

        Cwmp.log.warn("Receive Inform form Device %s. cwmpipd=%s. Events=%s", serial, cwmpid, ", ".join(events))
        response = make_response(Cwmp.m_common_header+render_template('InformResponse.jinja.xml', cwmpid=cwmpid))
        response.headers['Content-Type'] = 'text/xml; charset="utf-8"'
        response.headers['SOAPServer'] = 'femto-acs/1.1.1'
        response.headers['Server'] = 'femto-acs/1.1.1'
        return response


    # description: handle a device GetRPCMethods request
    # input: tree
    #
    def handle_getrpcmethods(self, tree):
        cwmpid = self.soap.get_cwmp_id(tree)

        Cwmp.log.warn("Receive GetRPCMethods")
        response = make_response(Cwmp.m_common_header+render_template('GetRPCMethodsResponse.jinja.xml', cwmpid=cwmpid, method_list=Soap.m_methods, length=len(Soap.m_methods)))
        response.headers['Content-Type'] = 'text/xml; charset="utf-8"'
        response.headers['SOAPServer'] = 'femto-acs/1.1.1'
        response.headers['Server'] = 'femto-acs/1.1.1'
        return response

    def send_setparams(self):
        """ request a setparams """
        # e.g. params are {name: "arfcn", xmltype: "xsd:int", value: "23"}
        serial = session['serial']

        params = {}
        params = self.generate_config(params, serial)

        # keep track if we already sent out a response
        Cwmp.log.error("Device %s sending configuration", serial)
        self.send_configuration(serial, True)
        response = make_response(Cwmp.m_common_header+render_template('SetParameterValues.jinja.xml',
                                                cwmpid=23, params=params, length_params=len(params)))
        response.headers['Content-Type'] = 'text/xml'
        return response

    def setparams_response(self, tree, node):
        """ handle the setparams response """
        serial = session['serial']
        status = self.soap.get_cwmp_setresponse_status(node)
        if status is not None:
            if status == '0':
                Cwmp.log.error("Device %s applied configuration changes without reboot", serial)
            elif status == '1':
                Cwmp.log.error("Device %s applied configuration changes but require a reboot", serial)
            else:
                Cwmp.log.error("Device %s returned unknown status value (%s)", serial)
        self.send_configuration(serial, False)
        response = make_response()
        response.headers['Content-Type'] = 'text/xml'
        return response

    def handle_request(self, request):
        # when the client doesn't send us any data, it's ready for our request
        if not request.content_length:
            if 'serial' not in session:
                Cwmp.log.error("Received an empty request from an unknown device. Can not generate configuration!")
                return make_response()
            if self.need_configuration(session['serial']):
                return self.send_setparams()

            Cwmp.log.error("Device %s already configured", session['serial'])
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
                return self.handle_getrpcmethods(tree)
            case "Inform":
                return self.handle_inform(tree, node)
            case "SetParameterValuesResponse":
                return self.setparams_response(tree, node)



