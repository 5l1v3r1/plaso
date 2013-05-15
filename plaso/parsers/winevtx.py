#!/usr/bin/python
# -*- coding: utf-8 -*-
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
"""Parser for Windows XML EventLog (EVTX) files."""
import logging

from plaso.lib import errors
from plaso.lib import event
from plaso.lib import eventdata
from plaso.lib import parser

import pyevtx


class WinEvtxRecordEvent(event.FiletimeEvent):
  """Convenience class for a Windows XML EventLog (EVTX) record event."""
  DATA_TYPE = 'windows:evtx:record'

  def __init__(self, evtx_record, recovered=False):
    """Initializes the event container.

    Args:
      evtx_record: The EVTX record (pyevtx.record).
      recovered: Boolean value to indicate the record was recovered, False
                 by default.
    """
    super(WinEvtxRecordEvent, self).__init__(
        evtx_record.get_written_time_as_integer(),
        eventdata.EventTimestamp.WRITTEN_TIME)

    # TODO: refactor to formatter.
    self.source_long = 'WinEvtx'
    # TODO: Change back to EVTX once this has been refactored to formatter.
    self.source_short = 'EVT'

    self.recovered = recovered
    self.offset = evtx_record.offset
    try:
      self.record_number = evtx_record.identifier
    except OverflowError as e:
      logging.warning(u'Unable to assign the record number [%s].', e)

    try:
      self.event_identifier = evtx_record.event_identifier
    except OverflowError as e:
      logging.warning(u'Unable to assign the event identifier [%s].', e)
    self.event_level = evtx_record.event_level
    self.source_name = evtx_record.source_name
    # Computer name is the value stored in the event record and does not
    # necessarily corresponds with the actual hostname.
    self.computer_name = evtx_record.computer_name
    self.user_sid = evtx_record.user_security_identifier

    self.strings = list(evtx_record.strings)

    self.xml_string = evtx_record.xml_string


class WinEvtxParser(parser.PlasoParser):
  """Parses Windows XML EventLog (EVTX) files."""
  NAME = 'WinEvtx'
  PARSER_TYPE = 'EVTX'

  def Parse(self, file_object):
    """Extract data from a Windows XML EventLog (EVTX) file.

    Args:
      file_object: A file-like object to read data from.

    Yields:
      An event object (WinEvtxRecordEvent) that contains the parsed data.
    """
    evtx_file = pyevtx.file()
    evtx_file.set_ascii_codepage(getattr(self._pre_obj, 'codepage', 'cp1252'))

    try:
      evtx_file.open_file_object(file_object)
    except IOError as exception:
      raise errors.UnableToParseFile('[%s] unable to parse file %s: %s' % (
          self.NAME, file_object.name, exception))

    for record_index in range(0, evtx_file.number_of_records):
      try:
        evtx_record = evtx_file.get_record(record_index)
        yield WinEvtxRecordEvent(evtx_record)
      except IOError as exception:
        logging.warning(
            u'[%s] unable to parse event record: %d in file: %s: %s',
            self.NAME, record_index, file_object.name, exception)

    for record_index in range(0, evtx_file.number_of_recovered_records):
      try:
        evtx_record = evtx_file.get_recovered_record(record_index)
        yield WinEvtxRecordEvent(evtx_record, recovered=True)
      except IOError as exception:
        logging.debug(
            u'[%s] unable to parse recovered event record: %d in file: %s: '
            '%s', self.NAME, record_index, file_object.name, exception)
