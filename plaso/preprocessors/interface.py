#!/usr/bin/python
# -*- coding: utf-8 -*-
#
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
"""This file contains classes used for preprocessing in plaso."""

import abc
import logging

from binplist import binplist
from dfvfs.helpers import file_system_searcher
from xml.etree import ElementTree

from plaso.lib import errors
from plaso.lib import registry
from plaso.parsers.plist_plugins import interface as plist_interface
from plaso.winreg import cache
from plaso.winreg import path_expander as winreg_path_expander
from plaso.winreg import winregistry


class PreprocessPlugin(object):
  """Class that defines the preprocess plugin object interface.

  Any preprocessing plugin that implements this interface
  should define which operating system this plugin supports.

  The OS variable supports the following values:
    + Windows
    + Linux
    + MacOSX

  Since some plugins may require knowledge gained from
  other checks all plugins have a weight associated to it.
  The weight variable can have values from one to three:
    + 1 - Requires no prior knowledge, can run immediately.
    + 2 - Requires knowledge from plugins with weight 1.
    + 3 - Requires knowledge from plugins with weight 2.

  The default weight of 3 is assigned to plugins, so each
  plugin needs to overwrite that value if needed.

  The plugins are grouped by the operating system they work
  on and then on their weight. That means that if the tool
  is run against a Windows system all plugins that support
  Windows are grouped together, and only plugins with weight
  one are run, then weight two followed by the rest of the
  plugins with the weight of three. There is no priority or
  guaranteed order of plugins that have the same weight, which
  makes it important to define the weight appropriately.
  """
  __metaclass__ = registry.MetaclassRegistry
  __abstract = True

  # Defines the OS that this plugin supports.
  SUPPORTED_OS = []
  # Weight is an INT, with the value of 1-3.
  WEIGHT = 3

  # Defines the knowledge base attribute to be set.
  ATTRIBUTE = ''

  @property
  def plugin_name(self):
    """Return the name of the plugin."""
    return self.__class__.__name__

  def _FindFileEntry(self, searcher, path):
    """Searches for a file entry that matches the path.

    Args:
      searcher: The file system searcher object (instance of
                dfvfs.FileSystemSearcher).
      path: The location of the file entry relative to the file system
            of the searcher.

    Returns:
      The file entry if successful or None otherwise.

    Raises:
      errors.PreProcessFail: if the file entry cannot be found or opened.
    """
    find_spec = file_system_searcher.FindSpec(
        location=path, case_sensitive=False)

    path_specs = list(searcher.Find(find_specs=[find_spec]))
    if not path_specs or len(path_specs) != 1:
      raise errors.PreProcessFail(u'Unable to find: {0:s}'.format(path))

    try:
      file_entry = searcher.GetFileEntryByPathSpec(path_specs[0])
    except IOError as exception:
      raise errors.PreProcessFail(
          u'Unable to retrieve file entry: {0:s} with error: {1:s}'.format(
              path, exception))

    return file_entry

  @abc.abstractmethod
  def GetValue(self, searcher, knowledge_base):
    """Return the value for the attribute.

    Args:
      searcher: The file system searcher object (instance of
                dfvfs.FileSystemSearcher).
      knowledge_base: A knowledge base object (instance of KnowledgeBase),
                      which contains information from the source data needed
                      for parsing.
    """
    raise NotImplementedError

  def Run(self, searcher, knowledge_base):
    """Set the attribute of the object store to the value from GetValue.

    Args:
      searcher: The file system searcher object (instance of
                dfvfs.FileSystemSearcher).
      knowledge_base: A knowledge base object (instance of KnowledgeBase),
                      which contains information from the source data needed
                      for parsing.
    """
    value = self.GetValue(searcher, knowledge_base)
    knowledge_base.SetValue(self.ATTRIBUTE, value)
    value = knowledge_base.GetValue(self.ATTRIBUTE, default_value=u'N/A')
    logging.info(u'[PreProcess] Set attribute: {0:s} to {1:s}'.format(
        self.ATTRIBUTE, value))


