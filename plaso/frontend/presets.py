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
"""Helper file for filtering out parsers."""

categories = {
    'winxp': [
        'bencode', 'filestat', 'google_drive', 'java_idx', 'lnk',
        'mcafee_protection', 'msiecf', 'olecf', 'openxml', 'prefetch',
        'recycle_bin_info2', 'skydrive_log_error', 'skydrive_log', 'skype',
        'symantec_scanlog', 'webhist', 'winevt', 'winfirewall', 'winjob',
        'winreg'],
    'winxp_slow': [
        'hachoir', 'winxp'],
    'win7': [
        'bencode', 'chrome_cache', 'chrome_cookies', 'chrome_history',
        'filestat', 'firefox_cache', 'firefox_downloads', 'firefox_history',
        'google_drive', 'java_idx', 'lnk', 'mcafee_protection', 'msiecf',
        'olecf', 'openxml', 'opera_global', 'opera_typed_history', 'prefetch',
        'recycle_bin', 'safari_history', 'skydrive_log', 'skydrive_log_error',
        'skype', 'symantec_scanlog', 'winevtx', 'winfirewall', 'winjob',
        'winreg'],
    'win7_slow': [
        'hachoir', 'win7'],
    'webhist': [
        'chrome_cache', 'chrome_cookies', 'chrome_history', 'firefox_cache',
        'firefox_downloads', 'firefox_history', 'java_idx', 'opera_global',
        'opera_typed_history', 'msiecf', 'safari_history'],
    'linux': [
        'bencode', 'chrome_cache', 'chrome_cookies', 'chrome_history',
        'filestat', 'firefox_cache', 'firefox_downloads', 'firefox_history',
        'google_drive', 'java_idx', 'olecf', 'openxml', 'opera_global',
        'opera_typed_history', 'selinux', 'skype', 'syslog', 'utmp',
        'xchatlog', 'xchatscrollback', 'zeitgeist'],
    'macosx': [
        'appusage', 'asl_log', 'bencode', 'bsm_log', 'chrome_cache',
        'chrome_cookies', 'chrome_history', 'cups_ipp', 'filestat',
        'firefox_cache', 'firefox_downloads',
        'firefox_history', 'google_drive', 'java_idx', 'ls_quarantine',
        'mac_appfirewall_log', 'mac_document_versions', 'mac_keychain',
        'mac_securityd', 'mackeeper_cache', 'macwifi', 'olecf', 'openxml',
        'opera_global', 'opera_typed_history', 'plist', 'skype', 'syslog',
        'utmpx'],
    'android': [
        'android_calls', 'android_sms'],
}


def GetParsersFromCategory(category):
  """Return a list of parsers from a parser category."""
  return_list = []
  if category not in categories:
    return return_list

  for item in categories.get(category):
    if item in categories:
      return_list.extend(GetParsersFromCategory(item))
    else:
      return_list.append(item)

  return return_list
