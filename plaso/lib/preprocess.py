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
import collections
import logging

from plaso.lib import errors
from plaso.lib import event
from plaso.lib import registry
from plaso.lib import utils
from plaso.parsers.plist_plugins import interface as plist_interface
from plaso.winreg import cache
from plaso.winreg import path_expander as winreg_path_expander
from plaso.winreg import winregistry

from plaso.proto import plaso_storage_pb2

from binplist import binplist
from xml.etree import ElementTree

import pytz


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

  # Defines the preprocess attribute to be set.
  ATTRIBUTE = ''

  def __init__(self, obj_store, collector):
    """Initializes the preprocess plugin object.

    Args:
      obj_store: the object store.
      collector: the preprocess collector (instance of PreprocessCollector).
    """
    super(PreprocessPlugin, self).__init__()
    self._obj_store = obj_store
    self._collector = collector

  def Run(self):
    """Set the attribute of the object store to the value from GetValue."""
    setattr(self._obj_store, self.ATTRIBUTE, self.GetValue())
    logging.info(
        u'[PreProcess] Set attribute: %s to %s', self.ATTRIBUTE,
        getattr(self._obj_store, self.ATTRIBUTE, 'N/A'))

  @abc.abstractmethod
  def GetValue(self):
    """Return the value for the attribute."""
    raise NotImplementedError

  @property
  def plugin_name(self):
    """Return the name of the plugin."""
    return self.__class__.__name__


