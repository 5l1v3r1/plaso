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
"""Tests for the SQLite database parser."""

import unittest

from plaso.lib import event
from plaso.parsers import sqlite


class Configuration(object):
  """Config object."""

  def __init__(self):
    """Initializes the configuration object."""
    self.parsers = ''


class SQLiteParserTest(unittest.TestCase):
  """Tests for the SQLite database parser."""

  def setUp(self):
    """Sets up the needed objects used throughout the test."""
    self._pre_obj = event.PreprocessObject()
    self._config = Configuration()

  def testPluginList(self):
    """Test the plugin list returns the right values."""
    # pylint: disable=protected-access
    self._parser = sqlite.SQLiteParser(self._pre_obj, self._config)

    all_plugins = self._parser._plugins
    self.assertGreaterEqual(len(all_plugins), 10)

    all_plugin_names = all_plugins.keys()

    self.assertTrue('skype' in all_plugin_names)
    self.assertTrue('chrome_history' in all_plugin_names)
    self.assertTrue('firefox_history' in all_plugin_names)

    # Change the calculations of the parsers.
    self._config.parsers = 'chrome_history, firefox_history, -skype'
    self._parser = sqlite.SQLiteParser(self._pre_obj, self._config)
    plugins = self._parser._plugins

    self.assertEquals(len(plugins), 2)

    # Test with a different plugin selection.
    self._config.parsers = 'sqlite, -skype'
    self._parser = sqlite.SQLiteParser(self._pre_obj, self._config)
    plugins = self._parser._plugins

    # This should result in all plugins EXCEPT the skype one.
    self.assertEquals(len(plugins), len(all_plugins) - 1)


if __name__ == '__main__':
  unittest.main()
