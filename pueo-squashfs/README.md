# pueo-squashfs

NOTE: This has moved from pueo-utils to the SURF PetaLinux project
because it's just too awkward to keep it up to date in both locations
and I can't figure out how to do git fetchy stuff from Yocto or
whatever.

https://github.com/barawn/petalinux-surfv6-pueo/

## Operation details

This is the controlling script which handles the PUEO boot process.
It is run at boot and persists around - restarting it relaunches
the PUEO boot script and any of the PUEO daemons. Stopping it
unmounts /usr/local entirely.

## /usr/local

/usr/local on PUEO is an overlay filesystem made up of 2 lower
directories. The first is built from python.sqfs and shouldn't
change much, and the second is made from pueo.sqfs and likely will.
python.sqfs is absurdly bigger, which is why it's split like this.

No changes you make to it will persist across reboots. If you 
want to save your changes, run the build_squashfs script to create
a new squashfs image called pueo.sqfs and copy it into the qspifs.

If you want to change things in /usr/local easily, you can
move /usr/local/boot.sh to /usr/local/boot.sh.tmp and restart
pueo-squashfs, which will prevent the boot process from running and
you can make changes to /usr/local freely. Then move it back
to boot.sh and restart it again, and it will launch.

If you want to reset /usr/local to the qspifs state:
1. stop pueo-squashfs
2. either ``rm -rf /tmp/pueo`` or ``rm -rf
/tmp/pueo/pueo_sqfs_working/*``

Deleting /tmp/pueo will cause it to be reread from qspifs, so it's
a little slower.

## Details

pueo-squashfs does

1. look for /tmp/pueo. If it doesn't exist, create it and temporary
subdirs.
2. look for /tmp/pueo/pueo.sqfs and /tmp/pueo/python.sqfs
  1. If either doesn't exist, mount the qspifs read-only at /mnt.
  2. Look for /mnt/pueo.sqfs and /mnt/python.sqfs. If they don't exist, fail entirely.
  3. Uncompress all files in /mnt/bitstreams ending in .gz/.bz2/.zstd to
/lib/firmware and if they're in subdirectories, link the subdirectory
name to the file (slot number).
  4. Unmount qspifs.
3. Mount /tmp/pueo/pueo.sqfs at /tmp/pueo/pueo_sqfs_mnt.
4. Mount /tmp/pueo/python.sqfs at /tmp/pueo/python_sqfs_mnt.
5. Mount /usr/local as an overlay of /tmp/pueo/pueo_sqfs_mnt, 
/tmp/pueo/python_sqfs_mnt and /tmp/pueo/pueo_sqfs_working.
6. Look in /usr/local for a file named ``boot.sh``
7. If it is found, run it and wait for SIGTERM.
8. Otherwise, sleep forever waiting for SIGTERM.
9. When SIGTERM is received, unmount /usr/local.

