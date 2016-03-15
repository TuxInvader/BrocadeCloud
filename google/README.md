###Google Autoscaling Driver

##Version 1.1 - 20160315

* New function "getvtmimgs" can retrieve the list of vTM images published by Brocade
* New function "createvtm" can be used to deploy a vTM into GCE. 

* Changes

 - authclient now outputs a JSON blob ready to be pasted into your OAUTH2 credential
   file.

 - Auto-scaled nodes have no compute API access by default
 - Auto-scaled nodes default disk size is 10Gb
 
## Example Scripts

A Cloud Bursting example is included in the examples folder



