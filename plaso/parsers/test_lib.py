#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright 2013 The Plaso Project Authors.
# Please see the AUTHORS file for details on individual authors.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
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
"""Parser related functions and classes for testing."""

import os
import unittest

from plaso.formatters import manager as formatters_manager
from dfvfs.lib import definitions
from dfvfs.path import factory as path_spec_factory
from dfvfs.resolver import resolver as path_spec_resolver

from plaso.artifacts import knowledge_base
from plaso.lib import event
from plaso.parsers import context


class ParserTestCase(unittest.TestCase):
  """The unit test case for a parser."""

  _TEST_DATA_PATH = os.path.join(os.getcwd(), 'test_data')

  # Show full diff results, part of TestCase so does not follow our naming
  # conventions.
  maxDiff = None

  def _GetEventObjects(self, event_generator):
    """Retrieves the event objects from the event_generator.

    This function will extract event objects from a generator.

    Args:
      event_generator: the event generator as returned by the parser.

    Returns:
      A list of event objects (instances of EventObject).
    """
    event_objects = []

    for event_object in event_generator:
      self.assertIsInstance(event_object, event.EventObject)
      event_objects.append(event_object)

    return event_objects

  def _GetTestFilePath(self, path_segments):
    """Retrieves the path of a test file relative to the test data directory.

    Args:
      path_segments: the path segments inside the test data directory.

    Returns:
      A path of the test file.
    """
    # Note that we need to pass the individual path segments to os.path.join
    # and not a list.
    return os.path.join(self._TEST_DATA_PATH, *path_segments)

  def _ParseFile(self, parser_object, path, knowledge_base_values=None):
    """Parses a file using the parser object.

    Args:
      parser_object: the parser object.
      path: the path of the file to parse.
      knowledge_base_values: optional dict containing the knowledge base
                             values. The default is None.

    Returns:
      A generator of event objects as returned by the parser.
    """
    path_spec = path_spec_factory.Factory.NewPathSpec(
        definitions.TYPE_INDICATOR_OS, location=path)
    return self._ParseFileByPathSpec(
        parser_object, path_spec, knowledge_base_values=knowledge_base_values)

  def _ParseFileByPathSpec(
      self, parser_object, path_spec, knowledge_base_values=None):
    """Parses a file using the parser object.

    Args:
      parser_object: the parser object.
      path_spec: the path specification of the file to parse.
      knowledge_base_values: optional dict containing the knowledge base
                             values. The default is None.

    Returns:
      A generator of event objects as returned by the parser.
    """
    knowledge_base_object = knowledge_base.KnowledgeBase()
    if knowledge_base_values:
      for identifier, value in knowledge_base_values.iteritems():
        knowledge_base_object.SetValue(identifier, value)

    parser_context = context.ParserContext(knowledge_base_object)
    file_entry = path_spec_resolver.Resolver.OpenFileEntry(path_spec)
    event_generator = parser_object.Parse(parser_context, file_entry)
    self.assertNotEquals(event_generator, None)

    return event_generator

  def _TestGetMessageStrings(
      self, event_object, expected_message, expected_message_short):
    """Tests the formatting of the message strings.

       This function invokes the GetMessageStrings function of the event
       formatter on the event object and compares the resulting messages
       strings with those expected.

    Args:
      event_object: the event object (instance of EventObject).
      expected_message: the expected message string.
      expected_message_short: the expected short message string.
    """
    manager_object = formatters_manager.EventFormatterManager
    message, message_short = manager_object.GetMessageStrings(event_object)
    self.assertEquals(message, expected_message)
    self.assertEquals(message_short, expected_message_short)

  def _TestGetSourceStrings(
      self, event_object, expected_source, expected_source_short):
    """Tests the formatting of the source strings.

       This function invokes the GetSourceStrings function of the event
       formatter on the event object and compares the resulting source
       strings with those expected.

    Args:
      event_object: the event object (instance of EventObject).
      expected_source: the expected source string.
      expected_source_short: the expected short source string.
    """
    manager_object = formatters_manager.EventFormatterManager
    # TODO: change this to return the long variant first so it is consistent
    # with GetMessageStrings.
    source_short, source = manager_object.GetSourceStrings(event_object)
    self.assertEquals(source, expected_source)
    self.assertEquals(source_short, expected_source_short)
