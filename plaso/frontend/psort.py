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
"""Psort (Plaso Síar Og Raðar Þessu) - Makes output from Plaso Storage files.

Sample Usage:
  psort.py /tmp/mystorage.dump "date > '01-06-2012'"

See additional details here: http://plaso.kiddaland.net/usage/psort
"""
import argparse
import collections
import datetime
import time
import os
import locale
import logging
import pdb
import sys

from plaso import filters
from plaso import formatters   # pylint: disable-msg=W0611
from plaso import output   # pylint: disable-msg=W0611

from plaso.lib import bufferlib
from plaso.lib import engine
from plaso.lib import event
from plaso.lib import output as output_lib
from plaso.lib import pfilter
from plaso.lib import storage
from plaso.lib import timelib
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


def ProcessOutput(
    output_buffer, formatter, my_filter=None, filter_buffer=None):
  """Fetch EventObjects from storage and process and filter them.

  Args:
    output_buffer: output.EventBuffer object.
    formatter: An OutputFormatter.
    my_filter: A filter object.
    filter_buffer: A filter buffer used to store previously discarded
    events to store time slice history.
  """
  counter = collections.Counter()
  my_limit = getattr(my_filter, 'limit', 0)
  forward_entries = 0

  event_object = formatter.FetchEntry()
  while event_object:
    if my_filter:
      event_match = event_object
      if isinstance(event_object, plaso_storage_pb2.EventObject):
        event_match = event.EventObject()
        event_match.FromProto(event_object)

      if my_filter.Match(event_match):
        counter['Events Included'] += 1
        if filter_buffer:
          # Indicate we want forward buffering.
          forward_entries = 1
          # Empty the buffer.
          for event_in_buffer in filter_buffer.Flush():
            counter['Events Added From Slice'] += 1
            counter['Events Included'] += 1
            counter['Events Filtered Out'] -= 1
            output_buffer.Append(event_in_buffer)
        output_buffer.Append(event_object)
        if my_limit:
          if counter['Events Included'] == my_limit:
            break
      else:
        if filter_buffer and forward_entries:
          if forward_entries <= filter_buffer.size:
            output_buffer.Append(event_object)
            forward_entries += 1
            counter['Events Added From Slice'] += 1
            counter['Events Included'] += 1
          else:
            # Reached the max, don't include other entries.
            forward_entries = 0
            counter['Events Filtered Out'] += 1
        elif filter_buffer:
          filter_buffer.Append(event_object)
          counter['Events Filtered Out'] += 1
        else:
          counter['Events Filtered Out'] += 1
    else:
      counter['Events Included'] += 1
      output_buffer.Append(event_object)

    event_object = formatter.FetchEntry()

  if output_buffer.duplicate_counter:
    counter['Duplicate Removals'] = output_buffer.duplicate_counter

  if my_limit:
    counter['Limited By'] = my_limit
  return counter


def ParseStorage(my_args):
  """Open a storage file and parse through it."""
  filter_use = None
  filter_buffer = None
  counter = None
  if my_args.filter:
    filter_use = filters.GetFilter(my_args.filter)
    if not filter_use:
      logging.error(
          u'No filter found for the filter expression: {}'.format(
              my_args.filter))
      sys.exit(1)

    if my_args.slicer:
      # Check to see if we need to create a circular buffer.
      filter_buffer = bufferlib.CircularBuffer(my_args.slice_size)

  if my_args.slice:
    if my_args.timezone == 'UTC':
      zone = pytz.utc
    else:
      zone = pytz.timezone(my_args.timezone)

    timestamp = timelib.Timestamp.FromTimeString(my_args.slice, zone)

    # Convert number of minutes to microseconds.
    range_operator = my_args.slice_size * int(1e6) * 60
    # Set the time range.
    pfilter.TimeRangeCache.SetLowerTimestamp(timestamp - range_operator)
    pfilter.TimeRangeCache.SetUpperTimestamp(timestamp + range_operator)

    # Check if the filter has a date filter built in and warn if so.
    if my_args.filter:
      if 'date' in my_args.filter or 'timestamp' in my_args.filter:
        logging.warning(
            'You are trying to use both a "slice" and a date filter, the '
            'end results might not be what you want it to be... a small delay '
            'is introduced to allow you to read this message')
        time.sleep(5)

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
              store, my_args.write, my_args, filter_use)
    except IOError as e:
      logging.error(u'Error occured during output processing: %s', e)

    if not formatter:
      logging.error(u'Unable to proceed, output buffer not available.')
      sys.exit(1)

    with output_lib.EventBuffer(formatter, my_args.dedup) as output_buffer:
      counter = ProcessOutput(
          output_buffer, formatter, filter_use, filter_buffer)

    for information in store.GetStorageInformation():
      if hasattr(information, 'counter'):
        counter['Stored Events'] += information.counter['total']

  if filter_use and not counter['Limited By']:
    counter['Filter By Date'] = counter['Stored Events'] - counter[
        'Events Included'] - counter['Events Filtered Out']
  return counter


