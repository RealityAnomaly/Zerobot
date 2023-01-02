FROM nvidia/cuda:11.7.0-runtime-ubuntu22.04
RUN apt-get update && apt-get -y install git python3 python3-pip python3-venv
RUN ulimit -p unlimited
ENTRYPOINT bash
