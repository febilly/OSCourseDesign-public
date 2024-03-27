#!/bin/bash

directory="/myfs"
img="disk.img"

if [ ! -d "$directory" ]; then
    sudo mkdir "$directory"
    chown -R $USER:$USER "$directory"
fi

echo "$PS1" > ~/os/ps1.txt
PS1="\[\033[01;32m\]UNIX V6++ FS\[\033[00m\]: \[\033[01;34m\]\w\[\033[00m\] \$ "
python3 ./mount.py "$img" "$directory" "$@"
cd "$directory"
