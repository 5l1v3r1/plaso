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
"""This file contains the EventObject and all implementations of it.

This file contains the definition for the EventObject and EventContainer,
which are core components of the storage mechanism of plaso.

"""
import heapq
import re

from plaso.lib import errors
from plaso.lib import timelib

# Regular expression used for attribute filtering
UPPER_CASE = re.compile('[A-Z]')


class EventContainer(object):
  """The EventContainer serves as a basic storage mechansim for plaso.

  An event container is a simple placeholder that is used to store
  EventObjects. It can also hold other EventContainer objects and basic common
  attributes among the EventObjects that are stored within it.

  An example of this scheme is:
    One container stores all logs from host A. That container therefore stores
    the hostname attribute.
    Then for each file that gets parsed a new container is created, which
    holds the common attributes for that file.

  That way the EventObject does not need to store all these attributes, only
  those that differ between different containers.

  The container also stores two timestamps, one for the first timestamp of
  all EventObjects that it contains, and the second one for the last one.
  That makes timebased filtering easier, since filtering can discard whole
  containers if they are outside the scope instead of going through each
  and every event.
  """

  # Define needed attributes
  events = None
  containers = None
  parent_container = None
  first_timestamp = None
  last_timestamp = None
  attributes = None

  def __init__(self):
    """Initializes the event container."""
    # A placeholder for all EventObjects directly stored.
    self.events = []

    # A placeholder for all EventContainer directly stored.
    self.containers = []

    self.first_timestamp = 0
    self.last_timestamp = 0

    self.attributes = {}

  def __setattr__(self, attr, value):
    """Sets the value to either the default or the attribute store."""
    try:
      object.__getattribute__(self, attr)
      object.__setattr__(self, attr, value)
    except AttributeError:
      self.attributes.__setitem__(attr, value)

  def __getattr__(self, attr):
    """Return attribute value from either attribute store.

    Args:
      attr: The attribute name

    Returns:
      The attribute value if one is found.

    Raise:
      AttributeError: If the object does not have the attribute
                      in either store.
    """
    try:
      return object.__getattribute__(self, attr)
    except AttributeError:
      pass

    # Try getting the attributes from the other attribute store.
    try:
      return self.GetValue(attr)
    except AttributeError:
      raise AttributeError('%s\' object has no attribute \'%s\'.' % (
          self.__class__.__name__, attr))

  def __len__(self):
    """Retrieves the number of items in the containter and its sub items."""
    counter = len(self.events)
    for container in self.containers:
      counter += len(container)

    return counter

  def GetValue(self, attr):
    """Determine if an attribute is set in container or in parent containers.

    Since attributes can be set either at the container level or at the
    event level, we need to provide a mechanism to traverse the tree and
    determine if the attribute has been set or not.

    Args:
      attr: The name of the attribute that needs to be checked.

    Returns:
      The attribute value if it exists, otherwise an exception is raised.

    Raises:
      AttributeError: if the attribute is not defined in either the container
                      itself nor in any parent containers.
    """
    if attr in self.attributes:
      return self.attributes.__getitem__(attr)

    if self.parent_container:
      return self.parent_container.GetValue(attr)

    raise AttributeError("'%s' object has no attribute '%s'." % (
        self.__class__.__name__, attr))

  def GetAttributes(self):
    """Return a set of all defined attributes.

    This returns attributes defined in the object that do not fall
    under the following criteria:
      + Starts with _
      + Starts with an upper case letter.

    Returns:
      A set that contains all the attributes that are either stored
      in the attribute store or inside the attribute store of any
      of the parent containers.
    """
    res = set(self.attributes.keys())

    if self.parent_container:
      res |= self.parent_container.GetAttributes()

    return res

  def __iter__(self):
    """An iterator that returns alls EventObjects stored in the containers."""
    all_events = []

    for event in self.events:
      heapq.heappush(all_events, (event.timestamp, event))
    for container in self.containers:
      for event in container:
        heapq.heappush(all_events, (event.timestamp, event))

    for _ in range(len(all_events)):
      yield heapq.heappop(all_events)[1]

  def Append(self, item):
    """Append either an EventContainer or an EventObject to the container.

    Args:
      item: The EventContainer or the EventObject to add to the container.

    Raises:
      errors.NotAnEventContainerOrObject: When an object is passed to the
      function that is not an EventObject or an EventContainer.
    """
    try:
      if item.description_long:
        self._Append(item, self.events, item.timestamp)
        return
    except AttributeError:
      pass
    except NotImplementedError:
      raise errors.NotAnEventContainerOrObject(
          'Unable to add an object that has not implemented description_long')
    try:
      if item.events and item.Append:
        self._Append(item, self.containers, item.first_timestamp,
                     item.last_timestamp)
        return
    except (AttributeError, TypeError):
      pass

    raise errors.NotAnEventContainerOrObject('Unable to determine the object.')

  def _Append(self, item, storage, timestamp_first, timestamp_last=None):
    """Append objects to container while checking timestamps."""
    item.parent_container = self
    storage.append(item)

    if not timestamp_last:
      timestamp_last = timestamp_first

    if not self.last_timestamp:
      self.last_timestamp = timestamp_last

    if not self.first_timestamp:
      self.first_timestamp = timestamp_first

    if timestamp_last > self.last_timestamp:
      self.last_timestamp = timestamp_last

    if timestamp_first < self.first_timestamp:
      self.first_timestamp = timestamp_first