class PlasoPreprocess(object):
  """Object used to store all information gained from preprocessing."""

  def FromProto(self, proto):
    """Unserializes the PlasoPreprocess from a protobuf.

    Args:
      proto: The protobuf (plaso_storage_pb2.PreProcess).

    Raises:
      RuntimeError: when the protobuf is not of type:
                    plaso_storage_pb2.PreProcess or when an unsupported
                    attribute value type is encountered
    """
    if not isinstance(proto, plaso_storage_pb2.PreProcess):
      raise RuntimeError('Unsupported proto')

    # TODO: Clear values before setting them.
    for attribute in proto.attributes:
      key, value = event.AttributeFromProto(attribute)
      if key == 'zone':
        value = pytz.timezone(value)
      setattr(self, key, value)

    if proto.HasField('counter'):
      self.counter = collections.Counter()
      dict_obj = ProtoToDict(proto.counter)
      for title, value in dict_obj.items():
        self.counter[title] = value

    if proto.HasField('plugin_counter'):
      self.plugin_counter = collections.Counter()
      dict_obj = ProtoToDict(proto.plugin_counter)
      for title, value in dict_obj.items():
        self.plugin_counter[title] = value

    if proto.HasField('store_range'):
      range_list = []
      for value in proto.store_range.values:
        if value.HasField('integer'):
          range_list.append(value.integer)
      self.store_range = (range_list[0], range_list[-1])

    if proto.HasField('collection_information'):
      self.collection_information = ProtoToDict(
          proto.collection_information)
      zone = self.collection_information.get('configure_zone')
      if zone:
        self.collection_information['configured_zone'] = pytz.timezone(zone)

  def ToProto(self):
    """Return a PreProcess protobuf built from the object."""
    proto = plaso_storage_pb2.PreProcess()

    for attribute, value in self.__dict__.items():
      if attribute == 'collection_information':
        zone = value.get('configured_zone', '')
        if zone and hasattr(zone, 'zone'):
          value['configured_zone'] = zone.zone
        proto.collection_information.MergeFrom(DictToProto(value))
      elif attribute == 'counter':
        value_dict = dict(value.items())
        proto.counter.MergeFrom(DictToProto(value_dict))
      elif attribute == 'plugin_counter':
        value_dict = dict(value.items())
        proto.plugin_counter.MergeFrom(DictToProto(value_dict))
      elif attribute == 'store_range':
        range_proto = plaso_storage_pb2.Array()
        range_start = range_proto.values.add()
        range_start.integer = int(value[0])
        range_end = range_proto.values.add()
        range_end.integer = int(value[-1])
        proto.store_range.MergeFrom(range_proto)
      else:
        if attribute == 'zone':
          value = value.zone
        if isinstance(value, (bool, int, float, long)) or value:
          proto_attribute = proto.attributes.add()
          event.AttributeToProto(
              proto_attribute, attribute, value)

    return proto

  def FromProtoString(self, proto_string):
    """Unserializes the PlasoPreprocess from a serialized protobuf."""
    proto = plaso_storage_pb2.PreProcess()
    proto.ParseFromString(proto_string)
    self.FromProto(proto)

  def ToProtoString(self):
    """Serialize a PlasoPreprocess into a string value."""
    proto = self.ToProto()

    return proto.SerializeToString()


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

  def GetValue(self):
    """Return the value gathered from a plist file for preprocessing."""
    try:
      file_path, _, file_name = self.PLIST_PATH.rpartition('/')
      paths = self._collector.GetFilePaths(file_path, file_name)
    except errors.PathNotFound as e:
      raise errors.PreProcessFail(u'Unable to find path: %s' % e)

    if not paths:
      raise errors.PreProcessFail(u'Unable to find path: %s' % self.PLIST_PATH)

    try:
      file_entry = self._collector.OpenFileEntry(paths[0])
      file_object = file_entry.Open()
    except IOError:
      raise errors.PreProcessFail(
          u'Unable to open file {}: {}'.format(paths[0], e))

    return self.ParseFile(file_entry, file_object)

  def ParseFile(self, file_entry, file_object):
    """Parse the file and return parsed key."""
    try:
      plist_file = binplist.BinaryPlist(file_object)
      top_level_object = plist_file.Parse()
    except binplist.FormatError as e:
      raise errors.PreProcessFail(
          u'File is not a plist:{}'.format(utils.GetUnicodeString(e)))
    except OverflowError as e:
      raise errors.PreProcessFail(
          u'Error processing:{} Error:{}'.format(file_entry.display_name, e))

    if not plist_file:
      raise errors.PreProcessFail(
          u'File is not a plist:{}'.format(utils.GetUnicodeString(
              file_entry.display_name)))

    match = None
    key_name = ''
    for plist_key in self.PLIST_KEYS:
      match = plist_interface.GetKeys(
          top_level_object, frozenset([plist_key]))
      if match:
        key_name = plist_key
        break

    if not match:
      raise errors.PreProcessFail(
          u'No plist keys found, trying to locate: {}'.format(','.join(
              self.PLIST_KEYS)))

    return self.ParseKey(match, key_name)

  def ParseKey(self, key, key_name):
    """Fetch the first discovered key from PLIST_KEYS and return value."""
    value = key.get(key_name, None)
    if not value:
      raise errors.PreProcessFail('Value not found.')

    return value


class MacXMLPlistPreprocess(MacPlistPreprocess):
  """Class that defines the Mac OS X XML plist preprocess plugin object."""
  __abstract = True

  def ParseFile(self, file_entry, file_object):
    """Parse the file and return parsed key."""
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
          u'Keys not found inside plist file [{}].'.format(
              ','.join(self.PLIST_KEYS)))

    return self.ParseKey(match, key_name)

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


