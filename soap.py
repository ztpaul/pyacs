#!/usr/bin/env python3
# Author: Alexander Couzens <lynxis@fe80.eu>
# (C) 2021 by sysmocom - s.f.m.c. GmbH <info@sysmocom.de>


import logging

class Soap:
    log = logging.getLogger('Soap')
    m_methods = ('GetRPCMethods', 'Inform') #RPC methods that ACS have supported.
    m_namespace = {
        'soap-env': 'http://schemas.xmlsoap.org/soap/envelope/',
        'cwmp': 'urn:dslforum-org:cwmp-1-2'
    }
        


    def get_cwmp_method(self, root):
        """ retrieve the cwmp method from the xml root Node """
        body = root.find('soap-env:Body', Soap.m_namespace)
        if body is None:
            logging.error('find soap-env:Body failed')
            return None

        prefix = '{' + Soap.m_namespace['cwmp'] + '}'
        for child in body:
            for method in Soap.m_methods:            
                if child.tag == prefix + method:
                    return (method, child)

            if child.tag == prefix+ 'SetParameterValuesResponse':
                return ('SetParameterValuesResponse', child)
        return None

    def get_cwmp_id(self, root):
        """ retrieve the cwmp id """
        header = root.find('soap-env:Header', Soap.m_namespace)
        if header is None:
            return None

        prefix = '{' + Soap.m_namespace['cwmp'] + '}'
        cwmpid = header.find(prefix+ 'ID', Soap.m_namespace)
        if cwmpid is not None:
            return cwmpid.text
        return None

    def get_cwmp_inform_events(self, inform):
        """ return a list of Inform Events """
        eventnode = inform.find('Event')
        if eventnode is None:
            return None

        events = []
        """ parse
                <Event soap-enc:arrayType="cwmp:EventStruct[2]"
                    <EventStruct>
                        <EventCode>4 VALUE CHANGE</EventCode>
                        <CommandKey></CommandKey>
                    </EventStruct>
                    <EventStruct>
                        <EventCode>0 BOOTSTRAP</EventCode>
                        <CommandKey></CommandKey>
                    </EventStruct>
                </Event>
        """
        for ev in eventnode:
            if ev.tag != "EventStruct":
                continue

            evcodenode = ev.find('EventCode')
            events.append(evcodenode.text)
        return events

    def get_cwmp_inform_sn(self, inform):
        """ retrieve the sn from an inform node """
        device_id = inform.find('DeviceId')
        if device_id is None:
            return None

        sn = device_id.find('SerialNumber')
        if sn is None:
            return None
        return sn.text

    def get_cwmp_setresponse_status(self, setparametervaluesresponse):
        """ retrieve the status from a setparametervaluesresponse node """
        statusnode = setparametervaluesresponse.find('Status')
        if statusnode is None:
            return None
        return statusnode.text