def ProcessArguments(arguments):
  """Process command line arguments."""
  parser = argparse.ArgumentParser(
      description=(
          u'PSORT - Application to read, filter and process '
          'output from a plaso storage file.'))

  parser.add_argument(
      '-d', '--debug', action='store_true', dest='debug', default=False,
      help='Fall back to debug shell if psort fails.')

  parser.add_argument(
      '-q', '--quiet', action='store_true', dest='quiet', default=False,
      help='Don\'t print out counter information after processing.')

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
      default='dynamic', help='Output format.  -o list to see loaded modules.')

  parser.add_argument(
      '-z', '--zone', metavar='TIMEZONE', default='UTC', dest='timezone',
      help='Timezone of output. list: "-z list"')

  parser.add_argument(
      '-w', '--write', metavar='OUTPUTFILE', dest='write',
      help='Output filename.  Defaults to stdout.')

  parser.add_argument(
      '--slice', metavar='DATE', dest='slice', type=str,
      default='', action='store', help=(
          'Create a time slice around a certain date. This parameter, if '
          'defined will display all events that happened X minutes before and '
          'after the defined date. X is controlled by the parameter '
          '--slice_size but defaults to 5 minutes.'))

  parser.add_argument(
      '--slicer', dest='slicer', action='store_true', default=False, help=(
          'Create a time slice around every filter match. This parameter, if '
          'defined will save all X events before and after a filter match has '
          'been made. X is defined by the --slice_size parameter.'))

  parser.add_argument(
      '--slice_size', dest='slice_size', type=int, default=5, action='store',
      help=(
          'Defines the slice size. In the case of a regular time slice it '
          'defines the number of minutes the slice size should be. In the '
          'case of the --slicer it determines the number of events before '
          'and after a filter match has been made that will be included in '
          'the result set. The default value is 5]. See --slice or --slicer '
          'for more details about this option.'))

  parser.add_argument(
      '-v', '--version', dest='version', action='version',
      version='log2timeline - psort version %s' % engine.__version__,
      help='Show the current version of psort.')

  parser.add_argument(
      'storagefile', metavar='PLASOFILE', default=None, nargs='?',
      type=unicode, help='Path to the Plaso storage file')

  parser.add_argument(
      'filter', nargs='?', action='store', metavar='FILTER', default=None,
      type=unicode, help=(
          'A filter that can be used to filter the dataset before it '
          'is written into storage. More information about the filters'
          ' and it\'s usage can be found here: http://plaso.kiddaland.'
          'net/usage/filters'))

  my_args = parser.parse_args(args=arguments)

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

  # Add local encoding settings.
  my_args.preferred_encoding = locale.getpreferredencoding()
  if my_args.preferred_encoding.lower() == 'ascii':
    logging.warning(
        u'The preferred encoding of your system is ASCII, which is not optimal '
        u'for the typically non-ASCII characters that need to be parsed and '
        u'processed. The tool will most likely crash and die, perhaps in a way '
        u'that may not be recoverable. A five second delay is introduced to '
        'give you time to cancel the runtime and reconfigure your preferred '
        'encoding, otherwise continue at own risk.')
    time.sleep(5)

  return my_args


def Main(my_args):
  """Start the tool."""
  try:
    counter = ParseStorage(my_args)

    if not my_args.quiet:
      logging.info(utils.FormatHeader('Counter'))
      for element, count in counter.most_common():
        logging.info(utils.FormatOutputString(element, count))
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
  my_options = ProcessArguments(sys.argv[1:])
  Main(my_options)
