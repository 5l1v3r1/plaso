#!/usr/bin/env python
# Copyright 2012 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for plaso.lib.pfilter."""
import unittest

from plaso.lib import event
from plaso.lib import objectfilter
from plaso.lib import pfile
from plaso.lib import pfilter
from plaso.lib import storage
from plaso.proto import plaso_storage_pb2
from plaso.proto import transmission_pb2

__pychecker__ = 'no-funcdoc'


class PFilterTest(unittest.TestCase):
  """Simple plaso specific tests to the pfilter implementation."""

  def testPlasoEvents(self):
    """Test plaso EventObjects, both Python and Protobuf version.

    These are more plaso specific tests than the more generic
    objectfilter ones. It will create an EventContainer that stores
    some attributes and then an EventObject that is stored inside
    that container. These objects will then be serialzed into an
    EventObject protobuf and all tests run against both the native
    Python object as well as the protobuf.
    """
    container = event.EventContainer()
    container.source_short = 'REG'
    container.source_long = 'Made up Source'

    evt = event.EventObject()
    # 2015-11-18T01:15:43
    evt.timestamp = 1447809343000000
    evt.timestamp_desc = 'Last Written'
    evt.description_short = 'This description is different than the long one.'
    evt.description_long = (
        u'User did a very bad thing, bad, bad thing that awoke Dr. Evil.')
    evt.filename = '/My Documents/goodfella/Documents/Hideout/myfile.txt'
    evt.hostname = 'Agrabah'
    evt.parser = 'Weirdo'
    evt.inode = '1245'
    evt.display_name = u'unknown:%s' % evt.filename

    transfer_proto = transmission_pb2.PathSpec()
    transfer_proto.type = transmission_pb2.PathSpec.OS
    transfer_proto.file_path = pfile.GetUnicodeString(evt.filename)

    evt.pathspec = transfer_proto.SerializeToString()
    container.Append(evt)

    evt_proto_str = storage.PlasoStorage.SerializeEvent(evt)
    evt_proto = plaso_storage_pb2.EventObject()
    evt_proto.ParseFromString(evt_proto_str)

    # Series of tests.
    query = "filename contains 'GoodFella'"
    self.RunPlasoTest(evt, evt_proto, query, True)

    # Double negative matching -> should be the same
    # as a positive one.
    query = "filename not not contains 'GoodFella'"
    parser = pfilter.PlasoParser(query)
    self.assertRaises(
        objectfilter.ParseError,
        parser.Parse)

    # Test date filtering.
    query = "date >= '2015-11-18'"
    self.RunPlasoTest(evt, evt_proto, query, True)

    query = "date < '2015-11-19'"
    self.RunPlasoTest(evt, evt_proto, query, True)

    # 2015-11-18T01:15:43
    query = "date < '2015-11-18T01:15:44.341' and date > '2015-11-18 01:15:42'"
    self.RunPlasoTest(evt, evt_proto, query, True)

    query = "date > '2015-11-19'"
    self.RunPlasoTest(evt, evt_proto, query, False)

    # Perform few attribute tests.
    query = "filename not contains 'sometext'"
    self.RunPlasoTest(evt, evt_proto, query, True)

    query = ("timestamp_desc CONTAINS 'written' AND date > '2015-11-18' AND "
             "date < '2015-11-25 12:56:21' AND (source_sort contains 'LOG' or"
             " source_short CONTAINS 'REG')")
    self.RunPlasoTest(evt, evt_proto, query, True)

    query = "parser is not 'Made'"
    self.RunPlasoTest(evt, evt_proto, query, True)

    query = "parser is not 'Weirdo'"
    self.RunPlasoTest(evt, evt_proto, query, False)

    # Test atttributes stored in the container.
    query = "source_long not contains 'Made'"
    self.RunPlasoTest(evt, evt_proto, query, False)

    query = "source is 'REG'"
    self.RunPlasoTest(evt, evt_proto, query, True)

    query = "source is not 'FILE'"
    self.RunPlasoTest(evt, evt_proto, query, True)

    # Multiple attributes.
    query = ("source_long is 'Made up Source' AND description_long regexp "
             "'bad, bad thing [\sa-zA-Z\.]+ evil'")
    self.RunPlasoTest(evt, evt_proto, query, False)

    query = ("source_long is 'Made up Source' AND description_long iregexp "
             "'bad, bad thing [\sa-zA-Z\.]+ evil'")
    self.RunPlasoTest(evt, evt_proto, query, True)

  def RunPlasoTest(self, obj, obj_proto, query, result):
    """Run a simple test against Plaso event object."""
    parser = pfilter.PlasoParser(query).Parse()
    matcher = parser.Compile(
        pfilter.PlasoAttributeFilterImplementation)

    self.assertEqual(result, matcher.Matches(obj))
    self.assertEqual(result, matcher.Matches(obj_proto))


if __name__ == "__main__":
  unittest.main()
