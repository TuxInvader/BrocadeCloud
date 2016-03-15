#!/bin/bash
#
# Example Script to deploy a vTM using the googledriver.py script.
# vTM is deployed using a specific image, and then configured using the
# startup-script.sh
#
#      Note: startup-script.sh sets the admin password!
#
# This script will then wait for the vTM to start and for the REST api
# to be active, prior to calling "puppet apply" to upload a configuration
# manifest.
#

# Image names for reference. You may use one of these or any other vTM image.
# Execute ./googledriver.py getvtmimgs for a full list
DEVELOPER="vtm-103r1-stm-dev-64"
VTM1000L="vtm-103r1-stm-csub-1000-l"

# Image to use and the GCM authentication details. See documentation and
# execute: ./googledriver.py authclient to generate credentials
img=$VTM1000L 
cfg=/home/mark/gcm.config
hieraYaml=/home/mark/.hiera/global.yaml

# Optionally you can specify a machineType and static Public_IP below.
# You must have pre-registered the IP address in GCP Networking.
# size=n1-standard-2
# vip=a.b.c.d

[ -n "$size" ] && optArgs="$optArgs --sizeid=${size}"
[ -n "$vip" ] && optArgs="$optArgs --natip=${vip}"

###############################################################################
# Deploy the vTM to the cloud and wait for it to be 'active'
###############################################################################

echo "Deploying vTM in Googles Cloud..."
echo ""
echo "googledriver.py createvtm --cred1=$cfg "
echo "    --cred2=fluted-lambda-122413 --cred3=europe-west1-b --name=vtm1"
echo "    --imageid=$img"
echo "    $optArgs"
echo ""

./googledriver.py createvtm --cred1=$cfg \
    --cred2=fluted-lambda-122413 --cred3=europe-west1-b --name=vtm1 \
    --script=startup-script.sh --imageid=$img $optArgs

# Poll Google and wait for the vtm to status to be "active"
active=1
while [ $active -ne 0 ]
do
    echo "Waiting for VTM to start...."
    sleep 10
    status=$(./googledriver.py status --cred1=/home/mark/gcm.config --cred2=fluted-lambda-122413 --cred3=europe-west1-b --name=vtm1 | grep active)
    active=$?
done
echo -e "Status: $status\n"

###############################################################################
# The rest of the script is here to push a configuration to vTM using Puppet.
###############################################################################

# First write the public IP to the hiera database, so puppet can find it..
echo -e "Updating Heira\n"
ip=$(./googledriver.py status --cred1=/home/mark/gcm.config --cred2=fluted-lambda-122413 --cred3=europe-west1-b --name=vtm1 | sed -e's/.*public_ip": "\([^"]*\).*/\1/')
cat > $hieraYaml <<EOF
---
googleIP: "$ip"
googleHost: "vtm1"
EOF

# Wait for the REST API to be available
active=1
while [ $active -ne 0 ]
do
    echo "Waiting for REST API..."
    sleep 10
    curl --insecure -s https://${ip}:9070/ | grep http.auth_required > /dev/null
    active=$?
done
echo -e "REST Active\n"

# Use puppet to upload configuration to the newly deployed vTM (via REST).
echo "Pushing configuration with puppet"
puppet apply config/google-vtm1.pp

