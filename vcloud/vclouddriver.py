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
import json
from requests.auth import HTTPBasicAuth
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element
from xml.etree.ElementTree import ElementTree


class VCloudManager(object):

    def __init__(self, api, org=None, vdc=None, verbose=0, timeout=60):

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
        self.verbose = verbose
        self.terminate_on_shutdown = True
        self._setup_name_space()

    def _debug(self, msg):
        if self.verbose:
            sys.stderr.write("DEBUG: {}".format(msg))

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
        self._debug("HTTP GET for: {}, Calling: {}\n".format(name, dictionary[name]))
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
        if vdc not in self.config["VDC"].keys():
            self.get_vdc_config(org,vdc)
        self._get_networks(vdc)
        self.config["NET"][network] = self._do_get_config(vdc, self.vdcs)
        return self.config["NET"][network]

    def get_vm_status(self, vapp, vm=None):
        vms = self.list_vapp_vms(vapp) if vm is None else [ vm ]
        status = {}
        for vm in vms:
            config = self.get_vapp_vm_config(vapp, vm)
            status[vm] = {"status": config.attrib.get("status"),
                          "id": config.attrib.get("id"),
                          "name": config.attrib.get("name"),
                          "needsCustomization": config.attrib.get("needsCustomization"),
                          "deployed": config.attrib.get("deployed"),
                          "nets": {}}
            net_conns = config.findall('.//{' + self.ns + '}NetworkConnection')
            for net in net_conns:
                network = net.attrib.get("network")
                status[vm]["nets"][network] = net.find('.//{' + self.ns + '}IpAddress').text
        return status

    def get_task_status(self, task):
        uri = task.get("href")
        response = requests.get(uri, headers=self.headers)
        if response.status_code != 200:
            self._debug("CODE: {}\n".format(response.status_code))
            self._debug("DATA: {}\n".format(response.text))
            raise Exception("Failed to get task. Code: {},".format(response.status_code) +
                " Data: {}".format(response.text))
        return ET.fromstring(response.text)

    def wait_for_task(self, task):
        start = time.time()
        status = task.get("status")
        while status == "running":
            self._debug(".")
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
            self._debug("POST: {}\n".format(uri))
            self._debug("Headers: {}\n".format(headers))
            self._debug("DATA: {}\n".format(data))
            raise Exception("ERROR: Task submission failed. Code: {},".format(response.status_code) +
                " Data: {}".format(response.text))
        self._debug("{} Running.".format(name))
        task = ET.fromstring(response.text)
        status = self.wait_for_task(task)
        self._debug("{} Completion Status: {}\n".format(name, status))
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
        
# Script Functions

def help():
    text="""
    Usage: vclouddriver.py [--help] action options

        action: [status|createnode|destroynode|get-vdc-info]

        common options:
            --verbose=1          Print verbose logging messages to the CLI
            --cloudcreds=<file>  Zeus config file containing the credentials

        alternatively set credentials manually:
            --cred1=configfile 

        configuration file:
        -------------------

        The config file should include: apiHost, user, pass, org, vdc, vapp,
        and network. You may also override these by passing them on the
        command line. Eg: --apiHost or --vdc

        action-specific options:
        ------------------------

        createnode                Add a node to the cloud

            --name=<nodename>     Name to give the new node
            --imageid=<template>  The template to use 
            --sizeid=<size>       Not used

        destroynode         Remove a node from the cloud

            --id=<uniqueid>     ID of the node to delete
            --name=<nodename>   Name of the node to delete

        status              Get current node status 

            --name=<nodename>   Display the status of the named node only.

        get-vdc-info          Display a list of resource in your VDC

"""
    sys.stderr.write(text)
    sys.exit(1)

