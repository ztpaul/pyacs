#!/usr/bin/env python3
# Author: Alexander Couzens <lynxis@fe80.eu>
# (C) 2021 by sysmocom - s.f.m.c. GmbH <info@sysmocom.de>

import configparser
import logging
from xml.etree.ElementTree import fromstring
import requests
from requests.auth import HTTPDigestAuth, HTTPBasicAuth

from flask import make_response, render_template, session
from soap import *

class Cwmp:
    mSoap = Soap()
    mPyacsConfig = configparser.ConfigParser()
    mPyacsConfig.read("./config/pyacs.ini")
    m_common_header = \
'<?xml version="1.0" encoding="UTF-8"?>\n\
<soap-env:Envelope\n\
    xmlns:soap-enc="http://schemas.xmlsoap.org/soap/encoding/"\n\
    xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/"\n\
    xmlns:xsd="http://www.w3.org/2001/XMLSchema"\n\
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n\
    xmlns:cwmp="urn:dslforum-org:cwmp-1-2">\n'

    def __init__(self):
        self.mConnectionRequestURL = ''
        self.pending_method = 'SetParameterValues' # run SetParameterValues to set default values for each CPE
        self.pending_arg = 'common' #arguments related to pending_method, can be a TR098/TR181 path or config section
    
    def set_cache(self, cache):
        self.mCache = cache

    def send_configuration(self, sn, push):
        """ write to the 'database' if this sn needs a configuration """
        self.mCache.set(sn, push)

    def need_configuration(self, sn):
        """ does this device needs a new configuration? """
        need = self.mCache.get(sn)
        if need is None:
            self.mCache.set(sn, True)
            return True
        return need



    def generate_config(self):
        """ return a params dict for setparams from the config file """
        params = {}

        config = configparser.ConfigParser()
        config.optionxform=str
        if Cwmp.mPyacsConfig['local']['DataModel'] == 'tr098':
            config_file = './config/tr098.ini'
        else:
            config_file = './config/tr181.ini'
        config.read(config_file)

        def read_config_to_params(section):
            for key in config[section]:
                try:
                    val, xmltype = config[section][key].split('|')
                    params[key] = {'value': val, 'xmltype': xmltype}
                except:
                    logging.error("Failed to parse %s key %s with value %s", section, key, config[section][key])

        read_config_to_params(self.pending_arg)

        return params



    def make_401_response(self, header):
        response = make_response()
        response.status_code = 401
        response.headers['Content-Type'] = 'text/xml; charset="utf-8"'
        response.headers['WWW-Authenticate'] = header
        return response


    def make_403_response(self):
        response = make_response()
        response.status_code = 403
        response.headers['Content-Type'] = 'text/xml; charset="utf-8"'
        return response

    def handle_Inform(self, tree, node):
        """ handle a device Inform request """
        cwmpid = Cwmp.mSoap.get_cwmp_id(tree)
        sn = Cwmp.mSoap.get_cwmp_inform_sn(node)
        events = Cwmp.mSoap.get_cwmp_inform_events(node)

        self.mConnectionRequestURL = Cwmp.mSoap.get_cwmp_inform_value(node, 'ManagementServer.ConnectionRequestURL')

        session['sn'] = sn
        if '0 BOOTSTRAP' in events or '1 BOOT' in events:
            self.send_configuration(sn, True)
            logging.error("Device %s booted", sn)

        logging.info("Receive Inform form Device %s. cwmpipd=%s. Events=%s", sn, cwmpid, ", ".join(events))
        response = make_response(Cwmp.m_common_header+render_template('cwmp/InformResponse.jinja.xml', cwmpid=cwmpid))
        response.headers['Content-Type'] = 'text/xml; charset="utf-8"'
        return response


    #########################################################################################################
    # description: handle a device GetRPCMethods request
    #
    # input:  tree - whole request data
    #
    # output: none
    #
    # return: response to CPE
    #########################################################################################################
    def handle_GetRPCMethods(self, tree):
        cwmpid = Cwmp.mSoap.get_cwmp_id(tree)

        logging.info("Receive GetRPCMethods")
        response = make_response(Cwmp.m_common_header+render_template('cwmp/GetRPCMethodsResponse.jinja.xml', cwmpid=cwmpid, method_list=Soap.m_methods, length=len(Soap.m_methods)))
        response.headers['Content-Type'] = 'text/xml; charset="utf-8"'
        return response

    def make_SetParameterValues_response(self):
        """ request a setparams """
        # e.g. params are {name: "arfcn", xmltype: "xsd:int", value: "23"}
        sn = session['sn']

        params = {}
        params = self.generate_config()

        # keep track if we already sent out a response
        logging.info("Device %s sending configuration", sn)
        self.send_configuration(sn, True)
        response = make_response(Cwmp.m_common_header+render_template('cwmp/SetParameterValues.jinja.xml',
                                                cwmpid=23, params=params, length_params=len(params)))
        response.headers['Content-Type'] = 'text/xml; charset="utf-8"'
        return response

    def handle_SetParameterValuesResponse(self, tree, node):
        """ handle the setparams response """
        sn = session['sn']
        status = Cwmp.mSoap.get_cwmp_setresponse_status(node)
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

    def handle_POST(self, request):
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

        method = Cwmp.mSoap.get_cwmp_method(tree) #here method is a tuple of "method string" and related "xml.etree.ElementTree.Element"
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

    def send_GET(self):
        response = requests.get(self.mConnectionRequestURL)
        logging.info(f"code={response.status_code}, headers={response.headers}")
        if response.status_code == 401:
            username = Cwmp.mPyacsConfig['cpe']['username']
            password = Cwmp.mPyacsConfig['cpe']['password']
            if 'Digest' in response.headers['WWW-Authenticate']:
                response = requests.get(self.mConnectionRequestURL,auth=HTTPDigestAuth(username,password))
            elif 'Basic' in response.headers['WWW-Authenticate']:
                response = requests.get(self.mConnectionRequestURL,auth=HTTPBasicAuth(username,password))
            else:
                logging.error("unknown auth header, headers={response.headers}")

            logging.info(f"code={response.status_code}, headers={response.headers}")

