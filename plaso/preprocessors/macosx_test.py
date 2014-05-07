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
"""Tests for the Mac OS X preprocess plug-ins."""

import os
import unittest

from dfvfs.helpers import file_system_searcher
from dfvfs.path import fake_path_spec

from plaso.lib import event
from plaso.preprocessors import macosx
from plaso.preprocessors import test_lib


class MacOSXBuildTest(test_lib.PreprocessPluginTest):
  """Tests for the Mac OS X build information preprocess plug-in object."""

  _FILE_DATA = (
      '<?xml version="1.0" encoding="UTF-8"?>\n'
      '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
      '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
      '<plist version="1.0">\n'
      '<dict>\n'
      '\t<key>ProductBuildVersion</key>\n'
      '\t<string>13C64</string>\n'
      '\t<key>ProductCopyright</key>\n'
      '\t<string>1983-2014 Apple Inc.</string>\n'
      '\t<key>ProductName</key>\n'
      '\t<string>Mac OS X</string>\n'
      '\t<key>ProductUserVisibleVersion</key>\n'
      '\t<string>10.9.2</string>\n'
      '\t<key>ProductVersion</key>\n'
      '\t<string>10.9.2</string>\n'
      '</dict>\n'
      '</plist>\n')

  def setUp(self):
    """Sets up the needed objects used throughout the test."""
    self._fake_file_system = self._BuildSingleFileFakeFileSystem(
        u'/System/Library/CoreServices/SystemVersion.plist',
        self._FILE_DATA)

    mount_point = fake_path_spec.FakePathSpec(location=u'/')
    self._searcher = file_system_searcher.FileSystemSearcher(
        self._fake_file_system, mount_point)

  def testGetValue(self):
    """Tests the GetValue function."""
    pre_obj = event.PreprocessObject()
    plugin = macosx.MacOSXBuild(pre_obj)

    plugin.Run(self._searcher)

    build = getattr(pre_obj, 'build', None)
    self.assertEquals(build, u'10.9.2')


class MacOSXHostname(test_lib.PreprocessPluginTest):
  """Tests for the Mac OS X hostname preprocess plug-in object."""

  # Note that is only part of the normal preferences.plist file data.
  _FILE_DATA = (
      '<?xml version="1.0" encoding="UTF-8"?>\n'
      '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
      '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
      '<plist version="1.0">\n'
      '<dict>\n'
      '\t<key>System</key>\n'
      '\t<dict>\n'
      '\t\t<key>Network</key>\n'
      '\t\t<dict>\n'
      '\t\t\t<key>HostNames</key>\n'
      '\t\t\t<dict>\n'
      '\t\t\t\t<key>LocalHostName</key>\n'
      '\t\t\t\t<string>Plaso\'s Mac mini</string>\n'
      '\t\t\t</dict>\n'
      '\t\t</dict>\n'
      '\t\t<key>System</key>\n'
      '\t\t<dict>\n'
      '\t\t\t<key>ComputerName</key>\n'
      '\t\t\t<string>Plaso\'s Mac mini</string>\n'
      '\t\t\t<key>ComputerNameEncoding</key>\n'
      '\t\t\t<integer>0</integer>\n'
      '\t\t</dict>\n'
      '\t</dict>\n'
      '</dict>\n'
      '</plist>\n')

  def setUp(self):
    """Sets up the needed objects used throughout the test."""
    self._fake_file_system = self._BuildSingleFileFakeFileSystem(
        u'/Library/Preferences/SystemConfiguration/preferences.plist',
        self._FILE_DATA)

    mount_point = fake_path_spec.FakePathSpec(location=u'/')
    self._searcher = file_system_searcher.FileSystemSearcher(
        self._fake_file_system, mount_point)

  def testGetValue(self):
    """Tests the GetValue function."""
    pre_obj = event.PreprocessObject()
    plugin = macosx.MacOSXHostname(pre_obj)

    plugin.Run(self._searcher)

    hostname = getattr(pre_obj, 'hostname', None)
    self.assertEquals(hostname, u'Plaso\'s Mac mini')