def convertNodeData(opts,vcm,item):
    node = { "uniq_id": item['id'], "name": item["name"],
        "created": "Sat 22 Oct 18:52:12 GMT 2016",
        "private_ip": item["nets"][opts["network"]],
        "public_ip": item["nets"][opts["network"]] }

    status = int(item["status"])
    if ( status < 4 ):
        node["status"] = "pending"
        node["complete"] = 33
    elif ( status == 4 ):
        if ( item["deployed"] == "true" ):
            node["status"] = "active"
            node["complete"] = 100
        else:
            node["status"] = "pending"
            node["complete"] = 66
    else:
        node["status"] = "destroyed"
        node["complete"] = 100
    return node

def get_status(opts, vcm):
    nodes = []
    if "name" in opts.keys():
        status = vcm.get_vm_status(opts["vapp"], opts["name"])
    else:
        status = vcm.get_vm_status(opts["vapp"])

    for vm in status.keys():
        node = status[vm]
        node = convertNodeData(opts,vcm,node)
        nodes.append(node)
    return nodes

def add_node(opts, vcm):
    if "name" not in opts.keys() or "imageid" not in opts.keys():
        sys.stderr.write("ERROR - You must provide --name, and --imageid to create a node\n")
        sys.exit(1)

    vcm.get_vapp_template_config(opts["imageid"])
    vcm.get_network_config(opts["network"])
    status = vcm.add_vm_to_vapp(opts["vapp"], opts["imageid"], opts["network"], opts["name"])
    nodeStatus = vcm.get_vm_status(opts["vapp"], opts["name"])
    myNode = convertNodeData(opts, vcm, nodeStatus[opts["name"]])
    ret = { "CreateNodeResponse":{"version":1, "code":202, "nodes":[ myNode ]}}
    print json.dumps(ret)

def del_node(opts, vcm):
    if "name" not in opts.keys() and "id" not in opts.keys():
        sys.stderr.write("ERROR - please provide --name or --id to delete node\n")
        sys.exit(1)

    myNode = None
    nodes = get_status(opts, vcm)
    for node in nodes:
        if "name" in opts.keys() and node["name"] == opts["name"]:
            myNode = node
            break
        elif "id" in opts.keys() and node["uniq_id"] == opts["id"]:
            myNode = node
            break

    if myNode is not None:
        vcm.del_vm_from_vapp(opts["vapp"], myNode["name"])
        ret = { "DestroyNodeResponse": { "version": 1, "code": 202, "nodes": \
            [{ "created": 0, "uniq_id": myNode['uniq_id'], "status": "destroyed", \
            "complete": "80"}]}}
    else:
        # should probbaly return a 404???
        opts["id"] = None if "id" not in opts.keys() else opts["id"]
        ret = { "DestroyNodeResponse": { "version": 1, "code": 202, "nodes": \
            [{ "created": 0, "uniq_id": opts['id'], "status": "destroyed", \
            "complete": "80"}]}}

    print json.dumps(ret)

def print_table(dictionary, spacing=3):
    for key in dictionary.keys():
        print "\n{}\n{}".format(key,"-"*len(key))
        ml = 0
        for item in dictionary[key].keys():
            ml = len(item) if len(item) > ml else ml
        for item in dictionary[key].keys():
            sp = ml - len(item) + spacing
            print "{}{}:{}".format(item, " "*sp, dictionary[key][item])
        print ""

def get_vdc_info(opts, vcm):
    to_print = {}
    to_print["Organizations"] = vcm.list_orgs()
    to_print["Virtual DCs"] = vcm.list_vdcs()
    to_print["Virtual Apps"] = vcm.list_vapps()
    to_print["Virtual Apps Templates"] = vcm.list_vapp_templates()

    print_table(to_print)

