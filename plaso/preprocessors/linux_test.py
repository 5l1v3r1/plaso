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
"""Tests for the Linux preprocess plug-ins."""

import unittest

from dfvfs.helpers import file_system_searcher
from dfvfs.path import fake_path_spec

from plaso.lib import event
from plaso.preprocessors import linux
from plaso.preprocessors import test_lib


class LinuxHostnameTest(test_lib.PreprocessPluginTest):
  """Tests for the Linux hostname preprocess plug-in object."""

  _FILE_DATA = (
      'plaso.kiddaland.net\n')

  def setUp(self):
    """Sets up the needed objects used throughout the test."""
    self._fake_file_system = self._BuildSingleFileFakeFileSystem(
        u'/etc/hostname', self._FILE_DATA)

    mount_point = fake_path_spec.FakePathSpec(location=u'/')
    self._searcher = file_system_searcher.FileSystemSearcher(
        self._fake_file_system, mount_point)

  def testGetValue(self):
    """Tests the GetValue function."""
    pre_obj = event.PreprocessObject()
    plugin = linux.LinuxHostname(pre_obj)

    plugin.Run(self._searcher)

    hostname = getattr(pre_obj, 'hostname', None)
    self.assertEquals(hostname, u'plaso.kiddaland.net')


class LinuxUsernamesTest(test_lib.PreprocessPluginTest):
  """Tests for the Linux usernames preprocess plug-in object."""

  _FILE_DATA = (
      'root:x:0:0:root:/root:/bin/bash\n'
      'bin:x:1:1:bin:/bin:/sbin/nologin\n'
      'daemon:x:2:2:daemon:/sbin:/sbin/nologin\n'
      'adm:x:3:4:adm:/var/adm:/sbin/nologin\n'
      'lp:x:4:7:lp:/var/spool/lpd:/sbin/nologin\n'
      'sync:x:5:0:sync:/sbin:/bin/sync\n'
      'shutdown:x:6:0:shutdown:/sbin:/sbin/shutdown\n'
      'halt:x:7:0:halt:/sbin:/sbin/halt\n'
      'mail:x:8:12:mail:/var/spool/mail:/sbin/nologin\n'
      'operator:x:11:0:operator:/root:/sbin/nologin\n'
      'games:x:12:100:games:/usr/games:/sbin/nologin\n'
      'ftp:x:14:50:FTP User:/var/ftp:/sbin/nologin\n'
      'nobody:x:99:99:Nobody:/:/sbin/nologin\n')

  def setUp(self):
    """Sets up the needed objects used throughout the test."""
    self._fake_file_system = self._BuildSingleFileFakeFileSystem(
        u'/etc/passwd', self._FILE_DATA)

    mount_point = fake_path_spec.FakePathSpec(location=u'/')
    self._searcher = file_system_searcher.FileSystemSearcher(
        self._fake_file_system, mount_point)

  def testGetValue(self):
    """Tests the GetValue function."""
    pre_obj = event.PreprocessObject()
    plugin = linux.LinuxUsernames(pre_obj)

    plugin.Run(self._searcher)

    users = getattr(pre_obj, 'users', None)
    self.assertEquals(len(users), 13)

    self.assertEquals(users[11].get('uid', None), u'14')
    self.assertEquals(users[11].get('gid', None), u'50')
    self.assertEquals(users[11].get('name', None), u'ftp')
    self.assertEquals(users[11].get('path', None), u'/var/ftp')
    self.assertEquals(users[11].get('shell', None), u'/sbin/nologin')


if __name__ == '__main__':
  unittest.main()
