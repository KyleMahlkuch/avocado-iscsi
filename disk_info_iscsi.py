#!/usr/bin/env python

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: 2017 IBM
# Author: Pridhiviraj Paidipeddi <ppaidipe@linux.vnet.ibm.com>

"""
Disk Info tests various storage block device list tools, and also it creates
filesystems on test disk and mount it on OS boot disk where the test code
available. Then it verifies all the tools with certain parameters like disk
name, Size, UUID, mount points and IO Sector sizes
"""

import platform
import os
from avocado import Test
from avocado import main
from avocado.utils import process
from avocado.utils import genio
from avocado.utils import distro
from avocado.utils import multipath
from avocado.utils.partition import Partition
from avocado.utils.software_manager import SoftwareManager
from avocado.utils.process import CmdError
from avocado.utils.partition import PartitionError


class DiskInfo(Test):

    """
    DiskInfo test for different storage block device tools
    """

    def setUp(self):
        """
        Verifies if we have list of packages installed on OS
        and also skips the test if user gives the current OS boot disk as
        disk input it may erase the data
        :param disk: test disk where the disk operations can be done
        :param fs: type of filesystem to create
        :param dir: path of the directory to mount the disk device
        """
        smm = SoftwareManager()
        pkg = ""
        if 'ppc' not in platform.processor():
            self.cancel("Processor is not ppc64")
        self.disk = self.params.get('disk', default=None)
        self.dirs = self.params.get('dir', default=self.workdir)
        self.fstype = self.params.get('fs', default='ext4')
        self.log.info("disk: %s, dir: %s, fstype: %s",
                      self.disk, self.dirs, self.fstype)
        if not self.disk:
            self.cancel("No disk input, please update yaml and re-run")
        cmd = "df --output=source"
        if self.disk in process.system_output(cmd, ignore_status=True) \
                .decode("utf-8"):
            self.cancel("Given disk is os boot disk,"
                        "it will be harmful to run this test")
        pkg_list = ["lshw"]
        self.distro = distro.detect().name
        if self.distro == 'Ubuntu':
            pkg_list.append("hwinfo")
        if self.fstype == 'ext4':
            pkg_list.append('e2fsprogs')
        if self.fstype == 'xfs':
            pkg_list.append('xfsprogs')
        if self.fstype == 'btrfs':
            ver = int(distro.detect().version)
            rel = int(distro.detect().release)
            if distro.detect().name == 'rhel':
                if (ver == 7 and rel >= 4) or ver > 7:
                    self.cancel("btrfs is not supported with \
                                RHEL 7.4 onwards")
            if self.distro == 'Ubuntu':
                pkg_list.append("btrfs-tools")
        for pkg in pkg_list:
            if pkg and not smm.check_installed(pkg) and not smm.install(pkg):
                self.cancel("Package %s is missing and could not be installed"
                            % pkg)
        self.disk_nodes = []
        self.disk_base = os.path.basename(self.disk)
        if multipath.is_path_a_multipath(self.disk_base):
            self.mpath = True
            self.disk_abs = self.disk_base
            all_wwids = multipath.get_multipath_wwids()
            for wwid in all_wwids:
                paths = multipath.get_paths(wwid)
                for path in paths:
                    if path == self.disk_abs:
                        #wwid of mpath our disk is on
                        mwwid=wwid
            self.disk_nodes = multipath.get_paths(mwwid)
        else:
            self.mpath = False
            self.disk_abs = self.disk_base
            self.disk_nodes.append(self.disk_base)

    def run_command(self, cmd):
        """
        Run command and fail the test if any command fails
        """
        try:
            process.run(cmd, shell=True, sudo=True)
        except CmdError as details:
            self.fail("Command %s failed %s" % (cmd, details))

    def test_commands(self):
        """
        Test block device tools to list different disk devices
        """
        cmd_list = ["lsblk -l", "fdisk -l", "sfdisk -l", "parted -l",
                    "df -h", "blkid", "lshw -c disk", "grub2-probe /boot"]
        if self.distro == 'Ubuntu':
            cmd_list.append("hwinfo --block --short")
        for cmd in cmd_list:
            self.run_command(cmd)

    def test(self):
        """
        Test disk devices with different operations of creating filesystem and
        mount it on a directory and verify it with certain parameters name,
        size, UUID and IO sizes etc
        """
        msg = []

        #get byid name
        self.disk_byid = os.path.basename(process.system_output("ls /dev/disk/by-id \
            -l| grep -i %s" % self.disk_abs, ignore_status=True, shell=True, \
            sudo=True).decode("utf-8").split("->")[1])
        self.log.info("byid name: %s", self.disk_byid)
        if process.system("ls /dev/disk/by-id -l| grep -i %s" % self.disk_byid,
                          ignore_status=True, shell=True, sudo=True) != 0:
            msg.append("Given disk %s is not in /dev/disk/by-id" % self.disk_abs)
        for disk_node in self.disk_nodes:
            if process.system("ls /dev/disk/by-path -l| grep -i %s" % disk_node,
                              ignore_status=True, shell=True, sudo=True) != 0:
                msg.append("Given disk %s is not in /dev/disk/by-path" % disk_node)

        # Verify disk listed in all tools
        if self.mpath:
            cmd_list = ["fdisk -l ", "lsblk "]
        else:
            cmd_list = ["fdisk -l ", "parted -l", "lsblk ",
                        "lshw -c disk "]
        if self.distro == 'Ubuntu':
            cmd_list.append("hwinfo --short --block")
        for cmd in cmd_list:
            cmd = cmd + " | grep -i %s" % self.disk_base
            if process.system(cmd, ignore_status=True,
                              shell=True, sudo=True) != 0:
                msg.append("Given disk %s is not present in %s" % (self.disk_base, cmd))
        if self.mpath:
            for disk_node in self.disk_nodes:
                if process.system("lshw -c disk | grep -i %s" % disk_node,
                                  ignore_status=True, shell=True, sudo=True) != 0:
                    msg.append("Given disk %s is not in lshw -c disk" % disk_node)

        # Get the size and UUID of the disk
        cmd = "lsblk -l %s --output SIZE -b |sed -n 2p" % self.disk
        output = process.system_output(cmd, ignore_status=True,
                                       shell=True, sudo=True).decode("utf-8")
        if not output:
            self.cancel("No information available in lsblk")
        self.size_b = (output.strip("\n"))[0]
        self.log.info("Disk: %s Size: %s", self.disk, self.size_b)

        # Get the physical/logical and minimal/optimal sector sizes
        pbs_sysfs = "/sys/block/%s/queue/physical_block_size" % self.disk_byid
        pbs = genio.read_file(pbs_sysfs).rstrip("\n")
        lbs_sysfs = "/sys/block/%s/queue/logical_block_size" % self.disk_byid
        lbs = genio.read_file(lbs_sysfs).rstrip("\n")
        mis_sysfs = "/sys/block/%s/queue/minimum_io_size" % self.disk_byid
        mis = genio.read_file(mis_sysfs).rstrip("\n")
        ois_sysfs = "/sys/block/%s/queue/optimal_io_size" % self.disk_byid
        ois = genio.read_file(ois_sysfs).rstrip("\n")
        self.log.info("pbs: %s, lbs: %s, mis: %s, ois: %s", pbs, lbs, mis, ois)

        # Verify sector sizes
        sector_string = "Sector size (logical/physical): %s " \
                        "bytes / %s bytes" % (lbs, pbs)
        output = process.system_output("fdisk -l %s" % self.disk,
                                       ignore_status=True, shell=True,
                                       sudo=True).decode("utf-8")
        if sector_string not in output:
            msg.append("Mismatch in sector sizes of lbs,pbs in "
                       "fdisk o/p w.r.t sysfs paths")
        io_size_string = "I/O size (minimum/optimal): %s " \
                         "bytes / %s bytes" % (mis, mis)
        if io_size_string not in output:
            msg.append("Mismatch in IO sizes of mis and ois"
                       " in fdisk o/p w.r.t sysfs paths")

        # Verify disk size in other tools
        cmd = "fdisk -l %s | grep -i %s" % (self.disk, self.disk)
        if self.size_b not in process.system_output(cmd,
                                                    ignore_status=True,
                                                    shell=True,
                                                    sudo=True).decode("utf-8"):
            msg.append("Size of disk %s mismatch in fdisk o/p" % self.disk)
        cmd = "sfdisk -l %s | grep -i %s" % (self.disk, self.disk)
        if self.size_b not in process.system_output(cmd,
                                                    ignore_status=True,
                                                    shell=True,
                                                    sudo=True).decode("utf-8"):
            msg.append("Size of disk %s mismatch in sfdisk o/p" % self.disk)

if __name__ == "__main__":
    main()
