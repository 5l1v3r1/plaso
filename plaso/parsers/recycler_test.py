#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright 2013 The Plaso Project Authors.
# Please see the AUTHORS file for details on individual authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
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
"""Tests for the Windows recycler parsers."""

import unittest

# pylint: disable-msg=unused-import
from plaso.formatters import recycler as recycler_formatter
from plaso.lib import eventdata
from plaso.lib import preprocess
from plaso.parsers import recycler
from plaso.parsers import test_lib


class WinRecycleBinParserTest(test_lib.ParserTestCase):
  """Tests for the Windows Recycle Bin parser."""

  def setUp(self):
    """Sets up the needed objects used throughout the test."""
    pre_obj = preprocess.PlasoPreprocess()
    self._parser = recycler.WinRecycleBinParser(pre_obj)
    # Show full diff results, part of TestCase so does not follow our naming
    # conventions.
    self.maxDiff = None

  def testParse(self):
    """Tests the Parse function."""
    test_file = self._GetTestFilePath(['$II3DF3L.zip'])
    events = self._ParseFile(self._parser, test_file)
    event_objects = self._GetEventObjects(events)

    self.assertEquals(len(event_objects), 1)

    event_object = event_objects[0]

    self.assertEquals(event_object.orig_filename, (
        u'C:\\Users\\nfury\\Documents\\Alloy Research\\StarFury.zip'))

    self.assertEquals(event_object.timestamp, 1331585398633000)
    self.assertEquals(event_object.file_size, 724919)

    expected_msg = (
        u'C:\\Users\\nfury\\Documents\\Alloy Research\\StarFury.zip '
        u'(from drive C?)')
    expected_msg_short = (
        u'Deleted file: C:\\Users\\nfury\\Documents\\Alloy Research\\'
        u'StarFury.zip')

    self._TestGetMessageStrings(event_object, expected_msg, expected_msg_short)


class WinRecyclerInfo2ParserTest(test_lib.ParserTestCase):
  """Tests for the Windows Recycler INFO2 parser."""

  def setUp(self):
    """Sets up the needed objects used throughout the test."""
    pre_obj = preprocess.PlasoPreprocess()
    self._parser = recycler.WinRecycleInfo2Parser(pre_obj)

    # Show full diff results, part of TestCase so does not follow our naming
    # conventions.
    self.maxDiff = None

  def testParse(self):
    """Reads an INFO2 file and run a few tests."""
    test_file = self._GetTestFilePath(['INFO2'])
    events = self._ParseFile(self._parser, test_file)
    event_objects = self._GetEventObjects(events)

    self.assertEquals(len(event_objects), 4)

    event_object = event_objects[0]

    # Date: 2004-08-25T16:18:25.237000+00:00
    self.assertEquals(event_object.timestamp, 1093450705237000)
    self.assertEquals(event_object.timestamp_desc,
                      eventdata.EventTimestamp.DELETED_TIME)

    self.assertEquals(event_object.index, 1)
    self.assertEquals(event_object.orig_filename, (
        u'C:\\Documents and Settings\\Mr. Evil\\Desktop\\lalsetup250.exe'))

    event_object = event_objects[1]

    expected_msg = (
        u'DC2 -> C:\\Documents and Settings\\Mr. Evil\\Desktop'
        u'\\netstumblerinstaller_0_4_0.exe [C:\\Documents and '
        u'Settings\\Mr. Evil\\Desktop\\netstumblerinstaller_0_4_0.exe] '
        u'(from drive C)')
    expected_msg_short = (
        u'Deleted file: C:\\Documents and Settings\\Mr. Evil\\Desktop'
        u'\\netstumblerinstaller...')

    self._TestGetMessageStrings(event_object, expected_msg, expected_msg_short)

    event_object = event_objects[2]

    short, source = eventdata.EventFormatterManager.GetSourceStrings(
        event_object)

    self.assertEquals(source, u'Recycle Bin')
    self.assertEquals(short, u'RECBIN')


if __name__ == '__main__':
  unittest.main()
