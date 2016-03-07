#!/usr/bin/python
#
# Google Compute Engine - Autoscaling Driver and utility for Brocade vTM
#
# Name:     googledriver.py
# Version:  1.0
# Date:     2016-03-07
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
import json
import requests
import time

class GoogleComputeManager:

    api = "https://www.googleapis.com/compute/v1/projects/"
    authUri = "http://metadata/computeMetadata/v1/instance/service-accounts" + \
              "/default/token"
    localAuth = True
    instances = {}
    instUri = None
    project = None
    zone = None
    authState = None
    creds = None

    def __init__(self, project, zone, authFile=None, authState=None):

        if authFile is not None:
            self.localAuth = False
            af = open(authFile,"r")
            self.creds = json.load(af)
            af.close()
        else:
            self.creds = {}

        if authState is not None and os.path.exists(authState):
            sf = open(authState,"r")
            update = json.load(sf)
            sf.close()
            self.creds.update(update)

        self.authState = authState
        self.project = project
        self.zone = zone
        self.instUri = self.api + project + "/zones/" + zone + "/instances" 
        
    def newInst(self, name, image, machineType=None, project=None, zone=None):
        project = self.project if project is None else project
        zone = self.zone if zone is None else zone
        instance = GoogleComputeInstance(name,project,zone,image,machineType)
        self.instances[name] = instance

    def newDevVTM(self, name, script=None, solutionKey=None):
        self.newInst(name, 'brocade-public-1063:vtm-103-stm-dev-64')
        self.instances[name].addTags( ["http-server", "https-server", \
                            "tcp-9090-server", "google-cloud-marketplace"] )
        if script is not None:
            self.instances[name].addScript(script)

        self.instances[name].addMeta("google-cloud-marketplace-solution-key", \
            "brocade-public-1063:stm-dev")

    def auth(self):
        now = time.time()
        if "access_token" not in self.creds.keys():
            # No access token
            self.refreshToken()
        elif "expires" not in self.creds.keys():
            # No expires time
            self.refreshToken()
        elif self.creds["expires"] - now <= 2:
            # Token has expired or is close
            if self.creds["expires"] - now > 0:
                time.sleep(3)
            self.refreshToken()
            
    def refreshToken(self):
        if self.localAuth == True:
            headers = { 'Metadata-Flavor': 'Google' }
            response = requests.get( self.authUri, headers=headers)
            update = json.loads(response.text)
        else:
            data = {
                'client_id': self.creds['client_id'],
                'client_secret': self.creds['client_secret'],
                'refresh_token': self.creds['refresh_token'],
                'grant_type': 'refresh_token'
            }
            response = requests.post(self.creds['token_uri'], data=data)
            update = response.json()

        self.creds['access_token'] = update['access_token']
        self.creds['expires'] = 0 + time.time() + update['expires_in']
        if self.authState is not None:
            sf = open(self.authState, "w")
            json.dump(self.creds,sf)
            sf.close()
    
    def start(self, name):
        inst = self.instances[name]
        headers = { 'Authorization': 'Bearer ' + self.creds['access_token'], \
            "Content-Type": "application/json" }
        response = requests.post( self.instUri, data = json.dumps(inst.conf),\
            headers = headers )
        return response.json()

    def status(self, name=None):
        if name is None:
            uri = self.instUri
        else:
            uri = self.instUri + "/" + name
        headers = { 'Authorization': 'Bearer ' + self.creds['access_token'] }
        response = requests.get( uri, headers=headers )
        if response.status_code != 200:
            ret = { "FAILED": True, "Code": response.status_code, 
                    "Error": response.text}
            return ret
        return response.json()

    def stop(self, name):
        headers = { 'Authorization': 'Bearer ' + self.creds['access_token'] }
        print "Stopping -> " + self.instUri + "/" + name + "/stop"
        response = requests.post( self.instUri + "/" + name + "/stop", \
            headers = headers )
        return response.json()

    def delete(self, name):
        headers = { 'Authorization': 'Bearer ' + self.creds['access_token'] }
        response = requests.delete( self.instUri + "/" + name, headers=headers)
        return response.json()

    def getDiskInfo(self, disk):
        headers = { 'Authorization': 'Bearer ' + self.creds['access_token'] }
        diskUri = self.instUri.rsplit('/',1)[0] + "/disks/" + disk
        response = requests.get( diskUri, headers=headers)
        return response.json()

	
