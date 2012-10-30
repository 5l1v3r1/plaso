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
"""This file contains the unit tests for the win_registry library in plaso."""
import os
import unittest

from plaso.lib import win_registry


class RegistryUnitTest(unittest.TestCase):
  """An unit test for the plaso win_registry library."""

  def setUp(self):
    """Sets up the needed objects used throughout the test."""
    self.base_path = os.path.join('plaso/test_data')

  def testDumpKeys(self):
    hive = os.path.join(self.base_path, 'NTUSER.DAT')
    fh = open(hive, 'rb')
    reg = win_registry.WinRegistry(fh)
    keys = list(reg)

    # Count the number of registry keys in the hive.
    self.assertEquals(len(keys), 1126)


if __name__ == '__main__':
  unittest.main()
