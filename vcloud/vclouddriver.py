#!/usr/bin/python
#
# VCloud Director - Autoscaling Driver and utility for Brocade vTM
#
# Name:     vclouddriver.py
# Version:  0.1
# Date:     2016-10-21
#  
# Copyright 2016 Brocade Communications Systems, Inc.  All rights reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# Mark Boddington (mbodding@brocade.com), Brocade Communications Systems,Inc.

import sys
import os
import re
import requests
import time
import requests
from requests.auth import HTTPBasicAuth
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element
from xml.etree.ElementTree import ElementTree


class VCloudManager(object):

    def __init__(self, api, org=None, vdc=None, timeout=60):

        NAME_SPACE = "http://www.vmware.com/vcloud/v1.5"
        XML_VERSION = "application/*+xml;version=5.1"

        if api.endswith('/') is False:
            api += "/"

        self.api = api
        self.ns = NAME_SPACE
        self.xmlVer = XML_VERSION
        self.org = org
        self.vdc = vdc
        self.headers = None
        self.config = None
        self.orgs = None
        self.vdcs = None
        self.vapps = None
        self.vms = None
        self.templates = None
        self.networks = None
        self.task = None
        self.timeout = timeout
        self.terminate_on_shutdown = True
        self._setup_name_space()

    def _setup_name_space(self):
        ET.register_namespace("", self.ns)
        ET.register_namespace("ovf", "http://schemas.dmtf.org/ovf/envelope/1")
        ET.register_namespace("ovfenv", "http://schemas.dmtf.org/ovf/environment/1")
        ET.register_namespace("vmext", "http://www.vmware.com/vcloud/extension/v1.5")
        ET.register_namespace("cim", "http://schemas.dmtf.org/wbem/wscim/1/common")
        ET.register_namespace("rasd", "http://schemas.dmtf.org/wbem/wscim/1/" +
            "cim-schema/2/CIM_ResourceAllocationSettingData")
        ET.register_namespace("vssd", "http://schemas.dmtf.org/wbem/wscim/1/" +
            "/cim-schema/2/CIM_VirtualSystemSettingData")
        ET.register_namespace("vmw", "http://www.vmware.com/schema/ovf")
        ET.register_namespace("xsi", "http://www.w3.org/2001/XMLSchema-instance")

    def _get_orgs(self):
        self.orgs = {}
        for org in self.config["Session"].findall(".//{" + self.ns + "}Link[@type=" +
            "'application/vnd.vmware.vcloud.org+xml']"):
            self.orgs[org.attrib.get("name")] = org.attrib.get("href")

    def _get_vdcs(self, org):
        self.vdcs = {}
        for vdc in self.config["ORG"][org].findall(".//{"+ self.ns + "}Link[@type=" +
            "'application/vnd.vmware.vcloud.vdc+xml']"):
            self.vdcs[vdc.attrib.get("name")] = vdc.attrib.get("href")

    def _get_vapps(self, vdc):
        self.vapps = {}
        self.templates = {}
        for vapp in self.config["VDC"][vdc].findall(".//{"+ self.ns + "}ResourceEntity"):
            appType = vapp.attrib.get("type")
            if appType == 'application/vnd.vmware.vcloud.vApp+xml':
                self.vapps[vapp.attrib.get("name")] = vapp.attrib.get("href")
            elif appType == 'application/vnd.vmware.vcloud.vAppTemplate+xml':
                self.templates[vapp.attrib.get("name")] = vapp.attrib.get("href")

    def _get_networks(self, vdc):
        self.networks = {}
        for net in self.config["VDC"][vdc].findall(".//{"+ self.ns + "}Network" +
            "[@type='application/vnd.vmware.vcloud.network+xml']"):
            self.networks[net.attrib.get("name")] = net.attrib.get("href")

    def _get_virtual_machines(self, vapp):
        self.vms = {}
        for v in self.config["VAPP"][vapp].findall(".//{"+ self.ns +"}Vm"):
            self.vms[v.attrib.get("name")] = v.attrib.get("href")

    def _check_args(self, org, vdc):
        if self.config is None:
            raise Exception("ERROR: You must call setupSession() first!")
        if org is None:
            if self.org is None:
                raise Exception("ERROR: You didn't provide a default ORG to VCloudManager(), so you must provide one here")
            else:
                org = self.org
        if vdc is None:
            if self.vdc is None:
                raise Exception("ERROR: You didn't provide a default VDC to VCloudManager(), so you must provide one here")
            else:
                vdc = self.vdc
        return [ org, vdc ]

    def _do_get_config(self, name, dictionary):
        if name not in dictionary:
            raise Exception("ERROR: Could not locate configuration for: {}.".format(name))
        response = requests.get(dictionary[name], headers=self.headers)
        if response.status_code != 200:
            raise Exception("HTTP Request Failed: {}".format(response.status_code))
        return ET.fromstring(response.text)

    def setup_session(self, user, password):
        url = self.api + "sessions"
        auth = HTTPBasicAuth(user, password)
        self.headers = {"Accept": self.xmlVer}
        response = requests.post(url, headers=self.headers, auth=auth)
        if response.status_code != 200:
            raise Exception("Authentication Failed: {}".format(response.status_code))
        self.headers['x-vcloud-authorization'] = response.headers['x-vcloud-authorization']
        self.config = { "Session": ET.fromstring(response.text), "ORG": {}, "NET": {},
            "VDC": {}, "VAPP": {}, "TMPL": {}, "VMS": {} }

    def close_session(self):
        self.headers = None
        self.config = None

    def dump_xml(self, config):
        for entry in self.config.keys():
            if config is None or config == entry:
                print "Dumping {} =================".format(entry)
                if type(self.config[entry]) is dict:
                    for item in self.config[entry].keys():
                        print "Dumping {} - {}".format(entry, item)
                        ET.dump(self.config[entry][item])
                else:
                    ET.dump(self.config[entry])

    def dump_config(self, xml=False, config=None):
        if self.config is None:
            raise Exception("ERROR: You must call setupSession() first!")

        if xml:
            self.dump_xml(config)

        if self.orgs is not None:
            print "Dumping ORG ================="
            print "Orgs: {}".format(self.orgs.keys())

        if self.vdcs is not None:
            print "Dumping VDC ================="
            print "VDCs: {}".format(self.vdcs.keys())

        if self.vapps is not None:
            print "Dumping VAPP ================="
            print "VApps: {}".format(self.vapps.keys())
            print "Templates: {}".format(self.templates.keys())

        if self.networks is not None:
            print "Dumping NET ================="
            print "Nets: {}".format(self.networks.keys())

    def list_orgs(self):
        self._check_args("", "")
        self._get_orgs()
        return self.orgs

    def get_org_config(self, org=None):
        org, vdc = self._check_args(org, "")
        self._get_orgs()
        self.config["ORG"][org] = self._do_get_config(org, self.orgs)
        return self.config["ORG"][org]

    def list_vdcs(self, org=None):
        org, vdc = self._check_args(org, "")
        if org not in self.config["ORG"].keys():
            self.get_org_config(org)
        self._get_vdcs(org)
        return self.vdcs

    def get_vdc_config(self, org=None, vdc=None):
        org, vdc = self._check_args(org, vdc)
        if org not in self.config["ORG"].keys():
            self.get_org_config(org)
        self._get_vdcs(org)
        self.config["VDC"][vdc] = self._do_get_config(vdc, self.vdcs)
        return self.config["VDC"][vdc]

    def list_vapps(self, org=None, vdc=None):
        org, vdc = self._check_args(org, vdc)
        if vdc not in self.config["VDC"].keys():
            self.get_vdc_config(org, vdc)
        self._get_vapps(vdc)
        return self.vapps

    def list_vapp_templates(self, org=None, vdc=None):
        self.list_vapps(org, vdc)
        return self.templates

    def get_vapp_config(self, vapp, org=None, vdc=None):
        self.list_vapps(org, vdc)
        self.config["VAPP"][vapp] = self._do_get_config(vapp, self.vapps)
        return self.config["VAPP"][vapp]

    def get_vapp_template_config(self, vapp, org=None, vdc=None):
        self.list_vapps(org, vdc)
        self.config["TMPL"][vapp] = self._do_get_config(vapp, self.templates)
        return self.config["TMPL"][vapp]

    def list_vapp_vms(self, vapp, org=None, vdc=None):
        org, vdc = self._check_args(org, vdc)
        if vapp not in self.config["VAPP"].keys():
            self.get_vapp_config(vapp, org, vdc)
        self._get_virtual_machines(vapp)
        return self.vms

    def get_vapp_vm_config(self, vapp, vm, org=None, vdc=None):
        self.list_vapp_vms(vapp, org, vdc)
        self.config["VMS"][vm] = self._do_get_config(vm,self.vms)
        return self.config["VMS"][vm]

    def get_network_config(self, network, org=None, vdc=None):
        org, vdc = self._check_args(org, vdc)
        if self.config is None:
            raise Exception("ERROR: You must call setupSession() first!")
        if self.vdcs is None:
            self.get_vdc_config(org,vdc)
        self._get_networks(vdc)
        if network not in self.networks: 
            raise Exception("ERROR: Unkown Network: {}".format(network))
        response = requests.get(self.networks[network], headers=self.headers)
        if response.status_code != 200:
            raise Exception("GetNetworkConfig Failed: {}".format(response.text))
        self.config["NET"][network] = ET.fromstring(response.text)
        return self.config["NET"][network]

    def get_task_status(self, task):
        uri = task.get("href")
        response = requests.get(uri, headers=self.headers)
        if response.status_code != 200:
            sys.stderr.write("CODE: {}\n".format(response.status_code))
            sys.stderr.write("DATA: {}\n".format(response.text))
            raise Exception("Failed to get task. Code: {},".format(response.status_code) +
                " Data: {}".format(response.text))
        return ET.fromstring(response.text)

    def wait_for_task(self, task):
        start = time.time()
        status = task.get("status")
        while status == "running":
            sys.stderr.write(".")
            if time.time() - start > self.timeout:
                return "running"
            time.sleep(5)
            task = self.get_task_status(task)
            status = task.get("status")
        return status

    def submit_task(self, uri, name="Task", ct=None, data=None):
        headers = self.headers
        if ct is not None:
            headers["Content-Type"] = ct
        response = requests.post(uri, headers=headers, data=data)
        if response.status_code != 202:
            sys.stderr.write("POST: {}\n".format(uri))
            sys.stderr.write("Headers: {}\n".format(headers))
            sys.stderr.write("DATA: {}\n".format(data))
            raise Exception("ERROR: Task submission failed. Code: {},".format(response.status_code) +
                " Data: {}".format(response.text))
        sys.stderr.write("{} Running.".format(name))
        task = ET.fromstring(response.text)
        status = self.wait_for_task(task)
        sys.stderr.write("{} Completion Status: {}\n".format(name, status))
        return status

    def add_vm_to_vapp(self, vapp, template, network, vm):
        if template not in self.templates.keys():
            raise Exception("Template has not been discovered: {}".format(template))
        if network not in self.networks.keys():
            raise Exception("Network has not been discovered: {}".format(network))
        rvo = RecomposeVAppObject(self.ns)
        rvo.add_vm_to_vapp(network, self.networks[network], vm, template, self.config)
        xml = rvo.to_string()
        uri = self.vapps[vapp] + "/action/recomposeVApp"
        ct = "application/vnd.vmware.vcloud.recomposeVAppParams+xml"
        status = self.submit_task(uri, "Recompose VAPP", ct, xml)
        if status == "success":
            self.get_vapp_config(vapp)
            self.list_vapp_vms(vapp)
            if vm in self.vms:
                status = self.poweron(vm)
        return status

    def del_vm_from_vapp(self, vapp, vm):
        if self.vms is None or vm not in self.vms:
            self.get_vapp_vm_config(vapp, vm)
        if vm not in self.vms:
            raise Exception("Unknown VM: {}".format(vm))

        self.shutdown(vm)
        rvo = RecomposeVAppObject(self.ns)
        rvo.del_vm_from_vapp(self.vms[vm])
        xml = rvo.to_string()
        uri = self.vapps[vapp] + "/action/recomposeVApp"
        ct = "application/vnd.vmware.vcloud.recomposeVAppParams+xml"
        status = self.submit_task(uri, "Recompose VAPP", ct, xml)
        return status
        
    def poweron(self, vm):
        if vm not in self.vms:
            raise Exception("ERROR: Unknown VM: {}".format(vm))
        uri = self.vms[vm] + "/power/action/powerOn"
        status = self.submit_task(uri, "Power On")
        return status

    def shutdown(self, vm):
        if vm not in self.vms:
            raise Exception("ERROR: Unknown VM: {}".format(vm))
        uri = self.vms[vm] + "/action/undeploy"
        ct = "application/vnd.vmware.vcloud.undeployVAppParams+xml"
        upa = Element("UndeployPowerAction")
        if self.terminate_on_shutdown:
            upa.text = "powerOff"
        else:
            upa.text = "shutdown"
        uvp = Element("{"+ self.ns + "}UndeployVAppParams")
        uvp.append(upa)
        xml = ET.tostring(uvp)
        status = self.submit_task(uri, "Power Off", ct, xml)
        return status