class GoogleComputeInstance:

    deployed = False
    name = None
    machineType = "n1-standard-1"
    imageSrc = None
    image = "vtm-103-stm-dev-64"

    endpoint = "https://www.googleapis.com/compute/v1/projects/"
    zone = "europe-west1-b"
    project = None

    conf = {
        "name": None,
        "zone": None,
        "machineType": None,
        "metadata": { "items": [ ] },
        "tags": { "items": [ ] },
        "disks": [
            {
                "type": "PERSISTENT",
                "boot": True,
                "mode": "READ_WRITE",
                "autoDelete": True,
                "deviceName": None,
                "initializeParams": {
                    "sourceImage": None,
                    "diskType": None,
                    "diskSizeGb": "16"
                }
            }
        ],
        "canIpForward": False,
        "networkInterfaces": [
            {
                "network": None,
                "accessConfigs": [
                    {
                        "name": "External NAT",
                        "type": "ONE_TO_ONE_NAT"
                    }
                ] 
            }
        ],
        "description": "",
        "scheduling": {
            "preemptible": False,
            "onHostMaintenance": "MIGRATE",
            "automaticRestart": True
        },
        "serviceAccounts": [
            {
                "email": "default",
                "scopes": [
                    "https://www.googleapis.com/auth/cloud-platform"
                ]
            }
        ]
    }

    def __init__( self, name, project, zone, image, machineType=None ):
        self.name = name
        self.project = project
        self.zone = zone
        if ':' in image:
            imageSrc, image = image.split(':')
            imageSrc += "/global/images/" + image
        else:
            imageSrc = project + "/global/images/"+ image
        imageSrc = self.project if imageSrc is None else imageSrc
        machineType = self.machineType if machineType is None else machineType

        self.conf["name"] = name
        self.conf["zone"] = "projects/" + project + "/zones/" + zone
        self.conf["machineType"] = ""+ self.conf["zone"] + "/machineTypes/" + \
            machineType 
        self.conf["disks"][0]["deviceName"] = name
        self.conf["disks"][0]["initializeParams"]["sourceImage"] = "https://" \
            + "www.googleapis.com/compute/v1/projects/" + imageSrc
        self.conf["disks"][0]["initializeParams"]["diskType"] = \
            self.conf["zone"] + "/diskTypes/pd-standard"
        self.conf["networkInterfaces"][0]["network"] = "projects/" + project \
            + "/global/networks/default",

    def addTag(self, tag):
        self.conf["tags"]["items"].append( tag )

    def addTags(self, tags):
        for tag in tags:
            self.addTag(tag)

    def addMeta(self, key, value):
        self.conf["metadata"]["items"].append( { "key": key, "value": value })

    def addScript(self, script):
        self.addMeta("startup-script", script)

# Script Functions

def help():
    text="""
    Usage: googledriver.py [--help] action options

        action: [status|createnode|destroynode]

        common options:
            --verbose=1          Print verbose logging messages to the CLI
            --cloudcreds=<file>  Zeus config file containing the credentials

        alternatively set credentials manually:
            --cred1=<username:password> or "local" 
            --cred2=<project>
            --cred3=<region>

        action-specific options:
        ------------------------

        createnode
            --name=<nodename>    Name to give the new node
            --imageid=<imageid>  The disk image [<project>:]<image>
            --sizeid=<size>      The machine type to use

        destroynode
            --id=<uniqueid>      ID of the node to delete
            --name=<nodename>    Name of the node to delete

        status
            --name=<nodename>    Display the status of the named node only.
            --google             Show Google API version, not the vTM version.

        authclient
            --clientid=<id>      The OAuth Client ID for your project
            --secret=<secret>    The OAuth Client Secret

"""
    sys.stderr.write(text)
    sys.exit(1)

