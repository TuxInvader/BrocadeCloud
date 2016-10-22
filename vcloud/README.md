#VMWare VCloud Director AutoScaling Driver
============

This is an autoscaler for VMware VCloud Director.  

The AutoScaler will deploy new Virtual Machines from "single machine" vAPP Templates into you running vAPP.

## Configuration

Follow the steps below to set up the AutoScaler with VCD.

### Upload The Driver

Upload the vclouddriver.py file into `Catalogs -> Extra Files -> Miscellaneous` and remember to mark it as executable.

### Upload a VCD-VAPP Configuration

Upload a configuration file for the vAPP you are autoscaling into `Catalogs -> Miscellaneous`. This one does
not neet to be executable. You will need a configuration file for each vAPP you want to AutoScale.  

For Example::  

```
apiHost  https://mycloud.mycompany.net/api
user     mark@brocade
pass     marksPassword
org      brocade
vdc      brocade-emea
vapp     testapp
network  Direct Internet connection
```

You should set the `apiHost, user, and pass` to match the VCD API you will be connecting to. The `org, and vdc`
should match your VCloud Organization, and Virtual Data Center names. The `vapp` is the name of the VApp which
we will be deploying machines into, and the `network` is the name of the network we will deploy on.

### Create Cloud Credentials

Once the driver and configuration files are uploaded, you will be able to create a set of Cloud Credentials under 
`Catalogs -> Cloud Credentials`. You should select the vclouddriver.py as the Cloud API, and you should enter the
name of your configuration file as Credential 1.  

For Example:
```
    Name:          vcd-vapp1
    Cloud API:     vclouddriver.py
    Credential 1:  vcd-vapp1.cfg
    Credential 2:  Unused, but you must enter something
```

## Setting up an AutoScale Pool

Once you have configured the VCD for your vApp, you will need to create the AutoScaling pool. Create a pool under
`Services - Pools`. You don't need to provide any nodes obviously, just give it a name and tick the "use autoscaling"
box.  

You should now be at the AutoScaler settings: `Services -> Pools -> [Pool Name] -> AutoScaling`. Set `autoscale!external`
to "no", and then set `Cloud Credentials` to your new VCD Credentials. The `Image ID` needs to be set to the name of the
vApp Template that you will be cloning VMs from. You need to enter a value in `Machine Type`, but VCD doesn't use it.
Finallye set the `Name Prefix` to something appropriate.  

Review the other settings, and click `update` when ready.

That's it, you're done!

