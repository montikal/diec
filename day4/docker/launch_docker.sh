#!/usr/bin/env bash
docker run -it --privileged \
    -v $HOME/diec:/code \
    mont43/rpi-buster-tf2.0-pyserial:1.1
