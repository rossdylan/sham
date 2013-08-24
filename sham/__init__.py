# Copyright 2014 Ross Delinger
# Use of this source code is governed by a BSD-style
# License that can be found in the LICENSE file.
import libvirt
from libvirt import libvirtError
from xml.etree import ElementTree
from string import ascii_lowercase
from sham.storage.volumes import Volume
from sham.storage.pools import StoragePool
from sham.network.interfaces import NetworkInterface
from sham.machine import VirtualMachine


class RetryableHype(object):
    def __init__(self, uri):
        self.uri = uri
        self.hyp = libvirt.open(uri)

    def retry(self, func):
        def wraps(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except:
                print('Libvirt errored out, retrying')
                self.hyp = libvirt.open(self.uri)
                return getattr(self.hyp, func.__name__)(*args, **kwargs)
        return wraps

    def __getattr__(self, name):
        return self.retry(getattr(self.hyp, name))


class VMManager(object):
    def __init__(self, uri):
        self.hyper = RetryableHype(uri)

    def get_storage_pools(self):
        pools = self.hyper.listAllStoragePools(0)
        return [StoragePool(pool) for pool in pools]

    def memory_free(self):
        """
        Returns in GB
        """
        return self.hyper.getFreeMemory() / 1e9

    def get_vms(self):
        domains = self.hyper.listAllDomains(0)
        return [VirtualMachine(d, self) for d in domains]

    def find_vm(self, name):
        """
        Try and find a VM by name
        :param name: Name of the VM
        :type name: str
        """
        try:
            domain = self.hyper.lookupByName(name)
            VM = VirtualMachine(domain, self)
        except libvirtError:
            VM = None
        return VM

    def fast_clone(self, VM, clone_name, mem=None):
        """
        Create a 'fast' clone of a VM. This means we make
        a snapshot of the disk and copy some of the settings
        and then create a new VM based on the snapshot and settings
        The VM is transient so when it is shutdown it deletes itself
        :param VM: The VM to base this clone on
        :type VM: sham.machine.VirtualMachine

        :param clone_name: The name for this clone
        :type clone_name: str
        """
        disks = VM.get_disks()
        ints = VM.get_interfaces()
        count = 0
        new_disks = []
        for disk in disks:
            pool = disk.pool
            new_disk_name = '{0}-disk{1}'.format(clone_name, count)
            count += 1
            new_disk = pool.create_backed_vol(new_disk_name, disk)
            new_disks.append(new_disk)

        for inter in ints:
            inter.mac = None
            # if the mac is set to None we don't include it in the xml
            # and libvirt will autogen one for us
        return self.create_vm(
            VM.domain_type,
            clone_name,
            VM.num_cpus,
            mem or VM.current_memory,
            mem or VM.max_memory,
            new_disks,
            ints)

    def create_vm(self, domain_type, name, cpus, mem, memmax, disks, nets, memunit='KiB', arch='x86_64'):
        domain = ElementTree.Element('domain')
        domain.set('type', domain_type)

        dname = ElementTree.SubElement(domain, 'name')
        dname.text = name

        memory = ElementTree.SubElement(domain, 'memory')
        memory.set('unit', memunit)
        memory.text = memmax

        curmem = ElementTree.SubElement(domain, 'currentMemory')
        curmem.set('unit', memunit)
        curmem.text = mem

        vcpus = ElementTree.SubElement(domain, 'vpu')
        vcpus.text = cpus

        os = ElementTree.SubElement(domain, 'os')
        os_type = ElementTree.SubElement(os, 'type')
        os_type.set('arch', arch)
        os_type.text = 'hvm'  # TODO(rdelinger) Make this user setable
        os_boot = ElementTree.SubElement(os, 'boot')
        os_boot.set('dev', 'hd')

        devices = ElementTree.SubElement(domain, 'devices')
        devices_emu = ElementTree.SubElement(devices, 'emulator')
        devices_emu.text = '/usr/bin/qemu-system-x86_64'  # TODO(rdelinger) make this use setable

        target_drives = iter(['vd{0}'.format(letter) for letter in ascii_lowercase])
        for disk in disks:
            disk_elem = ElementTree.SubElement(devices, 'disk')
            disk_elem.set('type', 'file')
            disk_elem.set('device', 'disk')

            driver = ElementTree.SubElement(disk_elem, 'driver')
            driver.set('name', 'qemu')  # TODO(rdelinger) auto load this somehow?
            driver.set('type', disk.format)

            source = ElementTree.SubElement(disk_elem, 'source')
            source.set('file', disk.path)

            target = ElementTree.SubElement(disk_elem, 'target')
            target.set('dev', target_drives.next())
            target.set('bus', 'virtio')  # TODO(rdelinger) auto load this

        for net in nets:  # These are network interfaces not libvirt Networks
            devices.append(net.root())

        video = ElementTree.SubElement(devices, 'video')
        vmodel = ElementTree.SubElement(video, 'model')
        vmodel.set('type', 'cirrus')
        vmodel.set('vram', '9216')
        vmodel.set('heads', '1')

        graphics = ElementTree.SubElement(devices, 'graphics')
        graphics.set('type', 'vnc')
        graphics.set('port', '-1')
        graphics.set('autoport', 'yes')

        self.hyper.createXML(ElementTree.tostring(domain), 0)
        return self.find_vm(name)
