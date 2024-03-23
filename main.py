from disk import Disk

disk = Disk("disk.img")
disk.mount()

print(disk._get_inode('/dev').data.d_size)

disk.unmount()