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
"""Parser for McAfee Anti-Virus Logs.

McAfee AV uses 4 logs to track when scans were run, when virus databases were
updated, and when files match the virus database."""

import logging

from plaso.lib import event
from plaso.lib import text_parser
from plaso.lib import timelib


class McafeeAVEvent(event.TextEvent):
  """Convenience class for McAfee AV Log events """
  DATA_TYPE = 'av:mcafee:accessprotectionlog'

  def __init__(self, timestamp, attributes):
    """Initializes a McAfee AV Log Event.

    Args:
      timestamp: The timestamp time value. The timestamp contains the
                 number of seconds since Jan 1, 1970 00:00:00 UTC.
      attributes: Dict of elements from the AV log line.
    """
    del attributes['time']
    del attributes['date']
    super(McafeeAVEvent, self).__init__(timestamp, attributes)
    self.full_path = attributes['filename']


class McafeeAccessProtectionParser(text_parser.TextCSVParser):
  """Parses the McAfee AV Access Protection Log."""

  NAME = 'mcafee_protection'

  VALUE_SEPARATOR = '\t'
  # Define the columns of the McAfee AV Access Protection Log.
  COLUMNS = ['date', 'time', 'status', 'username', 'filename',
             'trigger_location', 'rule', 'action']

  def VerifyRow(self, row):
    """Verify that this is a McAfee AV Access Protection Log file."""

    if len(row) != 8:
      return False

    # This file can have the UTF-8 marker at the beginning of the first row.
    # TODO: Find out all the code pages this can have.  Asked McAfee 10/31.
    if row['date'][0:3] == '\xef\xbb\xbf':
      row['date'] = row['date'][3:]

    # Check the date format!
    # If it doesn't pass, then this isn't a McAfee AV Access Protection Log
    try:
      self.GetTimestamp(row['date'], row['time'])
    except (TypeError, ValueError):
      return False

    # Use the presence of these strings as a backup or incase of partial file.
    if (not 'Access Protection' in row['status'] and
        not 'Would be blocked' in row['status']):
      return False

    return True

  def GetTimestamp(self, date, time):
    """Return a 64-bit signed timestamp in microseconds since Epoch.

     The timestamp is made up of two strings, the date and the time, separated
     by a tab. The time is in local time. The month and day can be either 1 or 2
     characters long.  E.g.: 7/30/2013\t10:22:48 AM

     Args:
       date: The string representing the date.
       time: The string representing the time.

     Returns:
       A plaso timestamp value, microseconds since Epoch in UTC.
    """

    if not (date and time):
      logging.warning('Unable to extract timestamp from McAfee AV logline.')
      return

    # TODO: Figure out how McAfee sets Day First and use that here.
    # The in-file time format is '07/30/2013\t10:22:48 AM'.
    timestamp = timelib.Timestamp.FromTimeString(
        u'{0:s} {1:s}'.format(date, time), timezone=self._pre_obj.zone)
    return timestamp

  def ParseRow(self, row):
    """Parse a single row from the McAfee Access Protection Log file."""

    epoch = self.GetTimestamp(row['date'], row['time'])
    yield McafeeAVEvent(epoch, row)
