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
"""A simple dump information gathered from a plaso storage container.

pinfo stands for Plaso INniheldurFleiriOrd or plaso contains more words.
"""
# To make YAML loading work.

import argparse
import datetime
import locale
import logging
import os
import pprint
import sys

from plaso.lib import storage


def GetInformation(params):
  """Return generator for all potential storage information in a container."""
  try:
    store = storage.PlasoStorage(params.storage_file, read_only=True)
  except IOError as e:
    logging.error(u'Unable to open storage file: %s', e)
    return

  infos = store.GetStorageInformation()

  if not infos:
    yield ''
    return

  last_entry = False

  for index, info in enumerate(infos):
    if index == len(infos) - 1:
      last_entry = True
    yield DisplayInformation(info, params, store, last_entry)


def DisplayInformation(info, params, store, last_entry=False):
  """Return information gathered from storage."""
  header = u''
  information = u''
  printer = pprint.PrettyPrinter(indent=8)
  if hasattr(info, 'collection_information'):
    date = datetime.datetime.utcfromtimestamp(
        info.collection_information.get('time_of_run', 0))
    filename = info.collection_information.get('file_processed', 'N/A')

    header = (u'{0}\n\t\tPlaso Storage Information\n{0}\nStorage file: {3}\nFil'
              'e processed: {1}\nTime of processing: {2}\n').format(
                  '-' * 80, filename, date.isoformat(), params.storage_file)

    for key, value in info.collection_information.items():
      information += u'\t{0} = {1}\n'.format(key, value)

  if hasattr(info, 'counter'):
    information += u'\nCounter Information:\n'
    for key, value in info.counter.most_common():
      information += u'\tCounter: %s = %d\n' % (key, value)

  if hasattr(info, 'plugin_counter'):
    information += u'\nPlugin Counter Information:\n'
    for key, value in info.plugin_counter.most_common():
      information += u'\tCounter: %s = %d\n' % (key, value)

  if hasattr(info, 'stores'):
    information += u'\nStore information:\n'
    information += u'\tNumber of available stores: %d\n' % info.stores['Number']
    if params.verbose:
      for key, value in info.stores.items():
        if key == 'Number':
          continue
        information += u'\t%s =\n%s\n' % (key, printer.pformat(value))
    else:
      information += u'\tPrintout omitted (use verbose to see)\n'

  preprocessing = u'Preprocessing information:\n'
  if params.verbose:
    for key, value in info.__dict__.items():
      if key == 'collection_information':
        continue
      elif key == 'counter' or key == 'stores':
        continue
      if isinstance(value, list):
        preprocessing += u'\t{0} = \n{1}\n'.format(key, printer.pformat(value))
      else:
        preprocessing += u'\t{0} = {1}\n'.format(key, value)
  else:
    preprocessing = u'Preprocessing information omitted (run with verbose).'

  if last_entry:
    if store.HasReports():
      reports = u'Reporting information omitted (run with verbose).'
    else:
      reports = u'No reports stored.'
  else:
    reports = ''

  if params.verbose and last_entry and store.HasReports():
    report_list = []
    for report in store.GetReports():
      report_list.append(report.GetString())
    reports = u'\n'.join(report_list)

  return u'{0}\n{1}\n{2}\n{3}\n{4}'.format(
      header, information, preprocessing, reports, '-+' * 40)


def Main():
  """Start the tool."""
  usage = """
Gives you information about the storage file, how it was
collected, what information was gained from the image, etc.
  """
  arg_parser = argparse.ArgumentParser(description=usage)

  format_str = '[%(levelname)s] %(message)s'
  logging.basicConfig(level=logging.INFO, format=format_str)

  arg_parser.add_argument(
      '-v', '--verbose', dest='verbose', action='store_true', default=False,
      help='Be extra verbose in the information printed out.')

  arg_parser.add_argument(
      'storage_file', nargs='?', action='store', metavar='STORAGE FILE',
      default=None, type=unicode, help='The storage file.')

  options = arg_parser.parse_args()

  if not options.storage_file:
    arg_parser.print_help()
    print ''
    arg_parser.print_usage()
    print ''
    logging.error('Not able to run without a storage file being indicated.')
    sys.exit(1)

  if not os.path.isfile(options.storage_file):
    logging.error(
        u'File [%s] needs to exist, and be a proper plaso storage file.',
        options.storage_file)
    sys.exit(1)

  # Get preferred encoding values.
  preferred_encoding = locale.getpreferredencoding()

  nothing = True
  for print_info in GetInformation(options):
    nothing = False
    print print_info.encode(preferred_encoding)

  if nothing:
    print u'No Plaso storage information found.'


if __name__ == '__main__':
  Main()
