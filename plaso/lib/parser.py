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
"""This file contains a class to provide a parsing framework to plaso.

This class contains a base framework class for parsing fileobjects, and
also some implementations that extend it to provide a more comprehensive
parser.
"""
import abc
import calendar
import csv
import datetime
import logging
import os
import tempfile

from plaso.lib import errors
from plaso.lib import event
from plaso.lib import lexer
from plaso.lib import registry
from plaso.lib import timelib

import pytz
import sqlite3


class PlasoParser(object):
  """A parent class defining a typical log parser.

  This parent class gets inherited from other classes that are parsing
  log files.

  """
  __metaclass__ = registry.MetaclassRegistry
  __abstract = True

  def __init__(self, pre_obj):
    """Parser constructor.

    Args:
      pre_obj: A PlasoPreprocess object that may contain information gathered
      from a preprocessing process.
    """
    self._pre_obj = pre_obj

  @property
  def parser_name(self):
    """Return the name of the parser."""
    return self.__class__.__name__

  @abc.abstractmethod
  def Parse(self, filehandle):
    """Verifies and parses the log file and returns EventObjects.

    This is the main function of the class, the one that actually
    goes through the log file and parses each line of it to
    produce a parsed line and a timestamp.

    It also tries to verify the file structure and see if the class is capable
    of parsing the file passed to the module. It will do so with series of tests
    that should determine if the file is of the correct structure.

    If the class is not capable of parsing the file passed to it an exception
    should be raised, an exception of the type UnableToParseFile that indicates
    the reason why the class does not parse it.

    Args:
      filehandle: A filehandle/file-like-object that is seekable to the file
      needed to be checked.

    Raises:
      NotImplementedError when not implemented.
    """
    raise NotImplementedError

  def Scan(self, filehandle):
    """Scans the file without verifying it, extracting EventObjects from it.

    Unlike the Parse() method it is not required to implement this method.
    This method skips the verification portion that is included in the Parse()
    method and automatically assumes that the file may not be correctly formed,
    potentially corrupted or only contains portion of the format that this
    parser provides support for.

    If the parser has the potential to scan the file and extract potential
    EventObjects from it, then this method should be implemented. It will never
    been called during the normal runtime of the tool, it is only called
    against a single file (for instance unallocated) using a single parser.

    Args:
      filehandle: A filehandle/file-like-object that is seekable to the file
      needed to be checked.

    Raises:
      NotImplementedError when not implemented.
    """
    raise NotImplementedError


