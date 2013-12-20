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
"""Plist_interface contains basic interface for plist plugins within Plaso.

Plist files are only one example of a type of object that the Plaso tool is
expected to encounter and process.  There can be and are many other parsers
which are designed to process specific data types.

PlistPlugin defines the attributes neccessary for registration, discovery
and operation of plugins for plist files which will be used by PlistParser.
"""

import logging

from plaso.lib import errors
from plaso.lib import plugin
from plaso.lib import registry


class PlistPlugin(plugin.BasePlugin):
  """This is an abstract class from which plugins should be based.

  The following are the attributes and methods expected to be overriden by a
  plugin.

  Attributes:
  PLIST_PATH - string of the filename the plugin is designed to process.
  PLIST_KEY - list of keys holding values that are neccessary for processing.

  Please note, PLIST_KEY is cAse sensitive and for a plugin to match a
  plist file needs to contain at minimum the number of keys needed for
  processing or WrongPlistPlugin is raised.

  For example if a Plist file contains the following keys,
  {'foo': 1, 'bar': 2, 'opt': 3} with 'foo' and 'bar' being keys critical to
  processing define PLIST_KEY as ['foo', 'bar']. If 'opt' is only optionally
  defined it can still be accessed by manually processing self.top_level from
  the plugin.

  Methods:
  GetEntries() - extract and format info from keys and yields event.PlistEvent.

  Quick note regarding the following __metaclass__ = registry.MetaclassRegistry.
  MetaclassRegisty is used to dynamically register plugins so that they are
  discoverable by the Plaso processing engine without additional code
  modifications.

  Plaso's implementation is identical and resides in lib/registry.py.
  """

  __metaclass__ = registry.MetaclassRegistry
  # __abstract prevents the interface itself from being registered as a plugin.
  __abstract = True

  NAME = 'plist'

  # PLIST_PATH is a string for the filename this parser is designed to process.
  # This is expected to be overriden by the processing plugin.
  # Ex. 'com.apple.bluetooth.plist'
  PLIST_PATH = 'any'

  # PLIST_KEYS is a list of keys required by a plugin.
  # This is expected to be overriden by the processing plugin.
  # Ex. frozenset(['DeviceCache', 'PairedDevices'])
  PLIST_KEYS = frozenset(['any'])

  # This is expected to be overriden by the processing plugin.
  # The URLS should contain a list of URL's with additional information about
  # this key or value.
  # Ex. ['http://www.forensicswiki.org/wiki/Property_list_(plist)']
  URLS = []

  # We need access to both the top_level object and the plist name in order to
  # properly evaluate whether this is the corretct plugin or not.
  # pylint: disable-msg=arguments-differ
  def Process(self, plist_name, top_level):
    """Determine if this is the correct plugin; if so proceed with processing.

    Process() checks if the current plist being processed is a match for a
    plugin by comparing the PATH and KEY requirements defined by a plugin.  If
    both match processing continues; else raise WrongPlistPlugin.

    This function also extracts the required keys as defined in self.PLIST_KEYS
    from the plist and stores the result in self.match[key] and calls
    self.GetEntries() which holds the processing logic implemented by the
    plugin.

    Args:
      plist_name: Name of the plist file.
      top_level: Plist in dictionary form.

    Raises:
      WrongPlistPlugin: If this plugin is not able to process the given file.

    Returns:
      A generator of events processed by the plugin.
    """

    self._top_level = top_level

    if plist_name.lower() != self.PLIST_PATH.lower():
      raise errors.WrongPlistPlugin(self.plugin_name, plist_name)

    if not set(top_level.keys()).issuperset(self.PLIST_KEYS):
      raise errors.WrongPlistPlugin(self.plugin_name, plist_name)

    logging.debug(u'Plist Plugin Used: {} for: {}'.format(self.plugin_name,
                                                          plist_name))
    self.match = GetKeys(top_level, self.PLIST_KEYS)
    return self.GetEntries()

  def GetEntries(self):
    """Yields PlistEvents from the values of entries within a plist.

    This is the main method that a plist plugin needs to implement.

    The contents of the plist keys defined in PLIST_KEYS will be made availible
    to the plugin as self.matched{'KEY': 'value'}. The plugin should implement
    logic to parse this into a useful event for incorporation into the Plaso
    timeline.

    For example if you want to note the timestamps of when devices were
    LastInquiryUpdated you would need to examine the bluetooth config file
    called 'com.apple.bluetooth' and need to look at devices under the key
    'DeviceCache'.  To do this the plugin needs to define
    PLIST_PATH = 'com.apple.bluetooth' and PLIST_KEYS =
    frozenset(['DeviceCache']). IMPORTANT: this interface requires exact names
    and is case sensitive. A unit test based on a real world file is expected
    for each plist plugin.

    When a file with this key is encountered during processing self.matched is
    populated and the plugin's GetEntries() is called.  The plugin would have
    self.matched = {'DeviceCache': [{'DE:AD:BE:EF:01': {'LastInquiryUpdate':
    DateTime_Object}, 'DE:AD:BE:EF:01': {'LastInquiryUpdate':
    DateTime_Object}'...}]} and needs to implement logic here to extract
    values, format, and yeild the data as a event.PlistEvent.

    The attributes for a PlistEvent should include the following:
      root = Root key this event was extracted from. E.g. DeviceCache/
      key = Key the value resided in.  E.g. 'DE:AD:BE:EF:01'
      time = Date this artifact was created in microseconds(usec) from epoch.
      desc = Short description.  E.g. 'Device LastInquiryUpdated'

    See plist/bt.py for the implemented example plugin.

    Yields:
      event.PlistEvent(root, key, time, desc) - An event from the plist.
    """


