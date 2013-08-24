# Copyright 2014 Ross Delinger
# Use of this source code is governed by a BSD-style
# License that can be found in the LICENSE file.

from xml.etree import ElementTree


class Volume(object):
    def __init__(self, virvol, pool):
        self.pool = pool
        self.virvol = virvol
        self.name = self.virvol.name()
        self.path = self.virvol.path()
        self.key = self.virvol.key()
        self.xml = ElementTree.fromstring(self.virvol.XMLDesc(0))

    @property
    def format(self):
        return self.xml.find('target').find('format').attrib['type']

    @property
    def capacity(self):
        return self.xml.find('capacity').text

    def wipe(self):
        self.virvol.wipe(0)

    def delete(self):
        self.virvol.delete(0)

    def __repr__(self):
        return 'Volume<{0}>'.format(self.path)
