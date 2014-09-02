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
"""Plug-in to collect the Less Frequently Used Keys."""

from plaso.lib import event
from plaso.parsers.winreg_plugins import interface


class BootVerificationPlugin(interface.KeyPlugin):
  """Plug-in to collect the Boot Verification Key."""

  NAME = 'winreg_boot_verify'

  REG_TYPE = 'SYSTEM'
  REG_KEYS = [u'\\{current_control_set}\\Control\\BootVerificationProgram']

  URLS = ['http://technet.microsoft.com/en-us/library/cc782537(v=ws.10).aspx']

  def GetEntries(self, unused_parser_context, key=None, **unused_kwargs):
    """Gather the BootVerification key values and return one event for all.

    This key is rare, so its presence is suspect.

    Args:
      parser_context: A parser context object (instance of ParserContext).
      key: The extracted registry key.

    Yields:
      Extracted event objects from the boot verify key.
    """
    text_dict = {}
    for value in key.GetValues():
      text_dict[value.name] = value.data
    yield event.WinRegistryEvent(
        key.path, text_dict, timestamp=key.last_written_timestamp)


class BootExecutePlugin(interface.KeyPlugin):
  """Plug-in to collect the BootExecute Value from the Session Manager key."""

  NAME = 'winreg_boot_execute'

  REG_TYPE = 'SYSTEM'
  REG_KEYS = [u'\\{current_control_set}\\Control\\Session Manager']

  URLS = ['http://technet.microsoft.com/en-us/library/cc963230.aspx']

  def GetEntries(self, unused_parser_context, key=None, **unused_kwargs):
    """Gather the BootExecute Value, compare to default, return event.

    The rest of the values in the Session Manager key are in a separate event.

    Args:
      parser_context: A parser context object (instance of ParserContext).
      key: The extracted registry key.

    Yields:
      Extracted event objects from the boot verify key.
    """
    text_dict = {}

    for value in key.GetValues():
      if value.name == 'BootExecute':
        # MSDN: claims that the data type of this value is REG_BINARY
        # although REG_MULTI_SZ is known to be used as well.
        if value.DataIsString():
          value_string = value.data
        elif value.DataIsMultiString():
          value_string = u''.join(value.data)
        elif value.DataIsBinaryData():
          value_string = value.data
        else:
          value_string = (
             u'unsupported value data type: {0:s}.').format(
             value.data_type_string)

        boot_dict = {'BootExecute': value_string}

        yield event.WinRegistryEvent(
            key.path, boot_dict,
            timestamp=key.last_written_timestamp)

      else:
        text_dict[value.name] = value.data

    yield event.WinRegistryEvent(
        key.path, text_dict, timestamp=key.last_written_timestamp)