class TextParser(PlasoParser, lexer.SelfFeederMixIn):
  """Generic text based parser that uses lexer to assist with parsing.

  This text based parser needs to be extended to provide an accurate
  list of tokens that define the structure of the log file that the
  parser is designed for.
  """
  __abstract = True

  # Define the max number of lines before we determine this is
  # not the correct parser.
  MAX_LINES = 15

  # List of tokens that describe the structure of the log file.
  tokens = [
      lexer.Token('INITIAL', '(.+)\n', 'ParseString', ''),
      ]

  def __init__(self, pre_obj, local_zone=True):
    """Constructor for the TextParser.

    Args:
      pre_obj: A PlasoPreprocess object that may contain information gathered
      from a preprocessing process.
      local_zone: A boolean value that determines if the entries
                  in the log file are stored in the local time
                  zone of the computer that stored it or in a fixed
                  timezone, like UTC.
    """
    lexer.SelfFeederMixIn.__init__(self)
    PlasoParser.__init__(self, pre_obj)
    self.line_ready = False
    self.attributes = {
        'body': '',
        'iyear': 0,
        'imonth': 0,
        'iday': 0,
        'time': '',
        'hostname': '',
        'username': '',
    }
    self.local_zone = local_zone

  def ClearValues(self):
    """Clears all the values inside the attributes dict.

    All values that start with the letter 'i' are considered
    to be an integer, otherwise string value is assumed.
    """
    self.line_ready = False
    for attr in self.attributes:
      if attr[0] == 'i':
        self.attributes[attr] = 0
      else:
        self.attributes[attr] = ''

  __pychecker__ = 'unusednames=kwargs'
  def ParseIncomplete(self, match, **kwargs):
    """Indication that we've got a partial line to match against."""
    self.attributes['body'] += match.group(0)
    self.line_ready = True

  __pychecker__ = 'unusednames=kwargs'
  def ParseMessage(self, **kwargs):
    """Signal that a line is ready to be parsed."""
    self.line_ready = True

  __pychecker__ = 'unusednames=kwargs'
  def SetMonth(self, match, **kwargs):
    """Parses the month.

       This is a callback function for the text parser (lexer) and is
       called by the corresponding lexer state.

    Args:
      match: A regular expression match group that contains the match
             by the lexer.
    """
    self.attributes['imonth'] = int(
        timelib.MONTH_DICT.get(match.group(1).lower(), 1))

  __pychecker__ = 'unusednames=kwargs'
  def SetDay(self, match, **kwargs):
    """Parses the day of the month.

       This is a callback function for the text parser (lexer) and is
       called by the corresponding lexer state.

    Args:
      match: A regular expression match group that contains the match
             by the lexer.
    """
    self.attributes['iday'] = int(match.group(1))

  __pychecker__ = 'unusednames=kwargs'
  def SetTime(self, match, **kwargs):
    """Set the time attribute."""
    self.attributes['time'] = match.group(1)

  __pychecker__ = 'unusednames=kwargs'
  def SetYear(self, match, **kwargs):
    """Parses the year.

       This is a callback function for the text parser (lexer) and is
       called by the corresponding lexer state.

    Args:
      match: A regular expression match group that contains the match
             by the lexer.
    """
    self.attributes['iyear'] = int(match.group(1))

  def Parse(self, filehandle):
    """Try to parse each line in the file."""
    self.fd = filehandle
    filehandle.seek(0)
    error_count = 0
    file_verified = False
    # We need to clear out few values in the Lexer before continuing.
    # There might be some leftovers from previous run.
    self.error = 0
    self.buffer = ''

    while 1:
      _ = self.NextToken()

      if self.state == 'INITIAL':
        self.entry_offset = getattr(self, 'next_entry_offset', 0)
        self.next_entry_offset = self.fd.tell() - len(self.buffer)

      if not file_verified and self.error >= self.MAX_LINES * 2:
        logging.debug('Lexer error count: %d and current state %s', self.error,
                      self.state)
        name = '%s (%s)' % (self.fd.name, self.fd.display_name)
        raise errors.UnableToParseFile(u'File %s not a %s.' % (
            name, self.parser_name))

      if self.line_ready:
        try:
          yield self.ParseLine(self._pre_obj.zone)
          file_verified = True
        except errors.TimestampNotCorrectlyFormed as e:
          error_count += 1
          if file_verified:
            logging.debug('[%s VERIFIED] Error count: %d and ERROR: %d',
                          filehandle.name, error_count, self.error)
            logging.warning(('[%s] Unable to parse timestamp, skipping entry. '
                             'Msg: [%s]'), self.parser_name, e)
          else:
            logging.debug('[%s EVALUATING] Error count: %d and ERROR: %d',
                          filehandle.name, error_count, self.error)
            if error_count >= self.MAX_LINES:
              raise errors.UnableToParseFile(u'File %s not a %s.' % (
                  self.fd.name, self.parser_name))

        finally:
          self.ClearValues()
      if self.Empty():
        break

    if not file_verified:
      raise errors.UnableToParseFile(
          u'File %s not a %s.' % (filehandle.name, self.parser_name))

  __pychecker__ = 'unusednames=kwargs'
  def ParseString(self, match, **kwargs):
    """Return a string with combined values from the lexer.

    Args:
      match: The matching object.

    Returns:
      A string that combines the values that are so far
      saved from the lexer.
    """
    try:
      self.attributes['body'] += match.group(1).strip('\n')
    except IndexError:
      self.attributes['body'] += match.group(0).strip('\n')

  def PrintLine(self):
    """"Return a string with combined values from the lexer."""
    month = int(self.attributes['imonth'])
    day = int(self.attributes['iday'])
    year = int(self.attributes['iyear'])

    # TODO: this is a work in progress. The reason for the try-catch is that
    # the text parser is handed a non-text file and must deal with converting
    # arbitrary binary data.
    try:
      line = u'%04d-%02d-%02d %s [%s] %s => %s' % (
          year, month, day, self.attributes['time'],
          self.attributes['hostname'], self.attributes['reporter'],
          self.attributes['body'])
    except UnicodeError:
      line = 'Unable to print line - due to encoding error.'

    return line

  def ParseLine(self, zone):
    """Return an EventObject extracted from the current line."""
    if not self.attributes['time']:
      raise errors.TimestampNotCorrectlyFormed(
          u'Unable to parse timestamp, time not set.')

    if not self.attributes['iyear']:
      raise errors.TimestampNotCorrectlyFormed(
          u'Unable to parse timestamp, year not set.')

    times = self.attributes['time'].split(':')
    if self.local_zone:
      time_zone = zone
    else:
      time_zone = pytz.UTC

    if len(times) < 3:
      raise errors.TimestampNotCorrectlyFormed(
          u'Unable to parse timestamp, not of the format HH:MM:SS [%s]' % (
              self.PrintLine()))
    try:
      secs = times[2].split('.')
      if len(secs) == 2:
        sec, us = secs
      else:
        sec = times[2]
        us = 0

      timestamp = datetime.datetime(
          int(self.attributes['iyear']), self.attributes['imonth'],
          self.attributes['iday'], int(times[0]), int(times[1]),
          int(sec), int(us), time_zone)

    except ValueError as e:
      raise errors.TimestampNotCorrectlyFormed(
          u'Unable to parse: %s [er: %s]', self.PrintLine(), e)

    epoch = int(calendar.timegm(timestamp.timetuple()) * 1e6)
    epoch += timestamp.microsecond

    return self.CreateEvent(
        epoch, getattr(self, 'entry_offset', 0), self.attributes)

  # TODO: this is a rough initial implementation to get this working.
  def CreateEvent(self, timestamp, offset, attributes):
    """Creates an event.

       This function should be overwritten by text parsers that require
       to generate specific event object type, the default is TextEvent.

    Args:
      timestamp: The timestamp time value. The timestamp contains the
                 number of microseconds since Jan 1, 1970 00:00:00 UTC.
      offset: The offset of the event.
      attributes: A dict that contains the events attributes.

    Returns:
      A text event (TextEvent).
    """
    event_object = event.TextEvent(timestamp, attributes)
    event_object.offset = offset
    return event_object


