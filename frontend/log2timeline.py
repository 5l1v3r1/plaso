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
"""This file contains log2timeline, the friendly front-end to plaso."""

import argparse
import logging
import multiprocessing
import os
import sys

from plaso.lib import errors
from plaso.lib import engine
from plaso.lib import pfilter
from plaso.lib import putils

# The number of bytes in a MiB.
BYTES_IN_A_MIB = 1024 * 1024


def Main():
  """Start the tool."""
  multiprocessing.freeze_support()
  arg_parser = argparse.ArgumentParser(
      description=('log2timeline is the main frontend to the plaso backend, us'
                   'ed to collect and correlate events extracted from the file'
                   'system'),
      epilog='And that\'s how you build a timeline using log2timeline.')

  arg_parser.add_argument(
      '-z', '--zone', dest='tzone', action='store', type=str, default='UTC',
      help='Define the timezone of the IMAGE (not the output).')

  arg_parser.add_argument(
      '-p', '--preprocess', dest='preprocess', action='store_true',
      default=False, help=('Turn on pre-processing. Pre-processing is turned '
                           'on by default in image parsing'))

  arg_parser.add_argument(
      '--buffer-size', '--bs', dest='buffer_size', action='store', default=0,
      help='The buffer size for the output (defaults to 196MiB).')

  arg_parser.add_argument(
      '--workers', dest='workers', action='store', type=int, default=0,
      help=('The number of worker threads [defaults to available system '
            'CPU\'s minus three].'))

  arg_parser.add_argument(
      '-i', '--image', dest='image', action='store_true', default=False,
      help='Indicates that this is an image instead of a regular file.')

  arg_parser.add_argument(
      '--vss', dest='parse_vss', action='store_true', default=False,
      help=('Collect data from VSS. Off by default, this should be used on Wi'
            'ndows systems that have active VSS (Volume Shadow Copies) that n'
            'eed to be included in the analysis.'))

  arg_parser.add_argument(
      '--vss-stores', dest='vss_stores', action='store', type=str, default=None,
      help=('List of stores to parse, format is X..Y where X and Y are intege'
            'rs, or a list of entries separated with a comma, eg: X,Y,Z or a '
            'list of ranges and entries, eg: X,Y-Z,G,H-J.'))

  arg_parser.add_argument(
      '--single-thread', dest='single_thread', action='store_true',
      default=False,
      help='Indicate that the tool should run in a single thread.')

  arg_parser.add_argument(
      '-f', '--file_filter', dest='file_filter', action='store', type=str,
      default=None, help=('List of files to include for targeted collection of'
                          ' files to parse, one line per file path, setup is '
                          '/path|file - where each element can contain either'
                          ' a variable set in the preprocessing stage or a '
                          'regular expression'))

  arg_parser.add_argument(
      '--scan-archives', dest='open_files', action='store_true', default=False,
      help=('Indicate that the tool should try to open files to extract embedd'
            'ed files within them, for instance to extract files from compress'
            'ed containers, etc.'))

  arg_parser.add_argument(
      '--noscan-archives', dest='open_files', action='store_false',
      help=('Indicate that the tool should NOT try to '
            'open files to extract embedded files within them.'))

  arg_parser.add_argument(
      '-o', '--offset', dest='image_offset', action='store', default=0,
      type=int, help=('The sector offset to the image in sector sizes (512'
                      ' bytes).'))

  arg_parser.add_argument(
      '--ob', '--offset_bytes', dest='image_offset_bytes', action='store',
      default=0, type=int, help='The bytes offset to the image')

  arg_parser.add_argument(
      '-v', '--version', action='version',
      version='log2timeline - plaso backend %s' % engine.__version__,
      help='Show the current version of the backend.')

  arg_parser.add_argument(
      '--info', dest='info', action='store_true', default=False,
      help='Print out information about supported plugins and parsers.')

  arg_parser.add_argument(
      '-d', '--debug', dest='debug', action='store_true', default=False,
      help='Turn on debug information in the tool.')

  arg_parser.add_argument(
      'output', action='store', metavar='STORAGE_FILE', nargs='?',
      help=('The path to the output file, if the file exists it will get '
            'appended to.'))

  arg_parser.add_argument(
      'filename', action='store', metavar='FILENAME_OR_MOUNT_POINT',
      nargs='?', help=(
          'The path to the file, directory, image file or mount point that the'
          ' tool should parse. If this is a directory it will recursively go '
          'through it, same with an image file.'))

  arg_parser.add_argument(
      'filter', action='store', metavar='FILTER', nargs='?', default=None,
      help=('A filter that can be used to filter the dataset before it '
            'is written into storage. More information about the filters'
            ' and it\'s usage can be found here: http://plaso.kiddaland.'
            'net/usage/filters'))

  options = arg_parser.parse_args()

  if options.tzone == 'list':
    print '=' * 40
    print '       ZONES'
    print '-' * 40
    for zone in engine.GetTimeZoneList():
      print '  %s' % zone
    print '=' * 40
    sys.exit(0)

  if options.info:
    # Import all plugins and parsers to print out the necessary information.
    # This is not import at top since this is only required if this parameter
    # is set, otherwise these libraries get imported in their respected
    # locations.
    from plaso import parsers
    from plaso import registry
    from plaso import output as outputs
    from plaso.lib import output
    from plaso.lib import win_registry_interface

    print '{:=^80}'.format(' log2timeline/plaso information. ')

    print '\n{:*^80}'.format(' Versions ')
    print FormatOutputString('plaso engine', engine.__version__)
    print FormatOutputString('python', sys.version)
    # TODO: Add here a list of all the parsing library versions.

    print '\n{:*^80}'.format(' Parsers ')
    for parser in sorted(putils.FindAllParsers()['all']):
      doc_string, _, _ = parser.__doc__.partition('\n')
      print FormatOutputString(parser.parser_name, doc_string)

    print '\n{:*^80}'.format(' Output Modules ')
    for name, description in sorted(output.ListOutputFormatters()):
      print FormatOutputString(name, description)

    print '\n{:*^80}'.format(' Registry Plugins ')
    reg_plugins = win_registry_interface.GetRegistryPlugins()
    a_plugin = reg_plugins.GetAllKeyPlugins()[0]

    for plugin, obj in sorted(a_plugin.classes.items()):
      doc_string, _, _ = obj.__doc__.partition('\n')
      print FormatOutputString(plugin, doc_string)

    sys.exit(0)

  # This frontend only deals with local setup of the tool.
  options.local = True

  format_str = '[%(levelname)s] (%(processName)-10s) %(message)s'
  if options.debug:
    logging.basicConfig(level=logging.DEBUG, format=format_str)
  else:
    logging.basicConfig(level=logging.INFO, format=format_str)

  if not options.output:
    arg_parser.print_help()
    print ''
    arg_parser.print_usage()
    print ''
    logging.error(
        'Wrong usage: need to define an output.')
    sys.exit(1)

  if not options.filename:
    arg_parser.print_help()
    print ''
    arg_parser.print_usage()
    print ''
    logging.error(u'No input file supplied.')
    sys.exit(1)

  options.recursive = os.path.isdir(options.filename)

  if options.filter and not pfilter.GetMatcher(options.filter):
    logging.error(
        (u'Filter error, unable to proceed. There is a problem with your '
         'filter: %s'), options.filter)
    sys.exit(1)

  if options.image_offset or options.image_offset_bytes:
    options.image = True

  if options.image:
    options.preprocess = True

  if options.buffer_size:
    if options.buffer_size[-1].lower() == 'm':
      options.buffer_size = int(options.buffer_size[:-1]) * BYTES_IN_A_MIB
    else:
      try:
        options.buffer_size = int(options.buffer_size)
      except ValueError:
        logging.error(('Wrong usage: Buffer size needs to be an integer or'
                       ' end with M'))
        sys.exit(1)

  if options.vss_stores:
    options.parse_vss = True
    stores = []
    try:
      for store in options.vss_stores.split(','):
        if '..' in store:
          begin, end = store.split('..')
          for nr in range(int(begin), int(end)):
            if nr not in stores:
              stores.append(nr)
        else:
          if int(store) not in stores:
            stores.append(int(store))
    except ValueError:
      arg_parser.print_help()
      print ''
      logging.error('VSS store range is wrongly formed.')
      sys.exit(1)

    options.vss_stores = sorted(stores)

  if options.parse_vss:
    options.image = True
    options.preprocess = True

  if options.file_filter:
    if not os.path.isfile(options.file_filter):
      logging.error(
          u'Error with collection filter, file: {} does not exist.'.format(
              options.file_filter))
      sys.exit(1)

  if options.workers < 1:
    # One worker for each "available" CPU (minus other processes).
    cpus = multiprocessing.cpu_count()
    options.workers = cpus
    if cpus > 3:
      options.workers -= 3

  try:
    l2t = engine.Engine(options)
  except errors.BadConfigOption as e:
    logging.warning('Unable to run tool, bad configuration: %s', e)
    sys.exit(1)

  try:
    l2t.Start()
    logging.info('Run completed.')
  except KeyboardInterrupt:
    logging.warning('Tool being killed.')
    l2t.StopThreads()


def FormatOutputString(name, description):
  """Return a formatted string ready for output."""
  if len(description) < 52:
    return u'{:>25s} : {}'.format(name, description)

  # Split each word up in the description.
  words = description.split()
  # We've got two lines.
  lengths = []
  counter = 0
  for word in words:
    counter += len(word) + 1
    lengths.append(counter)

  index = 0
  for length_index, length in enumerate(lengths):
    if length < 53:
      index = length_index
  index += 1
  ret = []
  ret.append(u'{:>25s} : {}'.format(name, u' '.join(words[:index])))
  ret.append(u'{: <28}{}'.format('', u' '.join(words[index:])))

  return u'\n'.join(ret)


if __name__ == '__main__':
  Main()