class RecomposeVAppObject(ElementTree):

    def __init__(self, ns, text="Recompose VApp"):

        root = Element("RecomposeVAppParams")
        super(RecomposeVAppObject, self).__init__(root)    
        self.ns = ns
        desc = Element("Description")
        desc.text = text
        root.append(desc)

    def add_vm_to_vapp(self, netName, netLink, vmName, template, config):
        if netName not in config["NET"].keys():
            raise Exception("Network has not been discovered: {}".format(netName))
        if template not in config["TMPL"].keys():
            raise Exception("Template has not been discovered: {}".format(template))

        # Configure the Network
        #instParams = Element("InstantiationParams")
        #netConfSection = Element("NetworkConfigSection")
        #ovfInfo = Element("ovf:Info", msgid="")
        #ovfInfo.text = "Configuration parameters for logical networks"
        #netConfig = Element("NetworkConfig", networkName=netName)
        #configuration = Element("Configuration")
        #ipScope = config["NET"][netName].find(".//{" + self.ns + "}IpScope" )
        ##fenceMode = config["NET"][netName].find(".//{" + self.ns + "}FenceMode" )
        #RNIAD = config["NET"][netName].find(".//{" + self.ns + "}RetainNetInfoAcrossDeployments" )
        #parentNet = Element("ParentNetwork", href=netLink, type="application/vnd.vmware.vcloud.orgNetwork+xml", name=netName )
        ##configuration.append(ipScope)
        #configuration.append(parentNet)
        #configuration.append(fenceMode)
        #configuration.append(RNIAD)
        #netConfig.append(configuration)
        #netConfSection.append(ovfInfo)
        #netConfSection.append(netConfig)
        #instParams.append(netConfSection)
        #self._root.append(instParams)

        # Configure the Template
        sourcedItem = Element("SourcedItem")
        vm = config["TMPL"][template].find(".//{" + self.ns + "}Vm")
        source = Element("Source", href=vm.attrib.get("href"), name=vmName)
        instParams = Element("InstantiationParams")
        netConfig = config["TMPL"][template].find(".//{" + self.ns + "}NetworkConnectionSection")
        netConfig.find(".//{" + self.ns + "}NetworkConnection").set("network", netName)
        instParams.append(netConfig)
        sourcedItem.append(source)
        sourcedItem.append(instParams)
        self._root.append(sourcedItem)

    def del_vm_from_vapp(self, nodeLink):
        delItem = Element("{" + self.ns + "}DeleteItem", href=nodeLink)
        self._root.append(delItem)

    def dump(self):
        self.write(sys.stdout, encoding="utf-8", xml_declaration=True, method="xml")

    def to_string(self, encoding="utf-8", method="xml"):
        return ET.tostring(self._root, encoding, method)
        
def main():
    pass

if __name__ == "__main__":
    main()
