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
"""This file contains a parser for the Stat object of a PFile."""
import pytsk3

from plaso.lib import event
from plaso.lib import parser
from plaso.lib import sleuthkit


class PfileStat(parser.PlasoParser):
  """Parse the PFile Stat object to extract filesystem timestamps.."""

  NAME = 'File Stat'
  PARSER_TYPE = 'FILE'

  DATE_MULTIPLIER = 1000000

  def Parse(self, filehandle):
    """Extract the stat object and parse it."""
    stat = filehandle.Stat()

    if not stat:
      return

    times = []
    for item, _ in stat:
      if item[-4:] == 'time':
        times.append(item)

    flags = stat.attributes.get('flags', None)

    for time in times:
      evt = event.EventObject()
      evt.timestamp = int(self.DATE_MULTIPLIER * getattr(stat, time, 0))
      evt.timestamp += getattr(stat, '%s_nano' % time, 0)

      if not evt.timestamp:
        continue

      evt.timestamp_desc = time

      evt.source_short = 'FILE'
      evt.source_long = u'%s Time' % getattr(stat, 'os_type', 'N/A')

      evt.description_short = filehandle.name
      append = u''
      if flags:
        if int(flags) & int(pytsk3.TSK_FS_META_FLAG_UNALLOC):
          append = u' (unallocated)'
      evt.description_long = u'{0}{1}'.format(
          filehandle.display_name, append)
      evt.offset = 0

      yield evt