class MacOSXKeyboard(test_lib.PreprocessPluginTest):
  """Tests for the Mac OS X keyboard layout preprocess plug-in object."""

  def setUp(self):
    """Sets up the needed objects used throughout the test."""
    file_object = open(os.path.join(
        self._TEST_DATA_PATH, u'com.apple.HIToolbox.plist'))
    file_data = file_object.read()
    file_object.close()

    self._fake_file_system = self._BuildSingleFileFakeFileSystem(
        u'/Library/Preferences/com.apple.HIToolbox.plist',
        file_data)

    mount_point = fake_path_spec.FakePathSpec(location=u'/')
    self._searcher = file_system_searcher.FileSystemSearcher(
        self._fake_file_system, mount_point)

  def testGetValue(self):
    """Tests the GetValue function."""
    pre_obj = event.PreprocessObject()
    plugin = macosx.MacOSXKeyboard(pre_obj)

    plugin.Run(self._searcher)

    keyboard_layout = getattr(pre_obj, 'keyboard_layout', None)
    self.assertEquals(keyboard_layout, u'US')


class MacOSXTimezone(test_lib.PreprocessPluginTest):
  """Tests for the Mac OS X timezone preprocess plug-in object."""

  def setUp(self):
    """Sets up the needed objects used throughout the test."""
    self._fake_file_system = self._BuildSingleLinkFakeFileSystem(
        u'/private/etc/localtime', u'/usr/share/zoneinfo/Europe/Amsterdam')

    mount_point = fake_path_spec.FakePathSpec(location=u'/')
    self._searcher = file_system_searcher.FileSystemSearcher(
        self._fake_file_system, mount_point)

  def testGetValue(self):
    """Tests the GetValue function."""
    pre_obj = event.PreprocessObject()
    plugin = macosx.MacOSXTimeZone(pre_obj)

    plugin.Run(self._searcher)

    time_zone_str = getattr(pre_obj, 'time_zone_str', None)
    self.assertEquals(time_zone_str, u'Europe/Amsterdam')


class MacOSXUsersTest(test_lib.PreprocessPluginTest):
  """Tests for the Mac OS X usernames preprocess plug-in object."""

  def setUp(self):
    """Sets up the needed objects used throughout the test."""
    file_object = open(os.path.join(
        self._TEST_DATA_PATH, u'com.apple.HIToolbox.plist'))
    file_data = file_object.read()
    file_object.close()

    self._fake_file_system = self._BuildSingleFileFakeFileSystem(
        u'/private/var/db/dslocal/nodes/Default/users/nobody.plist',
        file_data)

    mount_point = fake_path_spec.FakePathSpec(location=u'/')
    self._searcher = file_system_searcher.FileSystemSearcher(
        self._fake_file_system, mount_point)

  def testGetValue(self):
    """Tests the GetValue function."""
    pre_obj = event.PreprocessObject()
    plugin = macosx.MacOSXUsers(pre_obj)

    plugin.Run(self._searcher)

    users = getattr(pre_obj, 'users', None)
    self.assertEquals(len(users), 1)

    # TODO: fix the parsing of the following values to match the behavior on
    # Mac OS X.

    # The string -2 is converted into the integer -1.
    self.assertEquals(users[0].get('uid', None), -1)
    # 'home' is 0 which represents: /var/empty but we convert it
    # into u'<not set>'.
    self.assertEquals(users[0].get('path', None), u'<not set>')
    # 'name' is 0 which represents: nobody but we convert it into u'<not set>'.
    self.assertEquals(users[0].get('name', None), u'<not set>')
    # 'realname' is 0 which represents: 'Unprivileged User' but we convert it
    # into u'N/A'.
    self.assertEquals(users[0].get('realname', None), u'N/A')


if __name__ == '__main__':
  unittest.main()
