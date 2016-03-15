## Sample/Example scripts for use with Google Compute Engine

#startup-script.sh
A startup script which can be passed to google in order to configure
the vTM at first boot. It accepts the license, sets a password, etc

#cloudBurst.sh
An example script which uses the driver to create a vTM in GCE, it
uses the startup-script.sh to configure the vTM, and then uses
puppet to apply a configuration manifest. See the config dir for a
sample

#config
contains a simple puppet manifest example

#deployVTM.sh
Deploy a vTM using the gcloud SDK

