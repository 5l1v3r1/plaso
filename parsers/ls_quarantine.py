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
"""This file contains a parser for application usage in plaso."""
from plaso.lib import event
from plaso.lib import parser


class ParseLsQuarantine(parser.SQLiteParser):
  """Parse the LaunchServices.QuarantineEvents databse on Mac OS X.

  File can be found here:
    /Users/<username>/Library/Preferences/com.apple.LaunchServices.\
        QuarantineEvents
  """

  NAME = 'LS Quarantine'

  # Define the needed queries.
  QUERIES = [(('SELECT LSQuarantineTimestamp+978328800 AS Epoch, LSQuarantine'
               'AgentName AS Agent, LSQuarantineOriginURLString AS URL, LSQua'
               'rantineDataURLString AS Data FROM LSQuarantineEvent ORDER BY '
               'Epoch'), 'ParseLSQuarantine')]

  # The required tables.
  REQUIRED_TABLES = ('LSQuarantineEvent',)

  DATE_MULTIPLIER = 1000000

  def ParseLSQuarantine(self, row, **_):
    """Return an EventObject from Parse LS QuarantineEvent record."""
    text_long = u'[{0}] Downloaded: {1} <{2}>'.format(
        row['Agent'], row['URL'], row['Data'])

    text_short = u'{0}'.format(row['URL'])

    date = int(row['Epoch'] * self.DATE_MULTIPLIER)

    evt = event.SQLiteEvent(date, 'File Downloaded', text_long, text_short, 'HIST',
                            u'%s Download Event' % self.NAME)

    yield evt

