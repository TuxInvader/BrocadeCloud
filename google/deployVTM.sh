#!/bin/bash

name=vtmtest

gcloud compute instances create $name \
  --image https://www.googleapis.com/compute/v1/projects/brocade-public-1063/global/images/vtm-103-stm-dev-64 \
  --machine-type n1-standard-1 \
  --metadata-from-file startup-script=startup-script.sh \
  --scopes default=https://www.googleapis.com/auth/compute \
  --tags tcp-9090-server,http-server,https-server,ssh-server


