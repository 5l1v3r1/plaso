#!/usr/bin/python
# -*- coding: utf-8 -*-
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
"""Tests for plaso.output.l2t_csv."""
import StringIO
import unittest

from plaso.lib import event
from plaso.lib import eventdata
from plaso.output import l2t_csv


class L2tTestEvent(event.EventObject):
  DATA_TYPE = 'test:l2t_csv'

  def __init__(self):
    super(L2tTestEvent, self).__init__()
    self.timestamp = 1340821021000000
    self.timestamp_desc = eventdata.EventTimestamp.WRITTEN_TIME
    self.hostname = 'ubuntu'
    self.filename = 'log/syslog.1'
    self.display_name = 'log/syslog.1'
    self.text = (
        u'Reporter <CRON> PID: 8442 (pam_unix(cron:session): session\n '
        u'closed for user root)')


class L2tTestEventFormatter(eventdata.EventFormatter):
  DATA_TYPE = 'test:l2t_csv'
  FORMAT_STRING = u'{text}'

  SOURCE_SHORT = 'LOG'
  SOURCE_LONG = 'Syslog'


class L2tCsvTest(unittest.TestCase):
  def setUp(self):
    self.output = StringIO.StringIO()
    self.formatter = l2t_csv.L2tcsv(None, self.output)

  def testStart(self):
    correct_line = (
        'date,time,timezone,MACB,source,sourcetype,type,user,host,short,desc,'
        'version,filename,inode,notes,format,extra\n')

    self.formatter.Start()
    self.assertEquals(self.output.getvalue(), correct_line)

  def testEventBody(self):
    """Test ensures that returned lines returned are fmt CSV as expected."""
    event_object = L2tTestEvent()

    self.formatter.Start()
    header = (
        'date,time,timezone,MACB,source,sourcetype,type,user,host,short,desc,'
        'version,filename,inode,notes,format,extra\n')
    self.assertEquals(self.output.getvalue(), header)
    self.formatter.EventBody(event_object)
    correct = (
        '06/27/2012,18:17:01,UTC,M...,LOG,Syslog,Content Modification Time,-,'
        'ubuntu,Reporter <CRON> PID: 8442 (pam_unix(cron:session): session '
        'closed for user root),Reporter <CRON> PID: 8442 '
        '(pam_unix(cron:session): '
        'session closed for user root),2,log/syslog.1,-,-,-,\n')
    self.assertEquals(self.output.getvalue(), header + correct)

  def testEventBodyNoCommas(self):
    """Test ensures that commas inside fields are replaced by space."""
    event_object = L2tTestEvent()

    self.formatter.EventBody(event_object)
    correct = (
        '06/27/2012,18:17:01,UTC,M...,LOG,Syslog,Content Modification Time,-,'
        'ubuntu,Reporter <CRON> PID: 8442 (pam_unix(cron:session): session '
        'closed for user root),Reporter <CRON> PID: 8442 '
        '(pam_unix(cron:session): session closed for user root),2,log/syslog.1'
        ',-,-,-,\n')
    self.assertEquals(self.output.getvalue(), correct)


if __name__ == '__main__':
  unittest.main()
