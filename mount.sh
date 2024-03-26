#!/bin/bash

directory="/myfs"
img="disk.img"

if [ ! -d "$directory" ]; then
    sudo mkdir "$directory"
    chown -R $USER:$USER "$directory"
fi

echo "$PS1" > ~/os/ps1.txt
PS1="(UNIX V6++ FS) \w $ "
python3 ./mount.py "$img" "$directory"
cd "$directory"
