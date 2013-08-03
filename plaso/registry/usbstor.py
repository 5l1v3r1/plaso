#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2013 The Plaso Project Authors.
# Please see the AUTHORS file for details on individual authors.#
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
"""This file contains the USBStor keys plugin for Plaso."""

import logging
from plaso.lib import event
from plaso.lib import eventdata
from plaso.lib import win_registry_interface

__author__ = 'David Nides (david.nides@gmail.com)'


class USBStor(win_registry_interface.KeyPlugin):
  """Base class for all USBStor keys."""

  REG_KEY = '\\{current_control_set}\\Enum\\USBSTOR'
  REG_TYPE = 'SYSTEM'
  DESCRIPTION = 'USBStor Entries'

  def GetEntries(self):
    """Collect Values under USBStor & return event for each one."""
    for subkey in self._key.GetSubkeys():

      text_dict = {}
      text_dict['subkey_name'] = subkey.name

      # Time last USB device of this class was first inserted.
      reg_evt = event.WinRegistryEvent(
          self._key.path, text_dict, subkey.timestamp,
          eventdata.EventTimestamp.FIRST_CONNECTED)

      reg_evt.source_append = ': {}'.format(self.DESCRIPTION)
      yield reg_evt

      # TODO: Determine if these 4 fields always exist.
      try:
        dtype, vendor, product, rev = subkey.name.split('&')
      except ValueError as exception:
        logging.warning(
            u'Unable to split string: {} - [{}]'.format(
              subkey.name, exception))

      for devicekey in subkey.GetSubkeys():
        text_dict['device_type'] = dtype
        text_dict['vendor'] = vendor
        text_dict['product'] = product
        text_dict['revison'] = rev
        text_dict['serial'] = devicekey.name

        friendly_name = devicekey.GetValue('FriendlyName')
        if friendly_name:
            text_dict['friendly_name'] = friendly_name.data

        # ParentIdPrefix applies to Windows XP Only.
        parent_id_prefix = devicekey.GetValue('ParentIdPrefix')
        if parent_id_prefix:
          text_dict['parent_id_prefix'] = parent_id_prefix.data

        # Win7 - Last Connection.
        # Vista/XP - Time of an insert.
        reg_evt = event.WinRegistryEvent(
            self._key.path, text_dict, devicekey.timestamp,
            eventdata.EventTimestamp.LAST_CONNECTED)

        reg_evt.source_append = ': {}'.format(self.DESCRIPTION)
        yield reg_evt

        # Build list of first Insertion times.
        first_insert = []
        device_parameter = devicekey.GetSubkey('Device Parameters')
        if device_parameter:
          first_insert.append(device_parameter.timestamp)
        log_configuration = devicekey.GetSubkey('LogConf')
        if log_configuration:
          if log_configuration.timestamp not in first_insert:
              first_insert.append(log_configuration.timestamp)
        properties = devicekey.GetSubkey('Properties')
        if properties:
          if properties.timestamp not in first_insert:
              first_insert.append(properties.timestamp)

        # Add first Insertion times.
        for timestamp in first_insert:
          reg_evt = event.WinRegistryEvent(
              self._key.path, text_dict, timestamp,
                  eventdata.EventTimestamp.LAST_CONNECTED)

          reg_evt.source_append = ': {}'.format(self.DESCRIPTION)
          yield reg_evt
