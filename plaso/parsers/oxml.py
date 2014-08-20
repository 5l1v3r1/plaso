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
"""This file contains a parser for OXML files (i.e. MS Office 2007+)."""

import logging
import re
import struct
import zipfile

from plaso.events import time_events
from plaso.lib import errors
from plaso.lib import eventdata
from plaso.lib import timelib
from xml.etree import ElementTree
from plaso.parsers import interface


__author__ = 'David Nides (david.nides@gmail.com)'


class OpenXMLParserEvent(time_events.TimestampEvent):
  """Process timestamps from MS Office XML Events."""

  DATA_TYPE = 'metadata:openxml'

  def __init__(self, timestamp_string, usage, metadata):
    """Initializes the event object.

    Args:
      timestamp_string: An ISO 8601 representation of a timestamp.
      usage: The description of the usage of the time value.
      metadata: A dict object containing extracted metadata.
    """
    timestamp = timelib.Timestamp.FromTimeString(timestamp_string)
    super(OpenXMLParserEvent, self).__init__(timestamp, usage, self.DATA_TYPE)
    for key, value in metadata.iteritems():
      setattr(self, key, value)


class OpenXMLParser(interface.BaseParser):
  """Parse metadata from OXML files."""

  NAME = 'openxml'

  DATA_TYPE = 'metadata:openxml'

  _METAKEY_TRANSLATE = {
    'creator': 'author',
    'lastModifiedBy': 'last_saved_by',
    'Total_Time': 'total_edit_time',
    'Pages': 'num_pages',
    'Characters_with_spaces': 'num_chars_w_spaces',
    'Paragraphs': 'num_paragraphs',
    'Characters': 'num_chars',
    'Lines': 'num_lines',
    'revision': 'revision_num',
    'Words': 'num_words',
    'Application': 'creating_app',
    'Shared_Doc': 'shared',
  }

  _FILES_REQUIRED = frozenset([
      '[Content_Types].xml', '_rels/.rels', 'docProps/core.xml'])

  def _FixString(self, key):
    """Convert CamelCase to lower_with_underscore."""
    # TODO: Add unicode support.
    fix_key = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', key)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', fix_key).lower()

  def Parse(self, parser_context, file_entry):
    """Extract data from an OXML file.

    Args:
      parser_context: A parser context object (instance of ParserContext).
      file_entry: A file entry object (instance of dfvfs.FileEntry).

    Yields:
      An event object (EventObject) that contains the parsed
      attributes.
    """
    file_object = file_entry.GetFileObject()

    if not zipfile.is_zipfile(file_object):
      raise errors.UnableToParseFile(
          u'[{0:s}] unable to parse file: {1:s} with error: {2:s}'.format(
              self.parser_name, file_entry.name, 'Not a Zip file.'))

    try:
      zip_container = zipfile.ZipFile(file_object, 'r')
    except (zipfile.BadZipfile, struct.error, zipfile.LargeZipFile):
      raise errors.UnableToParseFile(
          u'[{0:s}] unable to parse file: {1:s} with error: {2:s}'.format(
              self.parser_name, file_entry.name, 'Bad Zip file.'))

    zip_name_list = set(zip_container.namelist())

    if not self._FILES_REQUIRED.issubset(zip_name_list):
      raise errors.UnableToParseFile(
          u'[{0:s}] unable to parse file: {1:s} with error: {2:s}'.format(
              self.parser_name, file_entry.name, 'OXML element(s) missing.'))
    metadata = {}
    timestamps = {}

    rels_xml = zip_container.read('_rels/.rels')
    rels_root = ElementTree.fromstring(rels_xml)

    for properties in rels_root.iter():
      if 'properties' in repr(properties.get('Type')):
        try:
          xml = zip_container.read(properties.get('Target'))
          root = ElementTree.fromstring(xml)
        except (OverflowError, IndexError, KeyError, ValueError) as exception:
          logging.warning(
            u'[{0:s}] unable to read property with error: {1:s}.'.format(
                self.parser_name, exception))
          continue

        for element in root.iter():
          if element.text:
            _, _, tag = element.tag.partition('}')
            # Not including the 'lpstr' attribute because it is
            # very verbose.
            if tag == 'lpstr':
              continue

            if tag in ('created', 'modified', 'lastPrinted'):
              timestamps[tag] = element.text
            else:
              tag_name = self._METAKEY_TRANSLATE.get(tag, self._FixString(tag))
              metadata[tag_name] = element.text

    if timestamps.get('created', None):
      yield OpenXMLParserEvent(
          timestamps.get('created'), eventdata.EventTimestamp.CREATION_TIME,
          metadata)

    if timestamps.get('modified', None):
      yield OpenXMLParserEvent(
          timestamps.get('modified'),
          eventdata.EventTimestamp.MODIFICATION_TIME, metadata)

    if timestamps.get('lastPrinted', None):
      yield OpenXMLParserEvent(
          timestamps.get('lastPrinted'), eventdata.EventTimestamp.LAST_PRINTED,
          metadata)