class TextCSVParser(PlasoParser):
  """An implementation of a simple CSV line-per-entry log files."""

  __abstract = True

  # A list that contains the names of all the fields in the log file.
  COLUMNS = []

  # A CSV file is comma separated, but this can be overwritten to include
  # tab, pipe or other character separation.
  VALUE_SEPARATOR = ','

  # If there is a header before the lines start it can be defined here, and
  # the number of header lines that need to be skipped before the parsing
  # starts.
  NUMBER_OF_HEADER_LINES = 0

  # If there is a special quote character used inside the structured text
  # it can be defined here.
  QUOTE_CHAR = '"'

  # Value that should not appear inside the file, made to test the actual
  # file to see if it confirms to standards.
  MAGIC_TEST_STRING = 'RegnThvotturMeistarans'

  @abc.abstractmethod
  def VerifyRow(self, row):
    """Return a bool indicating whether or not this is the correct parser."""
    pass

  def ParseRow(self, row):
    """Parse a line of the log file and return an extracted EventObject.

    Args:
      row: A dictionary containing all the fields as denoted in the
      COLUMNS class list.

    Returns:
      An EventObject extracted from a single line from the log file.
    """
    event_object = event.EventObject()
    event_object.row_dict = row
    return event_object

  def Parse(self, filehandle):
    """A generator that returns extracted EventObjects from the log file."""
    self.entry_offset = 0
    # If we specifically define a number of lines we should skip do that here.
    for _ in range(0, self.NUMBER_OF_HEADER_LINES):
      line = filehandle.readline()
      self.entry_offset += len(line)

    reader = csv.DictReader(
        filehandle, fieldnames=self.COLUMNS, restkey=self.MAGIC_TEST_STRING,
        restval=self.MAGIC_TEST_STRING, delimiter=self.VALUE_SEPARATOR,
        quotechar=self.QUOTE_CHAR)

    try:
      row = reader.next()
    except csv.Error:
      raise errors.UnableToParseFile(
          u'File %s not a CSV file, unable to parse.' % filehandle.name)

    if len(row) != len(self.COLUMNS):
      raise errors.UnableToParseFile(
          u'File %s not a %s. (wrong nr. of columns %d vs. %d)' % (
              filehandle.name, self.parser_name, len(row), len(self.COLUMNS)))

    for key, value in row.items():
      if key == self.MAGIC_TEST_STRING or value == self.MAGIC_TEST_STRING:
        raise errors.UnableToParseFile(
            u'File %s not a %s (wrong nr. of columns, should be %d' % (
                filehandle.name, self.parser_name, len(row)))

    if not self.VerifyRow(row):
      raise errors.UnableToParseFile('File %s not a %s. (wrong magic)' % (
          filehandle.name, self.parser_name))

    for evt in self._ParseRow(row):
      if evt:
        yield evt

    for row in reader:
      for evt in self._ParseRow(row):
        if evt:
          yield evt

  def _ParseRow(self, row):
    """Parse a line and extract an EventObject from it if possible."""
    for evt in self.ParseRow(row):
      if not evt:
        continue
      evt.offset = self.entry_offset
      yield evt

    self.entry_offset += len(self.VALUE_SEPARATOR.join(row.values())) + 1