def RecurseKey(recur_item, root='', depth=15):
  """Flattens nested dictionaries and lists by yielding it's values.

  The hierarchy of a plist file is a series of nested dictionaries and lists.
  This is a helper function helps plugins navigate the structure without
  having to reimplent their own recsurive methods.

  This method implements an overridable depth limit to prevent processing
  extremely deeply nested plists. If the limit is reached a debug message is
  logged indicating which key processing stopped on.

  Example Input Plist:
    recur_item = { DeviceRoot: { DeviceMAC1: [Value1, Value2, Value3],
                                 DeviceMAC2: [Value1, Value2, Value3]}}

  Example Output:
    ('', DeviceRoot, {DeviceMACs...})
    (DeviceRoot, DeviceMAC1, [Value1, Value2, Value3])
    (DeviceRoot, DeviceMAC2, [Value1, Value2, Value3])

  Args:
    recur_item: An object to be checked for additional nested items.
    root: The pathname of the current working key.
    depth: A counter to ensure we stop at the maximum recursion depth.

  Yields:
    A tuple of the root, key, and value from a plist.
  """
  if depth < 1:
    logging.debug(u'Recursion limit hit for key: %s', root)
    return

  if type(recur_item) in (list, tuple):
    for recur in recur_item:
      for key in RecurseKey(recur, root, depth):
        yield key
    return

  if not hasattr(recur_item, 'iteritems'):
    return

  for key, value in recur_item.iteritems():
    yield root, key, value
    if isinstance(value, dict):
      value = [value]
    if isinstance(value, list):
      for item in value:
        if isinstance(item, dict):
          for keyval in RecurseKey(
              item, root=root + u'/' + key, depth=depth - 1):
            yield keyval


def GetKeys(top_level, keys, depth=1):
  """Helper function to return keys nested in a plist dict.

  By default this function will return the values for the named keys requested
  by a plugin in match{}. The default setting is to look a single layer down
  from the root (same as the check for plugin applicability). This level is
  suitable for most cases.

  For cases where there is varability in the name at the first level
  (e.g. it is the MAC addresses of a device, or a UUID) it is possible to
  override the depth limit and use GetKeys to fetch from a deeper level.

  E.g.
  Top_Level (root):                                               # depth = 0
  |-- Key_Name_is_UUID_Generated_At_Install 1234-5678-8           # depth = 1
  |  |-- Interesting_SubKey_with_value_to_Process: [Values, ...]  # depth = 2

  Args:
    top_level: Plist in dictionary form.
    keys: A list of keys that should be returned.
    depth: Defines how many levels deep to check for a match.

  Returns:
    A dictionary with just the keys requested.
  """
  keys = set(keys)
  match = {}

  if depth == 1:
    for key in keys:
      match[key] = top_level[key]
  else:
    for _, parsed_key, parsed_value in RecurseKey(top_level, depth=depth):
      if parsed_key in keys:
        match[parsed_key] = parsed_value
        if set(match.keys()) == keys:
          return match
  return match


def GetKeysDefaultEmpty(top_level, keys, depth=1):
  """Return keys nested in a plist dict, defaulting to an empty value.

  The method GetKeys fails if the supplied key does not exist within the
  plist object. This alternate method behaves the same way as GetKeys
  except that instead of raising an error if the key doesn't exist it will
  assign a default empty value ('') to the field.

  Args:
    top_level: Plist in dictionary form.
    keys: A list of keys that should be returned.
    depth: Defines how many levels deep to check for a match.

  Returns:
    A dictionary with just the keys requested.
  """
  keys = set(keys)
  match = {}

  if depth == 1:
    for key in keys:
      value = top_level.get(key, None)
      if value is not None:
        match[key] = value
  else:
    for _, parsed_key, parsed_value in RecurseKey(top_level, depth=depth):
      if parsed_key in keys:
        match[parsed_key] = parsed_value
        if set(match.keys()) == keys:
          return match
  return match
