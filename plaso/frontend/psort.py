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
"""Psort (Plaso Síar Og Raðar Þessu) - Makes output from Plaso Storage files.

Sample Usage:
  psort.py /tmp/mystorage.dump "date > '01-06-2012'"

See additional details here: http://plaso.kiddaland.net/usage/psort
"""
import argparse
import datetime
import os
import logging
import pdb
import sys

from plaso import filters
from plaso import formatters
from plaso import output

from plaso.lib import engine
from plaso.lib import event
from plaso.lib import filter_interface
from plaso.lib import limit
from plaso.lib import output as output_lib
from plaso.lib import storage
from plaso.lib import utils
from plaso.proto import plaso_storage_pb2
import pytz


def SetupStorage(input_file_path):
  """Sets up the storage object.

  Attempts to initialize the storage object from the PlasoStorage library.  If
  we fail on a IO Error (common case for typos) log a warning and gracefully
  exit.

  Args:
    input_file_path: Filesystem path to the plaso storage container.

  Returns:
    A storage.PlasoStorage object.
  """
  try:
    return storage.PlasoStorage(input_file_path, read_only=True)
  except IOError as details:
    logging.error('IO ERROR: %s', details)
  else:
    logging.error('Other Critical Failure Reading Files')
  sys.exit(1)


def ProcessOutput(output_buffer, formatter, my_filter=None):
  """Fetch EventObjects from storage and process and filter them.

  Args:
    output_buffer: output.EventBuffer object.
    formatter: An OutputFormatter.
    my_filter: A filter object.
  """
  filter_count = 0
  total_count = 0
  limit = getattr(my_filter, 'limit', 0)

  event_object = formatter.FetchEntry()
  while event_object:
    if my_filter:
      event_match = event_object
      if isinstance(event_object, plaso_storage_pb2.EventObject):
        event_match = event.EventObject()
        event_match.FromProto(event_object)

      if my_filter.Match(event_match):
        output_buffer.Append(event_object)
        if limit:
          total_count += 1
          if total_count is limit:
            break
      else:
        filter_count += 1
    else:
      output_buffer.Append(event_object)

    event_object = formatter.FetchEntry()

  if filter_count:
    logging.info('Events filtered out: %d', filter_count)

  if output_buffer.duplicate_counter:
    logging.info(
        'Duplicate entries removed: %d', output_buffer.duplicate_counter)


def ParseStorage(my_args):
  """Open a storage file and parse through it."""
  filter_use = None
  if my_args.filter:
    filter_use = filter_interface.GetFilter(my_args.filter)
    if not filter_use:
      logging.error(
          u'No filter found for the filter expression: {}'.format(
              my_args.filter))
      sys.exit(1)

  with SetupStorage(my_args.storagefile) as store:
    # Identify which stores to use.
    store.SetStoreLimit(filter_use)

    try:
      formatter_cls = output_lib.GetOutputFormatter(my_args.output_format)
      if not formatter_cls:
        logging.error((
            u'Wrong output module choosen, module <{}> does not exist. Please '
            'use {} -o list to see all available modules.').format(
                my_args.output_format, sys.argv[0]))
        sys.exit(1)
      formatter = formatter_cls(
              store, my_args.write, pytz.timezone(my_args.timezone), filter_use)
    except IOError as e:
      logging.error(u'Error occured during output processing: %s', e)

    if not formatter:
      logging.error(u'Unable to proceed, output buffer not available.')
      sys.exit(1)

    with output_lib.EventBuffer(formatter, my_args.dedup) as output_buffer:
      ProcessOutput(output_buffer, formatter, filter_use)


def Main():
  """Start the tool."""
  parser = argparse.ArgumentParser(
      description=(
          u'PSORT (Plaso Síar Og Raðar Þessu) - Read, filter and process '
          'output from a plaso storage file.'))

  parser.add_argument(
      '-d', '--debug', action='store_true', dest='debug', default=False,
      help='Fall back to debug shell if psort fails.')

  # TODO: Change this behavior so by default it runs with dedups removed once
  # the dedup process has been optimized and does not slow down the tool as
  # much as the current implementation.
  parser.add_argument(
      '-r', '--remove_dedup', action='store_true', dest='dedup', default=False,
      help=(
          'Check and merge duplicate entries in the storage file '
          '(experimental option at this stage).'))

  parser.add_argument(
      '-o', '--output_format', metavar='FORMAT', dest='output_format',
      default='L2tCsv', help='Output format.  -o list to see loaded modules.')

  parser.add_argument(
      '-z', '--zone', metavar='TIMEZONE', default='UTC', dest='timezone',
      help='Timezone of output. list: "-z list"')

  parser.add_argument(
      '-w', '--write', metavar='OUTPUTFILE', dest='write',
      help='Output filename.  Defaults to stdout.')

  parser.add_argument(
      '-v', '--version', dest='version', action='version',
      version='log2timeline - psort version %s' % engine.__version__,
      help='Show the current version of psort.')

  parser.add_argument(
      'storagefile', metavar='PLASOFILE', default=None, nargs='?',
      help='Path to the Plaso storage file')

  parser.add_argument(
      'filter', nargs='?', action='store', metavar='FILTER', default=None,
      help=('A filter that can be used to filter the dataset before it '
            'is written into storage. More information about the filters'
            ' and it\'s usage can be found here: http://plaso.kiddaland.'
            'net/usage/filters'))

  my_args = parser.parse_args()

  format_str = '[%(levelname)s] %(message)s'
  logging.basicConfig(level=logging.INFO, format=format_str)

  if my_args.timezone == 'list':
    print utils.FormatHeader('Zones')
    max_length = 0
    for zone in pytz.all_timezones:
      if len(zone) > max_length:
        max_length = len(zone)

    print utils.FormatOutputString('Timezone', 'UTC Offset', max_length)
    for zone in pytz.all_timezones:
      zone_obj = pytz.timezone(zone)
      date_str = str(zone_obj.localize(datetime.datetime.utcnow()))
      if '+' in date_str:
        _, _, diff = date_str.rpartition('+')
        diff_string = '+{}'.format(diff)
      else:
        _, _, diff = date_str.rpartition('-')
        diff_string = '-{}'.format(diff)
      print utils.FormatOutputString(zone, diff_string, max_length)
    print '-' * 80
    sys.exit(0)

  if my_args.output_format == 'list':
    print utils.FormatHeader('Output Modules')
    for name, description in output_lib.ListOutputFormatters():
      print utils.FormatOutputString(name, description, 10)
    print '-' * 80
    sys.exit(0)

  if not my_args.storagefile:
    parser.print_help()
    print ''
    parser.print_usage()
    print ''
    logging.error('STORAGEFILE required! or -h for HELP')
    sys.exit(0)

  if not os.path.isfile(my_args.storagefile):
    parser.print_help()
    print ''
    parser.print_usage()
    print ''
    logging.error(u'Storage file {} does not exist.'.format(
        my_args.storagefile))
    sys.exit(0)

  if not my_args.write:
    my_args.write = sys.stdout

  try:
    ParseStorage(my_args)
  except IOError as e:
    # Piping results to "|head" for instance causes an IOError.
    if 'Broken pipe' not in str(e):
      logging.error('Processing stopped early: %s.', e)
  except KeyboardInterrupt:
    pass
  # Catching a very generic error in case we would like to debug
  # a potential crash in the tool.
  except Exception:
    if not my_args.debug:
      raise
    pdb.post_mortem()


if __name__ == '__main__':
  Main()
