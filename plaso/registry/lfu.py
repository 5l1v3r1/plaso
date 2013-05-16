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
"""Plug-in to collect the Less Frequently Used Keys."""
import logging

from plaso.lib import event
from plaso.lib import win_registry_interface


class BootVerificationPlugin(win_registry_interface.KeyPlugin):
  """Plug-in to collect the Boot Verification Key."""

  REG_KEY = '\\{current_control_set}\\Control\\BootVerificationProgram'
  REG_TYPE = 'SYSTEM'
  URLS = ['http://technet.microsoft.com/en-us/library/cc782537(v=ws.10).aspx']

  def GetEntries(self):
    """Gather the BootVerification key values and return one event for all.
    This key is rare, so its presence is suspect."""
    text_dict = {}
    text_dict['BootVerification'] = u'REGALERT'
    for value in self._key.GetValues():
      text_dict[value.name] = value.GetData()
    event_object = event.WinRegistryEvent(self._key.path, text_dict,
                                          self._key.timestamp)
    yield event_object


class BootExecutePlugin(win_registry_interface.KeyPlugin):
  """Plug-in to collect the BootExecute Value from the Session Manager key."""

  REG_KEY = '\\{current_control_set}\\Control\\Session Manager'
  REG_TYPE = 'SYSTEM'
  URLS = ['http://technet.microsoft.com/en-us/library/cc963230.aspx']

  def GetEntries(self):
    """Gather the BootExecute Value, compare to default, return event. The
    rest of the values in the Session Manager key are in a separate event."""
    text_dict = {}

    for value in self._key.GetValues():
      if value.name == 'BootExecute':
        boot_dict = {}
        boot = value.GetData(unicode)
        if boot != u'autocheck autochk *':
          boot_dict['BootExecute'] = u'REGALERT: {}'.format(boot)
        else:
          boot_dict['BootExecute'] = boot

        event_object = event.WinRegistryEvent(
            self._key.path, boot_dict, self._key.timestamp)
        yield event_object
      else:
        text_dict[value.name] = value.GetData()

    event_object = event.WinRegistryEvent(
        self._key.path, text_dict, self._key.timestamp)
    yield event_object