class EventObject(object):
  """An event object is the main datastore for an event in plaso.

  The framework is designed to parse files and create an event
  from every single record, line or key extracted from the file.

  An EventContainer is the main data store for that event, however
  the container only contains information about common atttributes
  to the event and information about all the EventObjects that are
  associated to that event. The EventObject is more tailored to the
  content of the parsed data and it will contain the actual data
  portion of the Event.

  This class defines the high level interface of EventObject.
  Before creating an EventObject a class needs to be implemented
  that inherits from EventObject and implements the functions in it.

  The EventObject is then used by output processing for saving
  in other forms, such as a protobuff, AFF4 container, CSV files,
  databases, etc.

  The goal of the EventObject is to provide a easily extensible
  data storage of each events internally in the tool.

  The main EventObject only exposes those functions that the
  implementations need to implement. The functions that are needed
  simply provide information about the event, or describe the
  attributes that are necessary. How they are assembled is totally
  up to the implementation.

  All required attributes of the EventObject are passed to the
  constructor of the object while the optional ones are set
  using the method SetValue(attribute, value).
  """

  parent_container = None
  attributes = None

  def __init__(self):
    """Initializes the event object."""
    self.attributes = {}

  def __setattr__(self, attr, value):
    """Sets the value to either the default or the attribute store."""
    try:
      object.__getattribute__(self, attr)
      object.__setattr__(self, attr, value)
    except AttributeError:
      self.attributes.__setitem__(attr, value)

  def __getattr__(self, attr):
    """Determine if attribute is set within the event or in a container."""
    try:
      return object.__getattribute__(self, attr)
    except AttributeError:
      pass

    # Check the attribute store.
    try:
      if attr in self.attributes:
        return self.attributes.__getitem__(attr)
    except TypeError as e:
      raise AttributeError('[Event] %s', e)

    # Check the parent.
    if self.parent_container:
      try:
        return self.parent_container.GetValue(attr)
      except AttributeError:
        raise AttributeError('%s\' object has no attribute \'%s\'.' % (
            self.__class__.__name__, attr))

    raise AttributeError('Attribute not defined')

  def GetAttributes(self):
    """Return a list of all defined attributes."""
    res = set(self.attributes.keys())

    # Description field is defined as a property, and therefore
    # needs to be included in the set.
    res.add('description_long')
    res.add('description_short')

    if self.parent_container:
      res |= self.parent_container.GetAttributes()

    return res

  def __str__(self):
    """Print a human readable string from the EventObject."""
    time = 0
    short = u''
    s_long = u''
    desc = u''

    __pychecker__ = ('missingattrs=timestamp,source_short,sou'
                     'rce_long,description_long')
    try:
      time = self.timestamp
    except AttributeError:
      pass

    try:
      short = self.source_short
    except AttributeError:
      pass
    try:
      s_long = self.source_long
    except AttributeError:
      pass
    try:
      desc = self.description_long
    except AttributeError:
      pass

    return u'[{0}] {1}/{2} - {3}'.format(time, short, s_long, desc)


