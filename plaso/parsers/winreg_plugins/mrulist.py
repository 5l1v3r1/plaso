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
"""This file contains a MRUList Registry plugin."""

import logging

from plaso.lib import event
from plaso.parsers.winreg_plugins import interface


class MRUListPlugin(interface.ValuePlugin):
  """A Registry plugin for keys that contain a MRUList value."""

  NAME = 'winreg_mrulist'

  REG_TYPE = 'any'
  REG_VALUES = frozenset(['MRUList', 'a'])
  URLS = [u'http://forensicartifacts.com/tag/mru/']

  def GetEntries(self, unused_parser_context, key=None, **unused_kwargs):
    """Extracts event objects from a MRU list.

    Args:
      parser_context: A parser context object (instance of ParserContext).
      key: A Windows Registry key (instance of WinRegKey).

    Yields:
      An event object (instance of EventObject) that contains a MRU list.
    """
    mru_list_value = key.GetValue('MRUList')

    if not mru_list_value:
      text_dict = {}
      logging.error(u'missing MRUList value.')

      yield event.WinRegistryEvent(
          key.path, text_dict, timestamp=key.last_written_timestamp)

    else:
      timestamp = key.last_written_timestamp

      entry_list = []
      text_dict = {}
      for entry_index, mru_value_name in enumerate(mru_list_value.data):
        value = key.GetValue(mru_value_name)
        if value:
          mru_value_string = value.data
        if not value:
          mru_value_string = u''
          logging.error(u'No such MRU value: {0}.'.format(mru_value_name))

        # Ignore any value that is empty.
        elif not value.data:
          logging.error(u'Missing MRU value: {0} data.'.format(mru_value_name))

        # TODO: add support for shell item based MRU value data.
        elif not value.DataIsString():
          mru_value_string = u''
          logging.error(u'Unsupported MRU value: {0} data type.'.format(
              mru_value_name))

        else:
          mru_value_string = value.data

        entry_list.append(mru_value_string)
        text_dict[u'Index: {0:d} [MRU Value {1:s}]'.format(
            entry_index + 1, mru_value_name)] = mru_value_string

      event_object = event.WinRegistryEvent(
          key.path, text_dict, timestamp=timestamp,
          source_append=': MRU List')
      event_object.mru_list = entry_list
      yield event_object