class SQLiteParser(PlasoParser):
  """A SQLite assistance parser for Plaso."""

  __abstract = True

  # Queries to be executed.
  # Should be a list of tuples with two entries, SQLCommand and callback
  # function name.
  QUERIES = []

  # List of tables that should be present in the database, for verification.
  REQUIRED_TABLES = ()

  def __init__(self, pre_obj, local_zone=False):
    """Constructor for the SQLite parser."""
    super(SQLiteParser, self).__init__(pre_obj)
    self._local_zone = local_zone

  def Parse(self, filehandle):
    """Return a generator for EventObjects extracted from SQLite db."""

    # TODO: Remove this when the classifier gets implemented
    # and used. As of now, there is no check made against the file
    # to verify it's signature, thus all files are sent here, meaning
    # that this method assumes everything is a SQLite file and starts
    # copying the content of the file into memory, which is not good
    # for very large files.
    magic = 'SQLite format 3'
    data = filehandle.read(len(magic))

    if data != magic:
      filehandle.seek(-len(magic), 1)
      raise errors.UnableToParseFile(
          u'File %s not a %s. (invalid signature)' % (
              filehandle.name, self.parser_name))

    # TODO: Current design copies the entire file into a buffer
    # that is parsed by each SQLite parser. This is not very efficient,
    # especially when many SQLite parsers are ran against a relatively
    # large SQLite database. This temporary file that is created should
    # be usable by all SQLite parsers so the file should only be read
    # once in memory and then deleted when all SQLite parsers have completed.

    # TODO: Change this into a proper implementation using APSW
    # and virtual filesystems when that will be available.
    # Info: http://apidoc.apsw.googlecode.com/hg/vfs.html#vfs and
    # http://apidoc.apsw.googlecode.com/hg/example.html#example-vfs
    # Until then, just copy the file into a tempfile and parse it.
    name = ''
    with tempfile.NamedTemporaryFile(delete=False) as fh:
      name = fh.name
      while data:
        fh.write(data)
        data = filehandle.read(65536)

    with sqlite3.connect(name) as self.db:
      try:
        self.db.row_factory = sqlite3.Row
        cursor = self.db.cursor()
      except sqlite3.DatabaseError as e:
        logging.debug('SQLite error occured: %s', e)

      # Verify the table by reading in all table names and compare it to
      # the list of required tables.
      try:
        sql_results = cursor.execute(
            'SELECT name FROM sqlite_master WHERE type="table"')
      except sqlite3.DatabaseError as e:
        logging.debug('SQLite error occured: %s', e)
        raise errors.UnableToParseFile(
            u'Unable to open the database file: %s', e)
      tables = []
      for row in sql_results:
        tables.append(row[0])

      if not set(tables) >= set(self.REQUIRED_TABLES):
        self._RemoveTempFile(name, filehandle.name)
        raise errors.UnableToParseFile(
            u'File %s not a %s (wrong tables).' % (filehandle.name,
            self.parser_name))

      for query, action in self.QUERIES:
        try:
          call_back = getattr(self, action, self.Default)
          sql_results = cursor.execute(query)
          row = sql_results.fetchone()
          while row:
            evt_gen = call_back(row=row, zone=self._pre_obj.zone)
            if evt_gen:
              for evt in evt_gen:
                if evt.timestamp < 0:
                  # TODO: For now we dependend on the timestamp to be
                  # set, change this soon so the timestamp does not need to
                  # be set.
                  evt.timestamp = 0
                evt.query = query
                if not hasattr(evt, 'offset'):
                  if 'id' in row.keys():
                    evt.offset = row['id']
                  else:
                    evt.offset = 0
                yield evt
            row = sql_results.fetchone()
        except sqlite3.DatabaseError as e:
          logging.debug('SQLite error occured: %s', e)

    self._RemoveTempFile(name, filehandle.name)

  def _RemoveTempFile(self, name, orig_name):
    """Delete the temporary created db file from the system."""
    try:
      os.remove(name)
    except (OSError, IOError) as e:
      logging.warning(
          u'Unable to remove temporary file: %s [derived from %s] due to: %s',
          name, orig_name, e)

  def Default(self, **kwarg):
    """Default callback method for SQLite events, does nothing."""
    __pychecker__ = 'unusednames=self'
    logging.debug('Default handler: %s', kwarg)


class BundleParser(PlasoParser):
  """A base class for parsers that need more than a single file to parse."""

  __abstract = True

  # A list of all file patterns to match against. This list will be used by the
  # collector to find all available files to parse.
  PATTERNS = []

  @abc.abstractmethod
  def ParseBundle(self, filehandles):
    """Return a generator of EventObjects from a list of files.

    Args:
      filehandles: A list of open file like objects.

    Yields:
      EventObject for each extracted event.
    """
    pass

  def Parse(self, filebundle):
    """Return a generator for EventObjects extracted from a path bundle."""
    if not isinstance(filebundle, event.EventPathBundle):
      raise errors.UnableToParseFile(u'Not a file bundle.')

    bundle_pattern = getattr(filebundle, 'pattern', None)

    if not bundle_pattern:
      raise errors.UnableToParseFile(u'No bundle pattern defined.')

    if u'|'.join(self.PATTERNS) != bundle_pattern:
      raise errors.UnableToParseFile(u'No bundle pattern defined.')

    filehandles = list(filebundle)

    return self.ParseBundle(filehandles)