class MacPlistPreprocess(PreprocessPlugin):
  """Class that defines the Mac OS X plist preprocess plugin object."""
  __abstract = True

  SUPPORTED_OS = ['MacOSX']
  WEIGHT = 2

  # Path to the plist file to be parsed, can depend on paths discovered
  # in previous preprocessors.
  PLIST_PATH = ''

  # The key that's value should be returned back. It is an ordered list
  # of preference. If the first value is found it will be returned and no
  # others will be searched.
  PLIST_KEYS = ['']

  def GetValue(self, searcher, unused_knowledge_base):
    """Returns a value retrieved from keys within a plist file.

    Where the name of the keys are defined in PLIST_KEYS.

    Args:
      searcher: The file system searcher object (instance of
                dfvfs.FileSystemSearcher).
      knowledge_base: A knowledge base object (instance of KnowledgeBase),
                      which contains information from the source data needed
                      for parsing.

    Returns:
      The value of the first key that is found.

    Raises:
      errors.PreProcessFail: if the preprocessing fails.
    """
    file_entry = self._FindFileEntry(searcher, self.PLIST_PATH)
    if not file_entry:
      raise errors.PreProcessFail(
          u'Unable to open file: {0:s}'.format(self.PLIST_PATH))

    file_object = file_entry.GetFileObject()
    value = self.ParseFile(file_entry, file_object)
    file_object.close()

    return value

  def ParseFile(self, file_entry, file_object):
    """Parses the plist file and returns the parsed key.

    Args:
      file_entry: The file entry (instance of dfvfs.FileEntry).
      file_object: The file-like object.

    Returns:
      The value of the first key defined by PLIST_KEYS that is found.

    Raises:
      errors.PreProcessFail: if the preprocessing fails.
    """
    try:
      plist_file = binplist.BinaryPlist(file_object)
      top_level_object = plist_file.Parse()

    except binplist.FormatError as exception:
      raise errors.PreProcessFail(
          u'File is not a plist: {0:s} with error: {1:s}'.format(
              file_entry.path_spec.comparable, exception))

    except OverflowError as exception:
      raise errors.PreProcessFail(
          u'Unable to process plist: {0:s} with error: {1:s}'.format(
              file_entry.path_spec.comparable, exception))

    if not plist_file:
      raise errors.PreProcessFail(
          u'File is not a plist: {0:s}'.format(file_entry.path_spec.comparable))

    match = None
    key_name = ''
    for plist_key in self.PLIST_KEYS:
      try:
        match = plist_interface.GetKeys(
            top_level_object, frozenset([plist_key]))
      except KeyError:
        continue
      if match:
        key_name = plist_key
        break

    if not match:
      raise errors.PreProcessFail(
          u'Keys not found inside plist file: {0:s}.'.format(
              u','.join(self.PLIST_KEYS)))

    return self.ParseKey(match, key_name)

  def ParseKey(self, key, key_name):
    """Retrieves a specific value from the key.

    Args:
      key: The key object (instance of dict).
      key_name: The name of the key.

    Returns:
      The value of the key defined by key_name.

    Raises:
      errors.PreProcessFail: if the preprocessing fails.
    """
    value = key.get(key_name, None)
    if not value:
      raise errors.PreProcessFail(
          u'Value of key: {0:s} not found.'.format(key_name))

    return value


class MacXMLPlistPreprocess(MacPlistPreprocess):
  """Class that defines the Mac OS X XML plist preprocess plugin object."""
  __abstract = True

  def _GetKeys(self, xml_root, key_name):
    """Return a dict with the requested keys."""
    match = {}

    generator = xml_root.iter()
    for key in generator:
      if 'key' in key.tag and key_name in key.text:
        value_key = generator.next()
        value = ''
        for subkey in value_key.iter():
          if 'string' in subkey.tag:
            value = subkey.text
        match[key.text] = value

    # Now we need to go over the match dict and retrieve values.
    return match

  def ParseFile(self, file_entry, file_object):
    """Parse the file and return parsed key.

    Args:
      file_entry: The file entry (instance of dfvfs.FileEntry).
      file_object: The file-like object.

    Returns:
      The value of the first key defined by PLIST_KEYS that is found.

    Raises:
      errors.PreProcessFail: if the preprocessing fails.
    """
    # TODO: Move to defusedxml for safer XML parsing.
    try:
      xml = ElementTree.parse(file_object)
    except ElementTree.ParseError:
      raise errors.PreProcessFail(u'File is not a XML file.')
    except IOError:
      raise errors.PreProcessFail(u'File is not a XML file.')

    xml_root = xml.getroot()
    key_name = ''
    match = None
    for key in self.PLIST_KEYS:
      match = self._GetKeys(xml_root, key)
      if match:
        key_name = key
        break

    if not match:
      raise errors.PreProcessFail(
          u'Keys not found inside plist file: {0:s}.'.format(
              u','.join(self.PLIST_KEYS)))

    return self.ParseKey(match, key_name)


