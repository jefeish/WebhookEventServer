#!/bin/bash

set -e

if [ -f '/workspaces/Apple-ACI-AWSInfra/.devcontainer/container.env' ]; then
  echo "Adding container.env to /root/.bashrc"
  echo "" >> /root/.bashrc
  cat /workspaces/Apple-ACI-AWSInfra/.devcontainer/container.env >> /root/.bashrc
else
  echo "container.env not found, ignoring"
fi

pushd ghes-cluster
  pip install -r requirements.txt
popd