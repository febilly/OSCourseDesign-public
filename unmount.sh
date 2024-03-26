#!/bin/bash

directory="/myfs"

cd ~/os

PS1=$(cat ~/os/ps1.txt)
fusermount -u "$directory"
