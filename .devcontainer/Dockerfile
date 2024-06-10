# See here for image contents: https://github.com/microsoft/vscode-dev-containers/tree/v0.166.1/containers/ubuntu/.devcontainer/base.Dockerfile

# [Choice] Ubuntu version: bionic, focal
ARG VARIANT="focal"
FROM mcr.microsoft.com/vscode/devcontainers/base:0-${VARIANT}

RUN apt-get update && apt-get upgrade --yes \
  && apt-get install curl git-lfs python3-pip gnupg2 --yes \
  && export EDITOR=/usr/bin/vi
