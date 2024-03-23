from disk import Disk

disk = Disk("disk.img")
disk.mount()

inode = disk._get_inode('/testfilename123')
print(inode.data.d_size)

disk.unmount()