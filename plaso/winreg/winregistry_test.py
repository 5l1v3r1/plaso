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
"""This file contains the tests for the Windows Registry library."""

import unittest

from plaso.winreg import test_lib
from plaso.winreg import winregistry


class RegistryUnitTest(test_lib.WinRegTestCase):
  """Tests for the Windows Registry library."""

  def testMountFile(self):
    """Tests mounting REGF files in the Registry."""
    registry = winregistry.WinRegistry(
        winregistry.WinRegistry.BACKEND_PYREGF)

    test_file = self._GetTestFilePath(['SOFTWARE'])
    file_entry = self._GetTestFileEntry(test_file)
    winreg_file = registry.OpenFile(file_entry, codepage='cp1252')

    registry.MountFile(winreg_file, u'HKEY_LOCAL_MACHINE\\Software')

    test_file = self._GetTestFilePath(['NTUSER-WIN7.DAT'])
    file_entry = self._GetTestFileEntry(test_file)
    winreg_file = registry.OpenFile(file_entry, codepage='cp1252')

    with self.assertRaises(KeyError):
      registry.MountFile(winreg_file, u'HKEY_LOCAL_MACHINE\\Software')

    registry.MountFile(winreg_file, u'HKEY_CURRENT_USER')


if __name__ == '__main__':
  unittest.main()
