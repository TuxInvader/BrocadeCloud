#!/bin/bash

passwd='th1sI$AS3cre+'

# Perform the initial config wizard stuff
echo 'appliance!licence_agreed   Yes' >> /opt/zeus/zxtm/global.cfg
echo 'appliance!timezone   Europe/London' >> /opt/zeus/zxtm/global.cfg
echo "System.Management.regenerateUUID" | /opt/zeus/zxtm/bin/zcli
echo "GlobalSettings.setRESTEnabled 1" | /opt/zeus/zxtm/bin/zcli
echo "Users.changePassword admin $passwd" | /opt/zeus/zxtm/bin/zcli
/opt/zeus/restart-zeus

# Add repositories so we can install packages
cat <<EOF > /etc/apt/sources.list.d/official.list
deb http://archive.ubuntu.com/ubuntu trusty main restricted universe
deb http://archive.ubuntu.com/ubuntu trusty-updates main restricted universe
deb http://security.ubuntu.com/ubuntu/ trusty-security main restricted universe
EOF

# Install some packages
#apt-get update
#apt-get install -y python-googleapi euca2ools

