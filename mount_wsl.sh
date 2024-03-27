#!/bin/bash

directory="/myfs"
img="disk.img"

if [ ! -d "$directory" ]; then
    sudo mkdir "$directory"
    chown -R $USER:$USER "$directory"
fi

python3 ./mount.py "$img" "$directory" "$@"
cd "$directory"