class WinRegistryPreprocess(PreprocessPlugin):
  """Class that defines the Windows Registry preprocess plugin object.

  By default registry needs information about system paths, which excludes
  them to run in priority 1, in some cases they may need to run in priority
  3, for instance if the registry key is dependent on which version of Windows
  is running, information that is collected during priority 2.
  """
  __abstract = True

  SUPPORTED_OS = ['Windows']
  WEIGHT = 2

  REG_KEY = '\\'
  REG_PATH = '{sysregistry}'
  REG_FILE = 'SOFTWARE'

  def __init__(self, obj_store, collector):
    """Initializes the Window Registry preprocess plugin object.

    Args:
      obj_store: the object store.
      collector: the preprocess collector (instance of PreprocessCollector).
    """
    super(WinRegistryPreprocess, self).__init__()
    self._path_expander = None

  def GetValue(self):
    """Return the value gathered from a registry key for preprocessing."""
    sys_dirs = list(self._collector.FindPaths(self.REG_PATH))
    if not sys_dirs:
      raise errors.PreProcessFail(
          u'Unable to find file name: {}/{}'.format(
              self.REG_PATH, self.REG_FILE))

    sys_dir = sys_dirs[0]
    file_name = self._collector.GetFilePaths(sys_dir, self.REG_FILE)
    if not file_name:
      raise errors.PreProcessFail(
          u'Unable to find file name: {}/{}'.format(
              sys_dir, self.REG_FILE))

    try:
      file_entry = self._collector.OpenFileEntry(file_name[0])
      file_object = file_entry.Open()
    except IOError as e:
      raise errors.PreProcessFail(
          u'Unable to open file: {} [{}]'.format(file_name[0], e))

    codepage = getattr(self._obj_store, 'code_page', 'cp1252')

    win_registry = winregistry.WinRegistry(
        winregistry.WinRegistry.BACKEND_PYREGF)

    try:
      winreg_file = self.winreg_file = win_registry.OpenFile(
          file_object, codepage=codepage)
    except IOError as e:
      raise errors.PreProcessFail(
          u'Unable to open the registry: {} [{}]'.format(file_name[0], e))

    if self._path_expander is None:
      reg_cache = cache.WinRegistryCache(winreg_file, self.REG_FILE)
      reg_cache.BuildCache()
      self._path_expander = winreg_path_expander.WinRegistryKeyPathExpander(
          self._obj_store, reg_cache)

    try:
      key_path = self._path_expander.ExpandPath(self.REG_KEY)
    except KeyError:
      key_path = u''

    try:
      key = winreg_file.GetKeyByPath(key_path)
    except IOError as e:
      raise errors.PreProcessFail(
          u'Error fetching registry key: {} Error {}'.format(key_path, e))

    if not key:
      raise errors.PreProcessFail(
          u'Registry key %s does not exist.' % self.REG_KEY)

    return self.ParseKey(key)

  @abc.abstractmethod
  def ParseKey(self, key):
    """Extract information from a registry key and save in storage."""


class PreprocessGetPath(PreprocessPlugin):
  """Return a simple path."""
  __abstract = True

  WEIGHT = 1
  ATTRIBUTE = 'nopath'
  PATH = 'doesnotexist'

  def GetValue(self):
    """Return the path as found by the collector."""
    try:
      paths = list(self._collector.FindPaths(self.PATH))
    except errors.PathNotFound as e:
      raise errors.PreProcessFail(u'Unable to find path: %s' % e)
    if paths:
      return paths[0]


def GuessOS(col_obj):
  """Return a string representing what we think the underlying OS is.

  The available return strings are:
    + Windows
    + MacOSX
    + Linux

  Args:
    col_obj: The collection object.

  Returns:
     A string indicating which OS we are dealing with.
  """
  # TODO: Add error handling for WindowsError, a builtin
  # error in Windows, but not found otherwise (so no global error exists).
  # This causes the tool to crash on Windows if preprocessor is unable to
  # guess the OS, like when accidentally run against a directory.
  try:
    if list(col_obj.FindPaths('/(Windows|WINNT)/System32')):
      return 'Windows'
  except (OSError, errors.PathNotFound):
    pass

  try:
    if list(col_obj.FindPaths('/System/Library')):
      return 'MacOSX'
  except (OSError, errors.PathNotFound):
    pass

  try:
    if list(col_obj.FindPaths('/etc')):
      return 'Linux'
  except (OSError, errors.PathNotFound):
    pass

  return 'None'


def DictToProto(dict_obj):
  """Return a dict message to a protobuf from a dict object."""
  proto_dict = plaso_storage_pb2.Dict()

  for dict_key, dict_value in dict_obj.items():
    sub_proto = proto_dict.attributes.add()
    event.AttributeToProto(sub_proto, dict_key, dict_value)

  return proto_dict


def ProtoToDict(proto):
  """Return a dict object from a Dict message."""
  dict_obj = {}
  for proto_dict in proto.attributes:
    dict_key, dict_value = event.AttributeFromProto(proto_dict)
    dict_obj[dict_key] = dict_value

  return dict_obj
