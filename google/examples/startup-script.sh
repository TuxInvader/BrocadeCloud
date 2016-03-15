#!/bin/bash

passwd='th1sI$AS3cre+'
keyfile='/opt/zeus/zxtm/etc/license.key.factory'

# Perform the initial config wizard stuff
echo "System.Management.regenerateUUID" | /opt/zeus/zxtm/bin/zcli
echo 'appliance!licence_agreed   Yes' >> /opt/zeus/zxtm/global.cfg
echo 'appliance!timezone   Europe/London' >> /opt/zeus/zxtm/global.cfg
echo "GlobalSettings.setRESTEnabled 1" | /opt/zeus/zxtm/bin/zcli
echo "Users.changePassword admin $passwd" | /opt/zeus/zxtm/bin/zcli
#/opt/zeus/restart-zeus

# setup the vTM license if we are using the non-developer edition
if [ -f $keyfile ]
then
    serial=$(/opt/zeus/zxtm/bin/zeus.zxtm --decodelicense $keyfile | awk '{if ($1 == "Serial:" )print $2 }')
    cp $keyfile /opt/zeus/zxtm/conf/licensekeys/${serial}
fi

# Cant upload Cloud Drivers via REST (vTM Bug: 17924)
driver='https://raw.githubusercontent.com/TuxInvader/BrocadeCloud/master/google/googledriver.py'
curl -o /opt/zeus/zxtm/conf/extra/googledriver.py $driver
chmod +x /opt/zeus/zxtm/conf/extra/googledriver.py

# Add repositories so we can install packages
cat <<EOF > /etc/apt/sources.list.d/official.list
deb http://archive.ubuntu.com/ubuntu trusty main restricted universe
deb http://archive.ubuntu.com/ubuntu trusty-updates main restricted universe
deb http://security.ubuntu.com/ubuntu/ trusty-security main restricted universe
EOF

# Install some packages
#apt-get update
#apt-get install -y python-googleapi euca2ools

