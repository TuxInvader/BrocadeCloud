_configuration_

* Upload the driver to Catalogs -> Extra Files -> Miscellaneous (Selecting the option to mark it as executable)

* Create a Cloud Crendentials configuration which then uses the docker autoscaler. 
  * You need to specify the name of a config file as credential1. 
  * We don't use cred2 or cred3 currently, but the UI will make you enter a value in cred2. May I suggested "sausages"?

* Upload the configuration file to Catalogs -> Extra Files -> Miscellaneous

The config file should look something like the one below:

    apiHost http://172.16.0.1:2375
    HostConfig {}
    env_EXAMPLE_ENV foobar

or

    apiHost https://172.16.0.1:2376
    HostConfig {}
    env_EXAMPLE_ENV foobar
    ca CA_CERT
    keys CLIENT_CERT

Where:

  * apiHost is the docker/swarm API endpoint.
  * HostConfig is passed through as a JSON hash (see the docker api for more info).
  * Anything starting env_ is passed through as environment variables with the 'env_' stripped.
  * When using https, you must provide the names of a CA and Client Certificate which exist in the catalog

Note: I haven't tested this with a swarm (yet), but it should work (tm)

