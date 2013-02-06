#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2012 Google Inc. All Rights Reserved.
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
"""This file contains a unit test for the mactime parser in plaso."""
import os
import pytz
import unittest

from plaso.formatters import mactime
from plaso.lib import eventdata
from plaso.lib import preprocess
from plaso.lib import putils
from plaso.parsers import mactime


class MactimeUnitTest(unittest.TestCase):
  """A unit test for the mactime parser."""

  def setUp(self):
    """Sets up the needed objects used throughout the test."""
    test_file = os.path.join('test_data', 'mactime.body')
    self.input_file = putils.OpenOSFile(test_file)

  def testParsing(self):
    """Test parsing of a mactime file."""
    pre_obj = preprocess.PlasoPreprocess()
    pre_obj.zone = pytz.UTC
    parser = mactime.MactimeParser(pre_obj)

    self.input_file.seek(0)
    events = list(parser.Parse(self.input_file))

    self.assertEquals(len(events), 40)

    # Test this entry:
    # 0|/a_directory/another_file|16|r/rrw-------|151107|5000|22|1337961563|
    # 1337961563|1337961563|0
    test_event1 = events[8]
    test_event2 = events[9]
    test_event3 = events[10]
    test_event4 = events[11]

    self.assertEquals(test_event1.timestamp, 0)
    self.assertEquals(test_event1.timestamp_desc, 'crtime')
    self.assertEquals(test_event1.inode, '16')
    self.assertEquals(test_event2.timestamp, 1337961563000000)
    self.assertEquals(test_event2.timestamp_desc, 'atime')
    self.assertEquals(test_event3.timestamp, 1337961563000000)
    self.assertEquals(test_event3.timestamp_desc, 'mtime')
    self.assertEquals(test_event4.timestamp, 1337961563000000)
    self.assertEquals(test_event4.timestamp_desc, 'ctime')
    self.assertEquals(test_event4.name, '/a_directory/another_file')
    self.assertEquals(test_event4.mode_as_string, 'r/rrw-------')

    msg, _ = eventdata.EventFormatterManager.GetMessageStrings(test_event1)
    self.assertEquals(msg, u'/a_directory/another_file')



if __name__ == '__main__':
  unittest.main()
