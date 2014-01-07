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
"""Parser for the Google Chrome Cookie database."""

from plaso.lib import errors
from plaso.lib import event
from plaso.lib import eventdata
from plaso.lib import timelib

# pylint: disable-msg=unused-import
from plaso.parsers import cookie_plugins
from plaso.parsers.cookie_plugins import interface as cookie_interface
from plaso.parsers.sqlite_plugins import interface


class ChromeCookieEvent(event.TimestampEvent):
  """Convenience class for a Chrome Cookie event."""

  DATA_TYPE = 'chrome:cookie:entry'

  def __init__(self, webkit_timestamp, timestamp_desc):
    """Initialize the event.

    Args:
      webkit_timestamp: Timestamp in the WebKit format.
      timestamp_desc: A timestamp description.
    """
    timestamp = timelib.Timestamp.FromWebKitTime(webkit_timestamp)
    super(ChromeCookieEvent, self).__init__(timestamp, timestamp_desc)


class ChromeCookieContainer(event.EventContainer):
  """Convenience class for a Chrome Cookie event container."""

  def __init__(self, hostname, cookie_name, value, path, secure, httponly,
               persistent):
    """Initializes the container.

    Args:
      hostname: The hostname of host that set the cookie value.
      cookie_name: The name field of the cookie.
      value: The value of the cookie.
      path: An URI of the page that set the cookie.
      secure: Indication if this cookie should only be transmitted over a secure
      channel.
      httponly: An indication that the cookie cannot be accessed through client
      side script.
      persistent: A flag indicating cookies persistent value.
    """
    super(ChromeCookieContainer, self).__init__()
    if hostname.startswith('.'):
      hostname = hostname[1:]

    self.host = hostname
    self.cookie_name = cookie_name
    self.data = value
    self.path = path
    self.secure = True if secure else False
    self.httponly = True if httponly else False
    self.persistent = True if persistent else False

    if self.secure:
      scheme = u'https'
    else:
      scheme = u'http'

    self.url = u'{}://{}{}'.format(scheme, hostname, path)

class ChromeCookiePlugin(interface.SQLitePlugin):
  """Parse Chrome Cookies file."""

  NAME = 'chrome_cookies'

  # Define the needed queries.
  QUERIES = [(('SELECT creation_utc, host_key, name, value, path, expires_utc,'
               'secure, httponly, last_access_utc, has_expires, persistent '
               'FROM cookies'), 'ParseCookieRow')]

  # The required tables common to Archived History and History.
  REQUIRED_TABLES = frozenset(['cookies', 'meta'])

  # Point to few sources for URL information.
  URLS = [
      u'http://src.chromium.org/svn/trunk/src/net/cookies/',
      (u'http://www.dfinews.com/articles/2012/02/'
       u'google-analytics-cookies-and-forensic-implications')]

  # Google Analytics __utmz variable translation.
  # Taken from:
  #   http://www.dfinews.com/sites/dfinews.com/files/u739/Tab2Cookies020312.jpg
  GA_UTMZ_TRANSLATION = {
      'utmcsr': 'Last source used to access.',
      'utmccn': 'Ad campaign information.',
      'utmcmd': 'Last type of visit.',
      'utmctr': 'Keywords used to find site.',
      'utmcct': 'Path to the page of referring link.'}

  def __init__(self, pre_obj):
    """Initialize the plugin."""
    super(ChromeCookiePlugin, self).__init__(pre_obj)
    self._cookie_plugins = cookie_interface.GetPlugins(
        pre_obj, ChromeCookieEvent.DATA_TYPE)

  def ParseCookieRow(self, row):
    """Parses a cookie row.

    Args:
      row: The row resulting from the query.

    Yields:
      An event container (ChromeCookieContainer) containing the event data.
    """
    container = ChromeCookieContainer(
        row['host_key'], row['name'], row['value'], row['path'], row['secure'],
        row['httponly'], row['persistent'])

    container.Append(ChromeCookieEvent(
        row['creation_utc'], eventdata.EventTimestamp.CREATION_TIME))

    container.Append(ChromeCookieEvent(
        row['last_access_utc'], eventdata.EventTimestamp.ACCESS_TIME))

    if row['has_expires']:
      container.Append(ChromeCookieEvent(
          row['expires_utc'], 'Cookie Expires'))

    # Go through all cookie plugins to see if there are is any specific parsing
    # needed.
    for cookie_plugin in self._cookie_plugins:
      try:
        for event_object in cookie_plugin.Process(
            cookie_name=row['name'], cookie_data=row['value']):
          container.Append(event_object)
      except errors.WrongPlugin:
        pass

    yield container