class FiletimeEvent(EventObject):
  """Convenience class for a FILETIME timestamp-based event."""

  def __init__(self, timestamp, description, description_long):
    """Initializes a FILETIME timestamp-based event object.

    Args:
      timestamp: the FILETIME timestamp value.
      description: the description of the usage of the timestamp.
      description_long: the long description (LEGACY).
    """
    super(FiletimeEvent, self).__init__()
    self.timestamp = timelib.WinFiletime2Unix(timestamp)
    self.timestamp_desc = description
    self.text_long = description_long
    self.text_short = description_long

  @property
  def description_long(self):
    return u'%s' % self.text_long

  @property
  def description_short(self):
    if len(self.text_short) > 80:
      return u'%s...' % self.text_short[0:77]

    return u'%s' % self.text_short


class RegistryEvent(EventObject):
  """Convenience class for a Windows Registry-based event."""

  # Add few class variables so they don't get defined as special attributes.
  keyname = u''
  keyvalue_dict = u''
  source_append = u''

  def __init__(self, key, value_dict, timestamp=None, desc=None):
    """Initializes a Windows registry event.

    Args:
      key: Name of the registry key being parsed.
      value_dict: The interpreted value of the key, stored as a dictionary.
      timestamp: If a timestamp is associated to the event, it's stored
      in a micro second value since Jan 1 1970 UTC.
      desc: Description of the timestamp.
    """
    super(RegistryEvent, self).__init__()
    self.source_short = 'REG'
    self.keyname = key
    self.keyvalue_dict = value_dict
    self.timestamp = timestamp
    self.timestamp_desc = desc or 'Last Written'

  @property
  def description_long(self):
    text = u' '.join([u'%s: %s' % (key, value) for (
        key, value) in sorted(self.keyvalue_dict.items())])
    if self.keyname:
      return u'[%s] %s' % (self.keyname, text)

    return text

  @property
  def description_short(self):
    text = self.keyname or u' '.join([u'%s: %s' % (key, value) for (
        key, value) in sorted(self.keyvalue_dict.items())])

    if len(text) > 80:
      return u'[%s...]' % text[0:77]

    return u'[%s]' % text


class TextEvent(EventObject):
  """Convenience class for a text log file-based event."""

  # Define attributes outside of attribute store.
  body = None

  def __init__(self, date, body, source, host=None, user=None):
    """Initializes a text event.

    Args:
      date: An integer, representing the time in microseconds since
            Jan 1, 1970 00:00:00 UTC.
      body: The text, processesed as it should be presented.
      source: The source_long description of the event.
      host: An optional host name if one is available within the log file.
      user: An optional user name if one is available within the log file.
    """
    super(TextEvent, self).__init__()
    self.timestamp = date
    self.timestamp_desc = 'Entry Written'
    self.source_short = 'LOG'
    self.source_long = source
    self.body = body
    if host:
      self.hostname = host
    if user:
      self.username = user

  @property
  def description_long(self):
    return '%s' % self.body

  @property
  def description_short(self):
    if len(self.body) > 80:
      return '%s...' % self.body[0:77]
    else:
      return '%s' % self.body


class SQLiteEvent(EventObject):
  """Convenience class for a SQLite-based event."""

  text_long = ''
  text_short = ''

  def __init__(self, date, description, description_long, description_short,
               source_short, source_long):
    """Initializes the SQLite-based event.

    Args:
      date: An integer, representing the time in microseconds since
            Jan 1, 1970 00:00:00 UTC.
      description: The timestamp description of the event.
      description_long: A string, the content of the description_long.
      description_short: A string, the content of the description_short.
      source_short: A string, the content of source_short.
      source_long: A string, the content of source_long.
    """
    super(SQLiteEvent, self).__init__()
    self.timestamp = date
    self.timestamp_desc = description
    self.source_short = source_short
    self.source_long = source_long
    self.text_long = description_long
    self.text_short = description_short

  @property
  def description_long(self):
    return u'%s' % self.text_long

  @property
  def description_short(self):
    if len(self.text_short) > 80:
      return u'%s...' % self.text_short[0:77]

    return u'%s' % self.text_short