def get_cloud_credentials(opts):

    # Find ZeusHome
    opts["ZH"] = os.environ.get("ZEUSHOME")
    if opts["ZH"] == None:
        if os.path.isdir("/usr/local/zeus"):
            opts["ZH"] = "/usr/local/zeus";
        elif os.path.isdir("/opt/zeus"):
            opts["ZH"] = "/opt/zeus";
        else:
            sys.stderr.write("ERROR - Can not find ZEUSHOME\n")
            sys.exit(1)

    # Open and parse the credentials file
    ccFile = opts["ZH"] + "/zxtm/conf/cloudcredentials/" + opts["cloudcreds"]
    if os.path.exists(ccFile) is False:
        sys.stderr.write("ERROR - Cloud credentials file does not exist: " + ccFile + "\n")
        sys.exit(1)
    ccFH = open( ccFile, "r")
    for line in ccFH:
        kvp = re.search("(\w+)\s+(.*)", line.strip() )
        if kvp != None:
            opts[kvp.group(1)] = kvp.group(2)
    ccFH.close()

    # Check credential 1 is the config file
    if "cred1" in opts.keys():
        opts["cred1"] = opts["ZH"] + "/zxtm/conf/extra/" + opts["cred1"]
        if os.path.exists( opts["cred1"] ) is False:
            sys.stderr.write("ERROR - VCloud config file is missing: " + opts["cred1"] + "\n")
            sys.exit(1)
    else:
        sys.stderr.write("ERROR - Credential 1 must be set to the VCloud config file name\n")
        sys.exit(1)

def setup(opts):

    if "cred1" not in opts.keys():
        get_cloud_credentials(opts)

    osFH = open( opts["cred1"], "r")
    for line in osFH:
        kvp = re.search("(\w+)\s+(.*)", line.strip() )
        if kvp != None:
            # command line args take precedence
            if kvp.group(1) not in opts.keys():
                opts[kvp.group(1)] = kvp.group(2)
    osFH.close()

    if "apiHost" not in opts.keys():
        sys.stderr.write("ERROR - 'apiHost' must be specified in the VCD config file: " + opts["cred1"] + "\n")
        sys.exit(1)

    if "org" not in opts.keys():
        sys.stderr.write("ERROR - 'org' must be specified in the VCD config file: " + opts["cred1"] + "\n")
        sys.exit(1)

    if "vdc" not in opts.keys():
        sys.stderr.write("ERROR - 'vdc' must be specified in the VCD config file: " + opts["cred1"] + "\n")
        sys.exit(1)

    # Store state in zxtm/internal if being run by vTM
    if "statefile" not in opts.keys():
        if "ZH" in opts.keys():
            opts["statefile"] = opts["ZH"] + "/zxtm/internal/vcd." + \
                opts["cloudcreds"] + ".state"
        else:
            opts["statefile"] = None

    # Set up the VCloudManager
    vcm = VCloudManager(opts["apiHost"], opts["org"], opts["vdc"], opts["verbose"])
    vcm.setup_session(opts["user"], opts["pass"])
    vcm.get_vapp_config(opts["vapp"])

    return vcm

def main():
    opts = {"verbose": False }

    # Read in the first argument or display the help
    if len(sys.argv) < 2:
        help()
    else:
        action = sys.argv[1]

    # Process additional arguments
    for arg in sys.argv:
        kvp = re.search("--([^=]+)=*(.*)", arg)
        if kvp != None:
            opts[kvp.group(1)] = kvp.group(2)

    # Check the action and call the appropriate function
    if action.lower() == "help":
        help()
    elif action.lower() == "status":
        vcm = setup(opts)
        nodes = get_status(opts, vcm)
        print json.dumps({ "NodeStatusResponse":{ "version": 1, "code": 200, "nodes": nodes }})
    elif action.lower() == "createnode":
        vcm = setup(opts)
        add_node(opts, vcm)
    elif action.lower() == "destroynode":
        vcm = setup(opts)
        del_node(opts, vcm)
    elif action.lower() == "get-vdc-info":
        vcm = setup(opts)
        get_vdc_info(opts, vcm)
    else:
        help()

if __name__ == "__main__":
    main()