def convertNodeData(opts,gcm,item):
    node = { "uniq_id": item['id'], "name": item["name"], \
        "status": item["status"], \
        "created": item["creationTimestamp"], \
        "private_ip": item["networkInterfaces"][0]["networkIP"], \
        "public_ip": \
            item["networkInterfaces"][0]["accessConfigs"][0]["natIP"] \
    }
    disk = gcm.getDiskInfo(item["name"])
    si = disk["sourceImage"].split("/projects/")[1].split("/global/images/")
    if si[0] == opts["cred2"]:
        node["imageid"] = si[1]
    else:
        node["imageid"] = ':'.join(si)

    node['sizeid'] = item['machineType'].rsplit('/',1)[1]

    if ( node["status"] == "PENDING" ):
        node["status"] = "pending"
        node["complete"] = 33
    elif ( node["status"] == "STAGING" ):
        node["status"] = "pending"
        node["complete"] = 66
    elif ( node["status"] == "RUNNING" ):
        node["status"] = "active"
        node["complete"] = 100
    elif ( node["status"] == "STOPPING" ):
        node["status"] = "destroyed"
        node["complete"] = 100
    else:
        node["status"] = "pending"
        node["complete"] = 50
    return node

def getStatus(opts, gcm):
    nodes = []
    if "name" in opts.keys():
        nodeStatus = gcm.status(opts["name"])
        if "FAILED" in nodeStatus.keys():
            status = nodeStatus
        else:
            status = { "items": [ nodeStatus ] }
    else:
        status = gcm.status()

    if ( "FAILED" in status.keys() ):
            sys.stderr.write("Failed to get Status for project: " + \
                opts["cred2"])
            sys.stderr.write(", zone: " + opts["cred3"] + "\n")
            sys.stderr.write("API Response: {}, {}\n".format( status["Code"], \
                status["Error"] ) )
            sys.exit(1)
    
    if "google" in opts.keys():
        print json.dumps(status)
        return

    if "items" in status.keys():
        for item in status["items"]:
            node = convertNodeData(opts, gcm, item)
            nodes.append(node)
    ret = { "NodeStatusResponse":{ "version": 1, "code": 200, "nodes": nodes }}
    print json.dumps(ret)

def addNode(opts, gcm):
    if "name" not in opts.keys() or "imageid" not in opts.keys() or \
        "sizeid" not in opts.keys():
        sys.stderr.write("ERR - You must provide --name, --imageid, ")
        sys.stderr.write("and --sizeid to create node\n")
        sys.exit(1)
    timeout = opts['timeout'] if 'timeout' in opts.keys() else 30
    loop = timeout / 5

    gcm.newInst(opts["name"], opts["imageid"], opts["sizeid"])
    result = gcm.start(opts["name"])
    for x in xrange(loop):
        myNode = gcm.status(opts["name"])
        if "status" in myNode.keys() and myNode["status"] == "RUNNING":
            break
        time.sleep(5)
    myNode = convertNodeData(opts, gcm, myNode)
    ret = { "CreateNodeResponse":{"version":1, "code":202, "nodes":[ myNode ]}}
    print json.dumps(ret)

def delNode(opts, gcm):
    if "name" not in opts.keys() and "id" not in opts.keys():
        sys.stderr.write("ERR - please provide --name or --id to delete node\n")
        sys.exit(1)
    timeout = opts['timeout'] if 'timeout' in opts.keys() else 30
    loop = timeout / 5

    myNode = None
    nodes = gcm.status()
    for item in nodes["items"]:
        if "name" in opts.keys() and item["name"] == opts["name"]:
            myNode = item
            break
        elif "id" in opts.keys() and item["id"] == opts["id"]:
            myNode = item
            break

    if myNode is not None:
        gcm.delete(myNode["name"])
        ret = { "DestroyNodeResponse": { "version": 1, "code": 202, "nodes": \
            [{ "created": 0, "uniq_id": myNode['id'], "status": "destroyed", \
            "complete": "80"}]}}
    else:
        opts["id"] = None if "id" not in opts.keys() else opts["id"]
        ret = { "DestroyNodeResponse": { "version": 1, "code": 202, "nodes": \
            [{ "created": 0, "uniq_id": opts['id'], "status": "destroyed", \
            "complete": "80"}]}}

    print json.dumps(ret)

