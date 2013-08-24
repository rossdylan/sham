# Copyright 2014 Ross Delinger
# Use of this source code is governed by a BSD-style
# License that can be found in the LICENSE file.

from xml.etree import ElementTree
from sham.storage.pools import StoragePool
from sham.storage.volumes import Volume
from sham.network.interfaces import NetworkInterface


class VirtualMachine(object):
    """
    Wrapper around a libvirt Domain
    Provides a set of functions that make it easier to interact with
    domains.
    """
    def __init__(self, domain, vmm):
        self.vmm = vmm
        self.domain = domain
        self.name = domain.name()
        self.xml = ElementTree.fromstring(self.domain.XMLDesc(0))

    @property
    def domain_type(self):
        """
        Return what type of domain this this (kvm/lxc/etc)
        """
        return self.xml.attrib['type']

    @property
    def current_memory(self):
        """
        Return the current memory allocated to this VM
        """
        return self.xml.find('currentMemory').text

    @property
    def max_memory(self):
        """
        Return the maximum memory this VM can have
        """
        return self.xml.find('memory').text

    @property
    def num_cpus(self):
        """
        Return the number of Virtual CPUS allocated to this VM
        """
        return self.xml.find('vcpu').text

    def get_interfaces(self):
        """
        Return a list of sham.network.interfaces.NetworkInterface
        describing all the interfaces this VM has
        """
        interfaces = self.xml.find('devices').iter('interface')
        iobjs = []
        for interface in interfaces:
            _type = interface.attrib['type']
            mac = interface.find('mac').attrib['address']
            source = interface.find('source').attrib[_type]
            model = interface.find('model').attrib['type']
            iobjs.append(NetworkInterface(_type, mac, source, model))
        return iobjs

    def get_disks(self):
        """
        Return a list of all the Disks attached to this VM
        The disks are returned in a sham.storage.volumes.Volume
        object
        """
        disks = [disk for disk in self.xml.iter('disk')]
        disk_objs = []
        for disk in disks:
            source = disk.find('source')
            if source is None:
                continue
            path = source.attrib['file']
            diskobj = self.domain.connect().storageVolLookupByPath(path)
            disk_objs.append(diskobj)
        return [Volume(d, StoragePool(d.storagePoolLookupByVolume())) for d in disk_objs]

    def delete(self):
        """
        Delete this VM, and remove all its disks
        """
        disks = self.get_disks()
        self.domain.undefine()
        for disk in disks:
            disk.wipe()
            disk.delete()

    def start(self):
        """
        Start the current VM
        """
        self.domain.create()

    def shutdown(self, delete=False):
        """
        Shutdown this VM
        :param delete: Should we delete after shutting the VM down?
        :type delete: bool
        """
        disks = self.get_disks()
        self.domain.destroy()
        if delete:
            for disk in disks:
                disk.wipe()
                disk.delete()

    def is_running(self):
        """
        Check if this VM is running
        """
        info = self.domain.info()
        # info[0] is a state (see enum virDomainState)
        if info[0] == 1:
            return True
        return False

    def __repr__(self):
        return "VirtualMachine< {0} >".format(self.name)

    def to_dict(self):
        """
        Return the values contained in this object as a dict
        """
        return {'domain_type': self.domain_type,
                'max_memory': self.max_memory,
                'current_memory': self.current_memory,
                'num_cpus': self.num_cpus,
                'running': self.is_running(),
                'name': self.name,
                }
