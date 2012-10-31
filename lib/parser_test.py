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
"""This file contains the unit tests for the parser library in plaso."""
import os
import pytz
import unittest

from plaso.lib import errors
from plaso.lib import lexer
from plaso.lib import parser


class EmtpyObject(object):
  """An empty object."""


class FakeFile(object):
  """Implements a fake file object, with content."""

  LINES = ('first line.', 'second line.', 'third line.')

  def __init__(self):
    self.buffer = ''
    self.name = 'IamFakeFile'
    self.display_name = self.name
    self.index = 0
    self.offset = 0
    self.size = 0
    for line in self.LINES:
      self.size += len(line)

  # We are implementing an interface.
  def readline(self):        # pylint: disable=C6409
    """Provides a "fake" readline function."""
    ret = ''
    if self.index < len(self.LINES):
      ret = self.LINES[self.index]

    self.index += 1
    self.offset += len(ret)
    return ret

  # We are implementing an interface.
  def read(self, read_size):    # pylint: disable=C6409
    if len(self.buffer) > read_size:
      ret = self.buffer[:read_size]
      self.buffer = self.buffer[read_size:]
      self.offset += len(ret)
      return ret

    if self.index < len(self.LINES):
      # Add to buffer.
      self.buffer += self.LINES[self.index]
      self.index += 1
      return self.read(read_size)

    ret = self.buffer
    self.buffer = ''
    self.offset += len(ret)
    return ret

  # We are implementing an interface.
  def seek(self, offset, whence=0):   # pylint: disable=C6409
    if whence == 0:
      self.index = 0
      self.buffer = ''
      self.offset = 0
      _ = self.read(offset)
    elif whence == 1:
      if offset > 0:
        _ = self.read(offset)
      else:
        ofs = self.offset + offset
        self.seek(ofs)
    elif whence == 2:
      ofs = self.size + offset
      if ofs > self.offset:
        _ = self.read(ofs - self.offset)
      else:
        self.seek(0)
        _ = self.read(ofs)
    else:
      raise RuntimeError('Illegal whence value %s' % whence)

  # We are implementing an interface.
  def tell(self):   # pylint: disable=C6409
    return self.offset

  def __iter__(self):
    while 1:
      line = self.readline()
      if not line:
        break
      yield line


class FakeBetterFile(FakeFile):
  """Implements a fake file object, with content."""

  LINES = ('01/01/2011 05:23:15 myuser:myhost- first line.\n',
           '12/24/1991 19:58:06 myuser:myhost- second line.\n',
           '06/01/1945 08:20:00 myuser:myhost- third line.\n')


class FakeTextParser(parser.TextParser):
  """Implement a text parser object that can successfully parse a text file.

  To be able to achieve that one function has to be implemented, the ParseDate
  one.
  """
  NAME = 'FakeTextFile'
  source_long = 'Fake File Parser'

  tokens = [
      lexer.Token('INITIAL',
                  r'^([\d\/]+) ', 'SetDate', 'TIME'),
      lexer.Token('TIME', r'([0-9:\.]+) ', 'SetTime', 'STRING_HOST'),
      lexer.Token('STRING_HOST', r'([^\-]+)- ', 'ParseStringHost', 'STRING'),
      lexer.Token('STRING', '([^\n]+)', 'ParseString', ''),
      lexer.Token('STRING', '\n', 'ParseMessage', 'INITIAL'),
      ]

  def ParseStringHost(self, match, **_):
    user, host = match.group(1).split(':')
    self.attributes['hostname'] = host
    self.attributes['username'] = user

  def SetDate(self, match, **_):
    month, day, year = match.group(1).split('/')
    self.attributes['imonth'] = int(month)
    self.attributes['iyear'] = int(year)
    self.attributes['iday'] = int(day)


class ParserUnitTest(unittest.TestCase):
  """An unit test for the plaso parser library."""

  def setUp(self):
    """Sets up the needed objects used throughout the test."""
    self.base_path = os.path.join('plaso/test_data')
    self._pre_obj = EmtpyObject()
    self._pre_obj.zone = pytz.UTC

  def testParserNotImplemented(self):
    """Test the base class Parse function."""
    self.assertRaises(TypeError, parser.PlasoParser)

  def testTextParserFail(self):
    """Test a text parser that will not match against content."""
    text_parser = FakeTextParser(self._pre_obj)
    fn = FakeFile()

    text_generator = text_parser.Parse(fn)
    self.assertRaises(errors.UnableToParseFile, list, text_generator)

  def testTextParserSuccess(self):
    """Test a text parser that will match against content."""
    text_parser = FakeTextParser(self._pre_obj)
    fn = FakeBetterFile()

    text_generator = text_parser.Parse(fn)

    first_entry = text_generator.next()
    second_entry = text_generator.next()

    self.assertEquals(first_entry.timestamp, 1293859395000000)
    self.assertEquals(first_entry.description_long, 'first line.')
    self.assertEquals(first_entry.hostname, 'myhost')
    self.assertEquals(first_entry.username, 'myuser')

    self.assertEquals(second_entry.timestamp, 693604686000000)
    self.assertEquals(second_entry.description_long, 'second line.')
    self.assertEquals(second_entry.hostname, 'myhost')
    self.assertEquals(second_entry.username, 'myuser')


if __name__ == '__main__':
  unittest.main()
