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
"""Tests for the Skype main.db history database plugin."""

import os
import unittest

# pylint: disable-msg=unused-import
from plaso.formatters import skype as skype_formatter
from plaso.lib import preprocess
from plaso.parsers.sqlite_plugins import interface
from plaso.parsers.sqlite_plugins import skype
from plaso.parsers.sqlite_plugins import test_lib
from plaso.pvfs import utils

import pytz


class SkypePluginTest(test_lib.SQLitePluginTestCase):
  """Tests for the Skype main.db history database plugin."""

  def setUp(self):
    """Sets up the needed objects used throughout the test."""
    pre_obj = preprocess.PlasoPreprocess()
    pre_obj.zone = pytz.UTC

    self._plugin = skype.SkypePlugin(pre_obj)

  def testProcess(self):
    """Tests the Process function on a Skype History database file.

      The History file contains 24 events:
          4 call events
          4 transfers file events
          1 sms events
         15 chat events

      Events used:
        id = 16 -> SMS
        id = 22 -> Call
        id = 18 -> File
        id =  1 -> Chat
        id = 14 -> ChatRoom
    """
    test_file = os.path.join(self.TEST_DATA_PATH, 'skype_main.db')
    event_generator = self._ParseDatabaseFileWithPlugin(self._plugin, test_file)
    event_objects = self._GetEventObjects(event_generator)

    calls = 0
    files = 0
    sms = 0
    chats = 0
    for event in event_objects:
      if event.data_type == 'skype:event:call':
        calls = calls + 1
      if event.data_type == 'skype:event:transferfile':
        files = files + 1
      if event.data_type == 'skype:event:sms':
        sms = sms + 1
      if event.data_type == 'skype:event:chat':
        chats = chats + 1

    self.assertEquals(len(event_objects), 24)
    self.assertEquals(files, 4)
    self.assertEquals(sms, 1)
    self.assertEquals(chats, 15)
    self.assertEquals(calls, 3)

    # TODO: Split this up into separate functions for testing each type of
    # event, eg: testSMS, etc.
    sms_event_object = event_objects[16]
    call_event_object = event_objects[22]
    event_file = event_objects[18]
    chat_event_object = event_objects[1]
    chat_room_event_object = event_objects[14]

    # date -u -d"Jul 01, 2013 22:14:22" +"%s.%N"
    timestamp = 1372716862 * 1000000
    self.assertEquals(sms_event_object.timestamp, timestamp)
    text_sms = (u'If you want I can copy '
                u'some documents for you, '
                u'if you can pay it... ;)')
    self.assertEquals(sms_event_object.text, text_sms)
    number = u'+34123456789'
    self.assertEquals(sms_event_object.number, number)

    # date -u -d"Oct 24, 2013 21:49:35" +"%s.%N"
    timestamp = 1382651375 * 1000000
    self.assertEquals(event_file.timestamp, timestamp)
    action_type = u'GETSOLICITUDE'
    self.assertEquals(event_file.action_type, action_type)
    source = u'gen.beringer <Gen Beringer>'
    self.assertEquals(event_file.source, source)
    destination = u'european.bbq.competitor <European BBQ>'
    self.assertEquals(event_file.destination, destination)
    transferred_filename = u'secret-project.pdf'
    self.assertEquals(event_file.transferred_filename, transferred_filename)
    filepath = u'/Users/gberinger/Desktop/secret-project.pdf'
    self.assertEquals(event_file.transferred_filepath, filepath)
    self.assertEquals(event_file.transferred_filesize, 69986)

    # date -u -d"Jul 30, 2013 21:27:11" +"%s.%N"
    timestamp = 1375219631 * 1000000
    self.assertEquals(chat_event_object.timestamp, timestamp)
    title = u'European Competitor | need to know if you got it..'
    self.assertEquals(chat_event_object.title, title)
    expected_msg = u'need to know if you got it this time.'
    self.assertEquals(chat_event_object.text, expected_msg)
    from_account = u'Gen Beringer <gen.beringer>'
    self.assertEquals(chat_event_object.from_account, from_account)
    self.assertEquals(chat_event_object.to_account, u'european.bbq.competitor')

    # date -u -d"Oct 27, 2013 15:29:19" +"%s.%N"
    timestamp = 1382887759 * 1000000
    self.assertEquals(chat_room_event_object.timestamp, timestamp)
    title = u'European Competitor, Echo123'
    self.assertEquals(chat_room_event_object.title, title)
    expected_msg = u'He is our new employee'
    self.assertEquals(chat_room_event_object.text, expected_msg)
    from_account = u'European Competitor <european.bbq.competitor>'
    self.assertEquals(chat_room_event_object.from_account, from_account)
    to_account = u'gen.beringer, echo123'
    self.assertEquals(chat_room_event_object.to_account, to_account)

    # date -u -d"Jul 01, 2013 22:12:17" +"%s.%N"
    timestamp = 1372716737 * 1000000
    self.assertEquals(call_event_object.timestamp, timestamp)
    self.assertEquals(call_event_object.dst_call, u'european.bbq.competitor')
    self.assertEquals(call_event_object.src_call, u'gen.beringer')
    self.assertEquals(call_event_object.user_start_call, False)
    self.assertEquals(call_event_object.video_conference, False)


if __name__ == '__main__':
  unittest.main()