def authMe(opts):
    from oauth2client.client import OAuth2WebServerFlow
    import logging
    logging.basicConfig(filename='/dev/null',level=logging.DEBUG)
    scopes = ("https://www.googleapis.com/auth/compute",)
    if "clientid" not in opts.keys() or "secret" not in opts.keys():
        sys.stderr.write("ERR - You must provide --clientid and --secret\n");
        sys.exit(1)
    flow = OAuth2WebServerFlow(opts['clientid'], opts['secret'], \
        " ".join(scopes), "urn:ietf:wg:oauth:2.0:oob", "BrocadeVTM")
    print "Open the following URL in your browser to authorize this client: "
    print "\n" + flow.step1_get_authorize_url() + "\n"
    auth_code = raw_input("Please enter the authorization code: ")

    credentials = flow.step2_exchange(code=auth_code)
    print("Access token:  {0}".format(credentials.access_token))
    print("Refresh token: {0}".format(credentials.refresh_token))

    print credentials.to_json()

# Open and parse the credentials file
def getCCopts(opts):

    opts["ZH"] = os.environ.get("ZEUSHOME")
    if opts["ZH"] == None:
        if os.path.isdir("/usr/local/zeus"):
            opts["ZH"] = "/usr/local/zeus";
        elif os.path.isdir("/opt/zeus"):
            opts["ZH"] = "/opt/zeus";
        else:
            sys.stderr.write("ERR - Can not find ZEUSHOME\n")
            sys.exit(1)

    ccFile = opts["ZH"] + "/zxtm/conf/cloudcredentials/" + opts["cloudcreds"]
    if os.path.exists(ccFile) is False:
        sys.stderr.write("ERR - Cloud config does not exist: "+ ccFile +"\n")
        sys.exit(1)
    ccFH = open( ccFile, "r")
    for line in ccFH:
        kvp = re.search("(\w+)\s+(.*)", line.strip() )
        if kvp != None:
            opts[kvp.group(1)] = kvp.group(2)
    ccFH.close()

def main():
    opts = {"verbose": 0 }

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

    if action.lower() in ('status','createnode','destroynode'):
        # We need cloud credentials... 
        if "cloudcreds" in opts.keys():
            getCCopts(opts)

        # Credential 1 should be "local" if running in GCE, in which case we,
        # use the metadata server. Or it should be an OATH2 config file.
        # The config file should be in json format, and contain:
        # token_uri, refresh_token, client_id, client_secret.

        # Set cred1 to None if we don't have it, GCM will do local metadata auth
        if "cred1" not in opts.keys():
            opts["cred1"] = None
        # Set cred1 to None if its "local", GCM will do local metadata auth
        elif opts["cred1"].lower() == "local":
            opts["cred1"] = None
        # Else locate the authentication file provided.
        else:
            if os.path.exists( opts["cred1"] ) == False:
                if "ZH" in opts.keys():
                    path = opts["ZH"] + "/zxtm/conf/extra/" + opts["cred1"]  
                    if os.path.exists(path):
                        opts["cred1"] = path
                    else:                  
                        sys.stderr.write("ERR - Can not find OAUTH2 Config " \
                            "file: "+ opts["cred1"]  +"\n")
                        sys.exit(1)

        # Store state in zxtm/internal if being run by vTM
        if "statefile" not in opts.keys():
            if "ZH" in opts.keys():
                opts["statefile"] = opts["ZH"] + "/zxtm/internal/gce." + \
                    opts["cloudcreds"] + ".state"
            else:
                opts["statefile"] = None

        # Credential 2 should be our project
        if "cred2" not in opts.keys():
            sys.stderr.write("ERR - You must supply your project ID in cred2\n")
            sys.exit(1)

        # Credential 3 should be our region
        if "cred3" not in opts.keys():
            sys.stderr.write("ERR - You must supply your Region in cred3\n")
            sys.exit(1)

        # Set up the GCM
        gcm = GoogleComputeManager(opts["cred2"], opts["cred3"], 
              opts["cred1"], opts["statefile"])
        gcm.auth()

    # Check the action and call the appropriate function
    if action.lower() == "help":
        help()
    elif action.lower() == "status":
        getStatus(opts, gcm)
    elif action.lower() == "createnode":
        addNode(opts, gcm)
    elif action.lower() == "destroynode":
        delNode(opts, gcm)
    elif action.lower() == "authclient":
        authMe(opts)
    else:
        help()
   

if __name__ == "__main__":
    main()
