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
"""Parser for Windows EventLog (EVT) files."""

import logging

import pyevt

from plaso.events import time_events
from plaso.lib import errors
from plaso.lib import eventdata
from plaso.parsers import interface
from plaso.parsers import manager


class WinEvtRecordEvent(time_events.PosixTimeEvent):
  """Convenience class for a Windows EventLog (EVT) record event."""

  DATA_TYPE = 'windows:evt:record'

  def __init__(
      self, timestamp, timestamp_description, evt_record, recovered=False):
    """Initializes the event.

    Args:
      timestamp: The POSIX timestamp value.
      timestamp_description: A description string for the timestamp value.
      evt_record: The EVT record (pyevt.record).
      recovered: Boolean value to indicate the record was recovered, False
                 by default.
    """
    super(WinEvtRecordEvent, self).__init__(timestamp, timestamp_description)

    self.recovered = recovered
    self.offset = evt_record.offset
    try:
      self.record_number = evt_record.identifier
    except OverflowError as exception:
      logging.warning(
          u'Unable to assign the record identifier with error: {0:s}.'.format(
              exception))
    try:
      self.event_identifier = evt_record.event_identifier
    except OverflowError as exception:
      logging.warning(
          u'Unable to assign the event identifier with error: {0:s}.'.format(
              exception))

    self.event_type = evt_record.event_type
    self.event_category = evt_record.event_category
    self.source_name = evt_record.source_name
    # Computer name is the value stored in the event record and does not
    # necessarily corresponds with the actual hostname.
    self.computer_name = evt_record.computer_name
    self.user_sid = evt_record.user_security_identifier

    self.strings = list(evt_record.strings)


class WinEvtParser(interface.BaseParser):
  """Parses Windows EventLog (EVT) files."""

  NAME = 'winevt'
  DESCRIPTION = u'Parser for Windows EventLog (EVT) files.'

  def _ParseRecord(
      self, parser_context, evt_record, file_entry=None, parser_chain=None,
      recovered=False):
    """Extract data from a Windows EventLog (EVT) record.

    Args:
      parser_context: A parser context object (instance of ParserContext).
      evt_record: An event record (pyevt.record).
      file_entry: Optional file entry object (instance of dfvfs.FileEntry).
                  The default is None.
      parser_chain: Optional string containing the parsing chain up to this
                    point. The default is None.
      recovered: Boolean value to indicate the record was recovered, False
                 by default.
    """
    try:
      creation_time = evt_record.get_creation_time_as_integer()
    except OverflowError as exception:
      logging.warning(
          u'Unable to read the timestamp from record with error: {0:s}'.format(
              exception))
      creation_time = 0

    if creation_time:
      event_object = WinEvtRecordEvent(
          creation_time, eventdata.EventTimestamp.CREATION_TIME,
          evt_record, recovered)
      parser_context.ProduceEvent(
          event_object, parser_chain=parser_chain, file_entry=file_entry)

    try:
      written_time = evt_record.get_written_time_as_integer()
    except OverflowError as exception:
      logging.warning(
          u'Unable to read the timestamp from record with error: {0:s}'.format(
              exception))
      written_time = 0

    if written_time:
      event_object = WinEvtRecordEvent(
          written_time, eventdata.EventTimestamp.WRITTEN_TIME,
          evt_record, recovered)
      parser_context.ProduceEvent(
          event_object, parser_chain=parser_chain, file_entry=file_entry)

  def Parse(self, parser_context, file_entry, parser_chain=None):
    """Extract data from a Windows EventLog (EVT) file.

    Args:
      parser_context: A parser context object (instance of ParserContext).
      file_entry: A file entry object (instance of dfvfs.FileEntry).
      parser_chain: Optional string containing the parsing chain up to this
                    point. The default is None.

    Raises:
      UnableToParseFile: when the file cannot be parsed.
    """
    parser_chain = self._BuildParserChain(parser_chain)

    file_object = file_entry.GetFileObject()
    evt_file = pyevt.file()
    evt_file.set_ascii_codepage(parser_context.codepage)

    try:
      evt_file.open_file_object(file_object)
    except IOError as exception:
      evt_file.close()
      file_object.close()
      raise errors.UnableToParseFile(
          u'[{0:s}] unable to parse file {1:s} with error: {2:s}'.format(
              self.NAME, file_entry.name, exception))

    for record_index in range(0, evt_file.number_of_records):
      try:
        evt_record = evt_file.get_record(record_index)
        self._ParseRecord(
            parser_context, evt_record, file_entry=file_entry,
            parser_chain=parser_chain)
      except IOError as exception:
        logging.warning((
            u'[{0:s}] unable to parse event record: {1:d} in file: {2:s} '
            u'with error: {3:s}').format(
                self.NAME, record_index, file_entry.name, exception))

    for record_index in range(0, evt_file.number_of_recovered_records):
      try:
        evt_record = evt_file.get_recovered_record(record_index)
        self._ParseRecord(
            parser_context, evt_record, file_entry=file_entry,
            parser_chain=parser_chain, recovered=True)
      except IOError as exception:
        logging.info((
            u'[{0:s}] unable to parse recovered event record: {1:d} in file: '
            u'{2:s} with error: {3:s}').format(
                self.NAME, record_index, file_entry.name, exception))

    evt_file.close()
    file_object.close()


manager.ParsersManager.RegisterParser(WinEvtParser)
