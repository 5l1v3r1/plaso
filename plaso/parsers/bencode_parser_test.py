#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright 2013 The Plaso Project Authors.
# Please see the AUTHORS file for details on individual authors.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Parser Test for BitTorrent client activity files."""

import os
import unittest

# pylint: disable-msg=unused-import
from plaso.formatters import bencode_parser as bencode_formatter
from plaso.lib import eventdata
from plaso.lib import preprocess
from plaso.parsers import bencode_parser
from plaso.parsers import test_lib

import pytz


class BencodeTest(test_lib.ParserTestCase):
  """The unit test for Bencode data plugins."""

  def setUp(self):
    """Sets up the needed objects used throughout the test."""
    self.pre_obj = preprocess.PlasoPreprocess()
    self.pre_obj.zone = pytz.UTC
    self._parser = bencode_parser.BencodeParser(self.pre_obj, None)

  def testTransmissionPlugin(self):
    """Read Transmission activity files and make few tests."""
    test_file = os.path.join('test_data', 'bencode_transmission')
    events = self._ParseFile(self._parser, test_file)
    event_container = self._GetEventContainer(events)

    self.assertEqual(len(event_container.events), 3)

    event_object = event_container.events[0]

    destination_expected = u'/Users/brian/Downloads'
    self.assertEqual(event_object.destination, destination_expected)

    self.assertEqual(event_object.seedtime, 4)

    description_expected = eventdata.EventTimestamp.ADDED_TIME
    self.assertEqual(event_object.timestamp_desc, description_expected)

    # 2013-10-17T21:57:16+00:00
    added_on_date_expected = 1383924680000000
    self.assertEqual(event_object.timestamp, added_on_date_expected)

    # Test on second event of first torrent.
    event_object = event_container.events[1]
    self.assertEqual(event_object.destination, destination_expected)
    self.assertEqual(event_object.seedtime, 4)

    description_expected = eventdata.EventTimestamp.FILE_DOWNLOADED
    self.assertEqual(event_object.timestamp_desc, description_expected)

    # 2013-10-18T00:10:22+00:00
    completed_date_expected = 1383935064000000
    self.assertEqual(event_object.timestamp, completed_date_expected)

  def testUTorrentPlugin(self):
    """Parse a uTorrent resume.dat file and make a few tests."""
    test_file = os.path.join('test_data', 'bencode_utorrent')
    events = self._ParseFile(self._parser, test_file)
    event_container = self._GetEventContainer(events)

    self.assertEqual(len(event_container.events), 4)

    caption_expected = u'plaso test'
    path_expected = u'e:\\torrent\\files\\plaso test'

    # First test on when the torrent was added to the client.
    event_object = event_container.events[3]

    self.assertEqual(event_object.caption, caption_expected)

    self.assertEqual(event_object.path, path_expected)

    self.assertEqual(event_object.seedtime, 511)

    description_expected = eventdata.EventTimestamp.ADDED_TIME
    self.assertEqual(event_object.timestamp_desc, description_expected)

    # 2013-08-03T14:52:12+00:00
    added_on_date_expected = 1375541532000000
    self.assertEqual(event_object.timestamp, added_on_date_expected)

    # Second test on when the torrent file was completely downloaded.
    event_object = event_container.events[2]

    self.assertEqual(event_object.caption, caption_expected)
    self.assertEqual(event_object.path, path_expected)
    self.assertEqual(event_object.seedtime, 511)

    description_expected = eventdata.EventTimestamp.FILE_DOWNLOADED
    self.assertEqual(event_object.timestamp_desc, description_expected)

    # 2013-08-03T18:11:35+00:00
    completed_date_expected = 1375553495000000
    self.assertEqual(event_object.timestamp, completed_date_expected)

    # Third test on when the torrent was first modified.
    event_object = event_container.events[0]

    self.assertEqual(event_object.caption, caption_expected)
    self.assertEqual(event_object.path, path_expected)
    self.assertEqual(event_object.seedtime, 511)

    description_expected = eventdata.EventTimestamp.MODIFICATION_TIME
    self.assertEqual(event_object.timestamp_desc, description_expected)

    # 2013-08-03T18:11:34+00:00
    completed_date_expected = 1375553494000000
    self.assertEqual(event_object.timestamp, completed_date_expected)

    # Fourth test on when the torrent was again modified.
    event_object = event_container.events[1]

    self.assertEqual(event_object.caption, caption_expected)
    self.assertEqual(event_object.path, path_expected)
    self.assertEqual(event_object.seedtime, 511)

    description_expected = eventdata.EventTimestamp.MODIFICATION_TIME
    self.assertEqual(event_object.timestamp_desc, description_expected)

    # 2013-08-03T16:27:59+00:00
    completed_date_expected = 1375547279000000
    self.assertEqual(event_object.timestamp, completed_date_expected)


if __name__ == '__main__':
  unittest.main()
