#!/usr/bin/python
# -*- coding: utf-8 -*-
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
"""This file provides functions for printing out information."""
import sys
from plaso.lib import utils
from plaso.lib import putils
# TODO: Write a GetLibraryVersions that gathers all the backend parsing
# libraries and their version numbers.


def GetPluginInformation():
  """Return a string with a list of all plugin and parser information."""
  return_string_pieces = []

  # Import all plugins and parsers to print out the necessary information.
  # This is not import at top since this is only required if this parameter
  # is set, otherwise these libraries get imported in their respected
  # locations.
  from plaso.lib import engine
  from plaso import filters as _
  from plaso import parsers as _
  from plaso import registry as _
  from plaso import output as _
  from plaso.frontend import presets
  from plaso.lib import filter_interface
  from plaso.lib import output
  from plaso.lib import win_registry_interface

  return_string_pieces.append(
      '{:=^80}'.format(' log2timeline/plaso information. '))

  return_string_pieces.append(utils.FormatHeader('Versions'))
  return_string_pieces.append(
      utils.FormatOutputString('plaso engine', engine.__version__))
  return_string_pieces.append(
      utils.FormatOutputString('python', sys.version))

  return_string_pieces.append(utils.FormatHeader('Parsers'))
  for parser in sorted(putils.FindAllParsers()['all']):
    doc_string, _, _ = parser.__doc__.partition('\n')
    return_string_pieces.append(
        utils.FormatOutputString(parser.parser_name, doc_string))

  return_string_pieces.append(utils.FormatHeader('Parser Lists'))
  for category, parsers in sorted(presets.categories.items()):
    return_string_pieces.append(
        utils.FormatOutputString(category, ', '.join(parsers)))

  return_string_pieces.append(
      utils.FormatHeader('Output Modules'))
  for name, description in sorted(output.ListOutputFormatters()):
    return_string_pieces.append(
        utils.FormatOutputString(name, description))

  return_string_pieces.append(utils.FormatHeader('Registry Plugins'))
  reg_plugins = win_registry_interface.GetRegistryPlugins()
  a_plugin = reg_plugins.GetAllKeyPlugins()[0]

  for plugin, obj in sorted(a_plugin.classes.items()):
    doc_string, _, _ = obj.__doc__.partition('\n')
    return_string_pieces.append(
        utils.FormatOutputString(plugin, doc_string))

  return_string_pieces.append(utils.FormatHeader('Filters'))
  for filter_obj in sorted(filter_interface.ListFilters()):
    doc_string, _, _ = filter_obj.__doc__.partition('\n')
    return_string_pieces.append(
        utils.FormatOutputString(filter_obj.filter_name, doc_string))

  return u'\n'.join(return_string_pieces)
