#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright 2014 The Plaso Project Authors.
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
"""Tests for the file system scanner object."""

import os
import unittest

from dfvfs.lib import definitions

from plaso.collector import scanner


class UserInputException(Exception):
  """Class that defines an user input exception."""


class TestFileSystemScanner(scanner.FileSystemScanner):
  """Test file system scanner that raises UserInputException."""

  def _GetPartionIdentifierFromUser(self, volume_system, volume_identifiers):
    """Asks the user to provide the partitioned volume identifier.

    Args:
      volume_system: The volume system (instance of dfvfs.TSKVolumeSystem).
      volume_identifiers: List of allowed volume identifiers.
    """
    raise UserInputException(u'_GetPartionIdentifierFromUser')

  def _GetVShadowIdentifiersFromUser(self, volume_system, volume_identifiers):
    """Asks the user to provide the VSS volume identifiers.

    Args:
      volume_system: The volume system (instance of dfvfs.VShadowVolumeSystem).
      volume_identifiers: List of allowed volume identifiers.
    """
    self.vss_stores = [1, 2]
    return self.vss_stores


class FileSystemScannerTest(unittest.TestCase):
  """Tests for the file system scanner."""

  _TEST_DATA_PATH = os.path.join(os.getcwd(), 'test_data')

  # Show full diff results, part of TestCase so does not follow our naming
  # conventions.
  maxDiff = None

  def _GetTestFilePath(self, path_segments):
    """Retrieves the path of a test file relative to the test data directory.

    Args:
      path_segments: the path segments inside the test data directory.

    Returns:
      A path of the test file.
    """
    # Note that we need to pass the individual path segments to os.path.join
    # and not a list.
    return os.path.join(self._TEST_DATA_PATH, *path_segments)

  def testScan(self):
    """Tests file systems scanning."""
    test_file = self._GetTestFilePath(['tsk_volume_system.raw'])

    test_scanner = TestFileSystemScanner()
    with self.assertRaises(UserInputException):
      _ = test_scanner.Scan(test_file)

    test_scanner = TestFileSystemScanner()
    test_scanner.SetPartitionOffset(0x0002c000)

    path_spec = test_scanner.Scan(test_file)
    self.assertNotEquals(path_spec, None)
    self.assertEquals(
        path_spec.type_indicator, definitions.TYPE_INDICATOR_TSK)
    self.assertEquals(test_scanner.partition_offset, 180224)

    test_scanner = TestFileSystemScanner()
    test_scanner.SetPartitionOffset(0x00030000)
    with self.assertRaises(UserInputException):
      _ = test_scanner.Scan(test_file)

    test_scanner = TestFileSystemScanner()
    test_scanner.SetPartitionNumber(1)

    path_spec = test_scanner.Scan(test_file)
    self.assertNotEquals(path_spec, None)
    self.assertEquals(
        path_spec.type_indicator, definitions.TYPE_INDICATOR_TSK)
    self.assertEquals(test_scanner.partition_offset, 180224)

    test_scanner = TestFileSystemScanner()
    test_scanner.SetPartitionNumber(7)
    with self.assertRaises(UserInputException):
      _ = test_scanner.Scan(test_file)

    test_file = self._GetTestFilePath(['image.E01'])
    test_scanner = TestFileSystemScanner()

    path_spec = test_scanner.Scan(test_file)
    self.assertNotEquals(path_spec, None)
    self.assertEquals(
        path_spec.type_indicator, definitions.TYPE_INDICATOR_TSK)
    self.assertEquals(test_scanner.partition_offset, 0)

    test_file = self._GetTestFilePath(['image.qcow2'])
    test_scanner = TestFileSystemScanner()

    path_spec = test_scanner.Scan(test_file)
    self.assertNotEquals(path_spec, None)
    self.assertEquals(
        path_spec.type_indicator, definitions.TYPE_INDICATOR_TSK)
    self.assertEquals(test_scanner.partition_offset, 0)

    test_file = self._GetTestFilePath(['vsstest.qcow2'])
    test_scanner = TestFileSystemScanner()

    path_spec = test_scanner.Scan(test_file)
    self.assertNotEquals(path_spec, None)
    self.assertEquals(
        path_spec.type_indicator, definitions.TYPE_INDICATOR_TSK)
    self.assertEquals(test_scanner.partition_offset, 0)
    self.assertEquals(test_scanner.vss_stores, [1, 2])


if __name__ == '__main__':
  unittest.main()
