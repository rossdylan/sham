# Copyright 2014 Ross Delinger
# Use of this source code is governed by a BSD-style
# License that can be found in the LICENSE file.

from xml.etree import ElementTree
from libvirt import libvirtError
from sham.storage.volumes import Volume


class StoragePool(object):
    def __init__(self, virsp):
        self.virsp = virsp

    def get_volumes(self):
        """
        Return a list of all Volumes in this Storage Pool
        """
        vols = [self.find_volume(name) for name in self.virsp.listVolumes()]
        return vols

    def create_backed_vol(self, name, backer, _format='qcow2'):
        """
        TODO(rdelinger) think about changing _format
        This is a pretty specialized function.
        It takes an existing volume, and creates a new volume
        that is backed by the existing volume
        Sadly there is no easy way to do this in libvirt, the
        best way I've found is to just create some xml and use the createXML
        function
        """
        vol_xml = ElementTree.Element('volume')
        vol_name = ElementTree.SubElement(vol_xml, 'name')
        name = '{0}.{1}'.format(name, _format)
        vol_name.text = name

        target = ElementTree.SubElement(vol_xml, 'target')
        target_format = ElementTree.SubElement(target, 'format')
        target_format.set('type', _format)

        vol_cap = ElementTree.SubElement(vol_xml, 'capacity')
        vol_cap.set('unit', 'bytes')  # @TODO(rdelinger) this should be dynamic
        vol_cap.text = backer.capacity

        backing_store = ElementTree.SubElement(vol_xml, 'backingStore')
        bs_path = ElementTree.SubElement(backing_store, 'path')
        bs_path.text = backer.path

        bs_format = ElementTree.SubElement(backing_store, 'format')
        bs_format.set('type', backer.format)

        XMLString = ElementTree.tostring(vol_xml)
        self.virsp.createXML(XMLString, 0)

        return self.find_volume(name)

    def find_volume(self, name):
        """
        Find a storage volume by its name
        :param name: The name of the volume
        :type name: str
        """
        try:
            return Volume(self.virsp.storageVolLookupByName(name), self)
        except libvirtError:
            return None

    def __repr__(self):
        name = self.virsp.name()
        numvols = self.virsp.numOfVolumes()
        return 'StoragePool<Name: {0}, Volumes: {1}>'.format(name, numvols)

