# Copyright 2014 Ross Delinger
# Use of this source code is governed by a BSD-style
# License that can be found in the LICENSE file.

from xml.etree import ElementTree


class NetworkInterface(object):
    def __init__(self, _type, mac_addr, source, model):
        self.xml_root = None
        self.type = _type
        self.mac = mac_addr
        self.source = source
        self.model = model

    def root(self):
        """
        TODO(rdelinger) rename this as to_xml or something similar
        """"
        self.xml_root = ElementTree.Element('interface')
        self.xml_root.set('type', self.type)
        if self.mac is not None:
            mac = ElementTree.SubElement(self.xml_root, 'mac')
            mac.set('address', self.mac)
        _source = ElementTree.SubElement(self.xml_root, 'source')
        _source.set(self.type, self.source)
        _model = ElementTree.SubElement(self.xml_root, 'model')
        _model.set('type', self.model)
        return self.xml_root