class WindowsRegistryPreprocess(PreprocessPlugin):
  """Class that defines the Windows Registry preprocess plugin object.

  By default registry needs information about system paths, which excludes
  them to run in priority 1, in some cases they may need to run in priority
  3, for instance if the Registry key is dependent on which version of Windows
  is running, information that is collected during priority 2.
  """
  __abstract = True

  SUPPORTED_OS = ['Windows']
  WEIGHT = 2

  REG_KEY = '\\'
  REG_PATH = '{sysregistry}'
  REG_FILE = 'SOFTWARE'

  def __init__(self):
    """Initializes the Window Registry preprocess plugin object."""
    super(WindowsRegistryPreprocess, self).__init__()
    self._file_path_expander = winreg_path_expander.WinRegistryKeyPathExpander()
    self._key_path_expander = None

  def GetValue(self, searcher, knowledge_base):
    """Return the value gathered from a Registry key for preprocessing.

    Args:
      searcher: The file system searcher object (instance of
                dfvfs.FileSystemSearcher).
      knowledge_base: A knowledge base object (instance of KnowledgeBase),
                      which contains information from the source data needed
                      for parsing.

    Raises:
      errors.PreProcessFail: if the preprocessing fails.
    """
    # TODO: optimize this in one find.
    try:
      # TODO: do not pass the full pre_obj here but just the necessary values.
      path = self._file_path_expander.ExpandPath(
          self.REG_PATH, pre_obj=knowledge_base.pre_obj)
    except KeyError:
      path = u''

    if not path:
      raise errors.PreProcessFail(
          u'Unable to expand path: {0:s}'.format(self.REG_PATH))

    find_spec = file_system_searcher.FindSpec(
        location=path, case_sensitive=False)
    path_specs = list(searcher.Find(find_specs=[find_spec]))

    if not path_specs or len(path_specs) != 1:
      raise errors.PreProcessFail(
          u'Unable to find directory: {0:s}'.format(self.REG_PATH))

    directory_location = searcher.GetRelativePath(path_specs[0])
    if not directory_location:
      raise errors.PreProcessFail(
          u'Missing directory location for: {0:s}'.format(self.REG_PATH))

    # The path is split in segments to make it path segement separator
    # independent (and thus platform independent).
    path_segments = searcher.SplitPath(directory_location)
    path_segments.append(self.REG_FILE)

    find_spec = file_system_searcher.FindSpec(
        location=path_segments, case_sensitive=False)
    path_specs = list(searcher.Find(find_specs=[find_spec]))

    if not path_specs:
      raise errors.PreProcessFail(
          u'Unable to find file: {0:s} in directory: {1:s}'.format(
              self.REG_FILE, directory_location))

    if len(path_specs) != 1:
      raise errors.PreProcessFail((
          u'Find for file: {1:s} in directory: {0:s} returned {2:d} '
          u'results.').format(
              self.REG_FILE, directory_location, len(path_specs)))

    file_location = getattr(path_specs[0], 'location', None)
    if not directory_location:
      raise errors.PreProcessFail(
          u'Missing file location for: {0:s} in directory: {1:s}'.format(
              self.REG_FILE, directory_location))

    try:
      file_entry = searcher.GetFileEntryByPathSpec(path_specs[0])
    except IOError as exception:
      raise errors.PreProcessFail(
          u'Unable to open file entry: {0:s} with error: {1:s}'.format(
              file_location, exception))

    if not file_entry:
      raise errors.PreProcessFail(
          u'Unable to open file entry: {0:s}'.format(file_location))

    # TODO: remove this check win_registry.OpenFile doesn't fail instead?
    try:
      file_object = file_entry.GetFileObject()
      file_object.close()
    except IOError as exception:
      raise errors.PreProcessFail(
          u'Unable to open file object: {0:s} with error: {1:s}'.format(
              file_location, exception))

    win_registry = winregistry.WinRegistry(
        winregistry.WinRegistry.BACKEND_PYREGF)

    try:
      winreg_file = win_registry.OpenFile(
          file_entry, codepage=knowledge_base.codepage)
    except IOError as exception:
      raise errors.PreProcessFail(
          u'Unable to open Registry file: {0:s} with error: {1:s}'.format(
              file_location, exception))

    self.winreg_file = winreg_file

    if not self._key_path_expander:
      # TODO: it is more efficient to have one cache that is passed to every
      # plugin, or maybe one path expander. Or replace the path expander by
      # dfvfs WindowsPathResolver?
      reg_cache = cache.WinRegistryCache()
      reg_cache.BuildCache(winreg_file, self.REG_FILE)
      self._key_path_expander = winreg_path_expander.WinRegistryKeyPathExpander(
          reg_cache=reg_cache)

    try:
      # TODO: do not pass the full pre_obj here but just the necessary values.
      key_path = self._key_path_expander.ExpandPath(
          self.REG_KEY, pre_obj=knowledge_base.pre_obj)
    except KeyError:
      key_path = u''

    if not key_path:
      raise errors.PreProcessFail(
          u'Unable to expand path: {0:s}'.format(self.REG_KEY))

    try:
      key = winreg_file.GetKeyByPath(key_path)
    except IOError as exception:
      raise errors.PreProcessFail(
          u'Unable to fetch Registry key: {0:s} with error: {1:s}'.format(
              key_path, exception))

    if not key:
      raise errors.PreProcessFail(
          u'Registry key {0:s} does not exist.'.format(self.REG_KEY))

    return self.ParseKey(key)

  @abc.abstractmethod
  def ParseKey(self, key):
    """Extract information from a Registry key and save in storage."""


