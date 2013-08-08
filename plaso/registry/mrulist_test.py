#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2012 The Plaso Project Authors.
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
"""This file contains the tests for the MRUList Registry plugins."""

import unittest

from plaso.formatters import winreg   # pylint: disable-msg=W0611
from plaso.lib import eventdata
from plaso.registry import mrulist
from plaso.winreg import test_lib


class TestMRUListRegistry(unittest.TestCase):
  """The unit test for MRUList registry parsing."""

  def setUp(self):
    """Sets up the needed objects used throughout the test."""
    values = []
    values.append(test_lib.TestRegValue(
        'MRUList', 'acb'.encode('utf_16_le'),
        test_lib.TestRegValue.REG_SZ, offset=123))
    values.append(test_lib.TestRegValue(
        'a', 'Some random text here'.encode('utf_16_le'),
        test_lib.TestRegValue.REG_SZ, offset=1892))
    values.append(test_lib.TestRegValue(
        'b', 'c:/evil.exe'.encode('utf_16_le'),
        test_lib.TestRegValue.REG_BINARY, offset=612))
    values.append(test_lib.TestRegValue(
        'c', 'C:/looks_legit.exe'.encode('utf_16_le'),
        test_lib.TestRegValue.REG_SZ, offset=1001))

    self.regkey = test_lib.TestRegKey(
        '\\Microsoft\\Some Windows\\InterestingApp\\MRU', 1346145829002031,
        values, 1456)

  def testMRUListPlugin(self):
    """Run a simple test against a mocked key with values."""
    plugin = mrulist.MRUListPlugin(None, None, None)
    generator = plugin.Process(self.regkey)
    self.assertTrue(generator)
    entries = list(generator)

    expected_line1 = (
        u'[\\Microsoft\\Some Windows\\InterestingApp\\MRU] '
        u'MRUList Entry 1: Some random text here')
    expected_line2 = (
        u'[\\Microsoft\\Some Windows\\InterestingApp\\MRU] '
        u'MRUList Entry 2: C:/looks_legit.exe')
    expected_line3 = (
        u'[\\Microsoft\\Some Windows\\InterestingApp\\MRU] '
        u'MRUList Entry 3: REGALERT: Unsupported MRU value: b data type.')

    self.assertEquals(len(entries), 3)
    self.assertEquals(entries[0].timestamp, 1346145829002031)
    self.assertEquals(entries[1].timestamp, 0)
    self.assertEquals(entries[2].timestamp, 0)

    msg1, _ = eventdata.EventFormatterManager.GetMessageStrings(entries[0])
    msg2, _ = eventdata.EventFormatterManager.GetMessageStrings(entries[1])
    msg3, _ = eventdata.EventFormatterManager.GetMessageStrings(entries[2])

    self.assertEquals(msg1, expected_line1)
    self.assertEquals(msg2, expected_line2)
    self.assertEquals(msg3, expected_line3)


if __name__ == '__main__':
  unittest.main()
