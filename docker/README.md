*configuration*

Upload the driver to Catalogs -> Extra Files -> Miscellaneous (Selecting the option to mark it as executable)

Create a Cloud Crendentials configuration which then uses the docker autoscaler. You need to specify the name of a config file as credential1, which should then be uploaded to extra files -> miscellaneous with the driver. We don't use cred2 or cred3 currently, but the UI will make you enter a value in cred2. May I suggested "sausages"?

The config file should look something like the one below:

apiHost http://172.16.0.1:2375
user root
HostConfig {}
env_ZEUS_EULA accept

Where:

  * apiHost is the docker/swarm API endpoint.
  * HostConfig is passed through as a JSON hash (see the docker api for more info).
  * Anything starting env_ is passed through as environment variables with the 'env_' stripped.

Note: I haven't tested this with a swarm (yet), but it should work (tm)