class PreprocessGetPath(PreprocessPlugin):
  """Return a simple path."""
  __abstract = True

  WEIGHT = 1
  ATTRIBUTE = 'nopath'
  PATH = 'doesnotexist'

  def GetValue(self, searcher, unused_knowledge_base):
    """Returns the path as found by the searcher.

    Args:
      searcher: The file system searcher object (instance of
                dfvfs.FileSystemSearcher).
      knowledge_base: A knowledge base object (instance of KnowledgeBase),
                      which contains information from the source data needed
                      for parsing.

    Returns:
      The first path location string.

    Raises:
      PreProcessFail: if the path could not be found.
    """
    find_spec = file_system_searcher.FindSpec(
        location_regex=self.PATH, case_sensitive=False)
    path_specs = list(searcher.Find(find_specs=[find_spec]))

    if not path_specs:
      raise errors.PreProcessFail(
          u'Unable to find path: {0:s}'.format(self.PATH))

    relative_path = searcher.GetRelativePath(path_specs[0])
    if not relative_path:
      raise errors.PreProcessFail(
          u'Missing relative path for: {0:s}'.format(self.PATH))

    return relative_path


def GuessOS(searcher):
  """Returns a string representing what we think the underlying OS is.

  The available return strings are:
    + Windows
    + MacOSX
    + Linux

  Args:
    searcher: The file system searcher object (instance of
              dfvfs.FileSystemSearcher).

  Returns:
     A string indicating which OS we are dealing with.
  """
  find_specs = [
    file_system_searcher.FindSpec(
        location=u'/etc', case_sensitive=False),
    file_system_searcher.FindSpec(
        location=u'/System/Library', case_sensitive=False),
    file_system_searcher.FindSpec(
        location=u'/Windows/System32', case_sensitive=False),
    file_system_searcher.FindSpec(
        location=u'/WINNT/System32', case_sensitive=False),
    file_system_searcher.FindSpec(
        location=u'/WINNT35/System32', case_sensitive=False),
    file_system_searcher.FindSpec(
        location=u'/WTSRV/System32', case_sensitive=False)]

  locations = []
  for path_spec in searcher.Find(find_specs=find_specs):
    relative_path = searcher.GetRelativePath(path_spec)
    if relative_path:
      locations.append(relative_path.lower())

  # We need to check for both forward and backward slashes since the path
  # spec will be OS dependent, as in running the tool on Windows will return
  # Windows paths (backward slash) vs. forward slash on *NIX systems.
  windows_locations = set([
      u'/windows/system32', u'\\windows\\system32', u'/winnt/system32',
      u'\\winnt\\system32', u'/winnt35/system32', u'\\winnt35\\system32',
      u'\\wtsrv\\system32', u'/wtsrv/system32'])

  if windows_locations.intersection(set(locations)):
    return 'Windows'

  if u'/system/library' in locations:
    return 'MacOSX'

  if u'/etc' in locations:
    return 'Linux'

  return 'None'
