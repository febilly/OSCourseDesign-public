#!/bin/bash

directory="/Users/$USER/Desktop/myfs"
img="disk.img"

if [ ! -d "$directory" ]; then
    mkdir "$directory"
fi

python3 ./mount.py mount "$img" "$directory" "$@"
