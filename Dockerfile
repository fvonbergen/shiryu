FROM docker.io/library/python:3.12-slim

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update &&                                         \
  apt-get upgrade --assume-yes --no-install-recommends &&     \
  apt-get install --assume-yes --no-install-recommends git && \
  apt-get autoremove &&                                       \
  apt-get clean
