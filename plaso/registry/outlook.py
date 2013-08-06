#!/usr/bin/python
# -*- coding: utf-8 -*-
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
"""This file contains a parser for MS Outlook for Plaso."""
# TODO: Needs test, create NTUSER.DAT test file with Outlook data or
# use winreg testlib.

from plaso.lib import event
from plaso.lib import win_registry_interface


__author__ = 'David Nides (david.nides@gmail.com)'


class Outlook(win_registry_interface.KeyPlugin):
  """Base class for all Data File locations plugins."""

  __abstract = True

  DESCRIPTION = 'Outlook'

  def GetEntries(self):
    """Collect Values under Outlook and return event for each one."""
    value_count = 0
    for value in self._key.GetValues():
      # Ignore the default value.
      if not value.name:
        continue

      # Ignore any value that is empty or that does not contain an integer.
      if not value.data or not value.DataIsInteger():
        continue

      # TODO: change this 32-bit integer into something meaningful, for now
      # the value name is the most interesting part.
      text_dict = {}
      text_dict[value.name] = '0x{0:08x}'.format(value.data)

      if value_count == 0:
        timestamp = self._key.last_written_timestamp
      else:
        timestamp = 0

      yield event.WinRegistryEvent(
          self._key.path, text_dict, timestamp=timestamp,
          source_append=': {0:s}'.format(self.DESCRIPTION))

      value_count += 1


# TODO: Address different MS Office versions.
class MSOutlook2010Search(Outlook):
  """Gathers MS Outlook 2010 Data File locations from the User hive."""

  REG_KEY = '\\Software\\Microsoft\\Office\\14.0\\Outlook\\Search'
  REG_TYPE = 'NTUSER'
  DESCRIPTION = 'PST Paths'


class MSOutlook2010Catalog(Outlook):
  """Gathers MS Outlook 2010 Data File locations from the User hive."""

  REG_KEY = (
    '\\Software\\Microsoft\\Office\\14.0\\Outlook\\Search\\Catalog')
  REG_TYPE = 'NTUSER'
  DESCRIPTION = 'PST Paths'


class MSOutlook2003Catalog(Outlook):
  """Gathers MS Outlook 2003 Data File locations from the User hive."""

  REG_KEY = '\\Software\\Microsoft\\Office\\12.0\\Outlook\\Catalog'
  REG_TYPE = 'NTUSER'
  DESCRIPTION = 'PST Paths'
