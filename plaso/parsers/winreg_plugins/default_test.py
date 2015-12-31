#!/usr/bin/python
# -*- coding: utf-8 -*-
#
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
"""This file contains a test for MRU registry parsing in Plaso."""

import unittest

# pylint: disable-msg=unused-import
from plaso.formatters import winreg as winreg_formatter
from plaso.lib import eventdata
from plaso.parsers.winreg_plugins import default
from plaso.winreg import test_lib


class TestDefaultRegistry(unittest.TestCase):
  """The unit test for default registry key parsing."""

  def setUp(self):
    """Sets up the needed objects used throughout the test."""
    values = []
    values.append(test_lib.TestRegValue('MRUList', 'acb'.encode('utf_16_le'),
                                        1, 123))
    values.append(test_lib.TestRegValue(
        'a', 'Some random text here'.encode('utf_16_le'), 1, 1892))
    values.append(test_lib.TestRegValue(
        'b', 'c:/evil.exe'.encode('utf_16_le'), 3, 612))
    values.append(test_lib.TestRegValue(
        'c', 'C:/looks_legit.exe'.encode('utf_16_le'), 1, 1001))

    self.regkey = test_lib.TestRegKey(
        '\\Microsoft\\Some Windows\\InterestingApp\\MRU', 1346145829002031,
        values, 1456)

  def testDefault(self):
    """Run a simple test against a mocked MRU list."""
    plugin = default.DefaultPlugin()
    generator = plugin.Process(self.regkey)
    self.assertTrue(generator)
    entries = list(generator)

    expected_line = (
        u'[\\Microsoft\\Some Windows\\InterestingApp\\MRU] '
        u'MRUList: [REG_SZ] acb '
        u'a: [REG_SZ] Some random text here '
        u'b: [REG_BINARY] '
        u'c: [REG_SZ] C:/looks_legit.exe')

    self.assertEquals(len(entries), 1)
    self.assertEquals(entries[0].timestamp, 1346145829002031)
    msg, _ = eventdata.EventFormatterManager.GetMessageStrings(entries[0])
    eventdata.EventFormatterManager.GetFormatter(entries[0])
    self.assertEquals(msg, expected_line)


if __name__ == '__main__':
  unittest.main()
