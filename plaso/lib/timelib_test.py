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
"""This file contains a unit test for the timelib in Plaso."""
import datetime
import unittest

from plaso.lib import timelib
import pytz


class TimeLibUnitTest(unittest.TestCase):
  """A unit test for the timelib."""

  def testCocoaTime(self):
    """Test the processing of timestamps created by Cocoa."""
    # date -u -d "Mon Jul  8 21:30:45 UTC 2013" +"%s.%N" = 1373319045.000000000
    self.assertEquals(timelib.Timestamp.FromCocoaTime(395011845),
                      1373319045000000)
    # date -u -d "Fri Jul 12 20:19:02 UTC 2013" +"%s.%N" = 1373660342.000000000
    self.assertEquals(timelib.Timestamp.FromCocoaTime(395353142),
                      1373660342000000)

    # date -u -d "Mon Jul  8 16:27:49 UTC 2013" +"%s.%N" = 1373300869.000000000
    self.assertEquals(timelib.Timestamp.FromCocoaTime(394993669),
                      1373300869000000)

  def testHFSTimes(self):
    # date -d "Thu Aug  1 15:25:28 EDT 2013" +"%s.%N" = 1375385128.000000000
    # EDT is UTC-4, so 1375385128 - (4*60*60) = 1375370728
    # 1375370728 + 2082844800 = 3458244328
    self.assertEquals(timelib.Timestamp.FromHfsTime(
        3458215528, pytz.timezone('EST5EDT'), True), 1375385128000000)

    # date -d "Thu Aug  1 15:25:28 UTC 2013" +"%s.%N" = 1375370728.000000000
    # 1375370728 + 2082844800 = 3458215528
    self.assertEquals(timelib.Timestamp.FromHfsPlusTime(
        3458215528), 1375370728000000)

    # date -d "Feb  29 15:25:28 UTC 2012" +"%s.%N" = 1330529128.000000000
    # 1330529128 + 2082844800 = 3413373928
    self.assertEquals(timelib.Timestamp.FromHfsPlusTime(
        3413373928), 1330529128000000)


  def testTimestampIsLeapYear(self):
    """Test the is leap year check."""
    self.assertEquals(timelib.Timestamp.IsLeapYear(2012), True)
    self.assertEquals(timelib.Timestamp.IsLeapYear(2013), False)
    self.assertEquals(timelib.Timestamp.IsLeapYear(2000), True)
    self.assertEquals(timelib.Timestamp.IsLeapYear(1900), False)

  def testTimestampDaysInMonth(self):
    """Test the days in month function."""
    self.assertEquals(timelib.Timestamp.DaysInMonth(0, 2013), 31)
    self.assertEquals(timelib.Timestamp.DaysInMonth(1, 2013), 28)
    self.assertEquals(timelib.Timestamp.DaysInMonth(1, 2012), 29)
    self.assertEquals(timelib.Timestamp.DaysInMonth(2, 2013), 31)
    self.assertEquals(timelib.Timestamp.DaysInMonth(3, 2013), 30)
    self.assertEquals(timelib.Timestamp.DaysInMonth(4, 2013), 31)
    self.assertEquals(timelib.Timestamp.DaysInMonth(5, 2013), 30)
    self.assertEquals(timelib.Timestamp.DaysInMonth(6, 2013), 31)
    self.assertEquals(timelib.Timestamp.DaysInMonth(7, 2013), 31)
    self.assertEquals(timelib.Timestamp.DaysInMonth(8, 2013), 30)
    self.assertEquals(timelib.Timestamp.DaysInMonth(9, 2013), 31)
    self.assertEquals(timelib.Timestamp.DaysInMonth(10, 2013), 30)
    self.assertEquals(timelib.Timestamp.DaysInMonth(11, 2013), 31)

  def testTimestampDaysInYear(self):
    """Test the days in year function."""
    self.assertEquals(timelib.Timestamp.DaysInYear(2013), 365)
    self.assertEquals(timelib.Timestamp.DaysInYear(2012), 366)

  def testTimestampDayOfYear(self):
    """Test the day of year function."""
    self.assertEquals(timelib.Timestamp.DayOfYear(0, 0, 2013), 0)
    self.assertEquals(timelib.Timestamp.DayOfYear(0, 2, 2013), 31 + 28)
    self.assertEquals(timelib.Timestamp.DayOfYear(0, 2, 2012), 31 + 29)
    self.assertEquals(timelib.Timestamp.DayOfYear(0, 11, 2013),
                      31 + 28 + 31 + 30 + 31 + 30 + 31 + 31 + 30 + 31 + 30)

  def testTimestampFromFatDateTime(self):
    """Test the FAT date time conversion."""
    # Aug 12, 2010 21:06:32
    fat_date_time = 0xa8d03d0c
    # date -u -d"Aug 12, 2010 21:06:32" +"%s"
    timestamp = 1281647192 * 1000000
    self.assertEquals(
        timelib.Timestamp.FromFatDateTime(fat_date_time), timestamp)

    # Invalid number of seconds.
    fat_date_time = (0xa8d03d0c & ~(0x1f << 16)) | ((30 & 0x1f) << 16)
    self.assertEquals(
        timelib.Timestamp.FromFatDateTime(fat_date_time), 0)

    # Invalid number of minutes.
    fat_date_time = (0xa8d03d0c & ~(0x3f << 21)) | ((60 & 0x3f) << 21)
    self.assertEquals(
        timelib.Timestamp.FromFatDateTime(fat_date_time), 0)

    # Invalid number of hours.
    fat_date_time = (0xa8d03d0c & ~(0x1f << 27)) | ((24 & 0x1f) << 27)
    self.assertEquals(
        timelib.Timestamp.FromFatDateTime(fat_date_time), 0)

    # Invalid day of month.
    fat_date_time = (0xa8d03d0c & ~(0x1f)) | (32 & 0x1f)
    self.assertEquals(
        timelib.Timestamp.FromFatDateTime(fat_date_time), 0)

    # Invalid month.
    fat_date_time = (0xa8d03d0c & ~(0x0f << 5)) | ((13 & 0x0f) << 5)
    self.assertEquals(
        timelib.Timestamp.FromFatDateTime(fat_date_time), 0)

  def testTimestampFromWebKitTime(self):
    """Test the WebKit time conversion."""
    # Aug 12, 2010 21:06:31.546875000
    # date -u -d"Aug 12, 2010 21:06:31.546875000" +"%s.%N"
    webkit_time = 0x2dec3d061a9bfb
    timestamp = (1281647191 * 1000000) + int(546875000 / 1000)
    self.assertEquals(timelib.Timestamp.FromWebKitTime(webkit_time), timestamp)

    # Jan 2, 1601 00:00:00.000000000
    # date -u -d"Jan 2, 1601 00:00:00.000000000" +"%s.%N"
    webkit_time = 86400 * 1000000
    timestamp = (-11644387200 * 1000000)
    self.assertEquals(timelib.Timestamp.FromWebKitTime(webkit_time), timestamp)

    # WebKit time that exceeds lower bound.
    webkit_time = -((1 << 63L) - 1)
    self.assertEquals(timelib.Timestamp.FromWebKitTime(webkit_time), 0)

  def testTimestampFromFiletime(self):
    """Test the FILETIME conversion."""
    # Aug 12, 2010 21:06:31.546875000
    # date -u -d"Aug 12, 2010 21:06:31.546875000" +"%s.%N"
    filetime = 0x01cb3a623d0a17ce
    timestamp = (1281647191 * 1000000) + int(546875000 / 1000)
    self.assertEquals(timelib.Timestamp.FromFiletime(filetime), timestamp)

    # Jan 2, 1601 00:00:00.000000000
    # date -u -d"Jan 2, 1601 00:00:00.000000000" +"%s.%N"
    filetime = 86400 * 10000000
    timestamp = (-11644387200 * 1000000)
    self.assertEquals(timelib.Timestamp.FromFiletime(filetime), timestamp)

    # FILETIME that exceeds lower bound.
    filetime = -1
    self.assertEquals(timelib.Timestamp.FromFiletime(filetime), 0)

  def testTimestampFromPosixTIme(self):
    """Test the POSIX time conversion."""
    # Aug 12, 2010 21:06:31.546875000
    # date -u -d"Aug 12, 2010 21:06:31" +"%s"
    posix_time = 1281647191
    timestamp = 1281647191 * 1000000
    self.assertEquals(timelib.Timestamp.FromPosixTime(posix_time), timestamp)

    # Feb 12, 1966 12:14:42
    # date -u -d"Feb 12, 1966 12:14:42" +"%s"
    posix_time = -122557518
    timestamp = -122557518 * 1000000
    self.assertEquals(timelib.Timestamp.FromPosixTime(posix_time), timestamp)

    # POSIX time that exceeds upper bound.
    posix_time = 9223372036855
    self.assertEquals(timelib.Timestamp.FromPosixTime(posix_time), 0)

    # POSIX time that exceeds lower bound.
    posix_time = -9223372036855
    self.assertEquals(timelib.Timestamp.FromPosixTime(posix_time), 0)

  def testMonthDict(self):
    """Test the month dict, both inside and outside of scope."""
    self.assertEquals(timelib.MONTH_DICT['nov'], 11)
    self.assertEquals(timelib.MONTH_DICT['jan'], 1)
    self.assertEquals(timelib.MONTH_DICT['may'], 5)

    month = timelib.MONTH_DICT.get('doesnotexist')
    self.assertEquals(month, None)

  def testLocaltimeToUTC(self):
    """Test the localtime to UTC conversion."""
    timezone = pytz.timezone('CET')

    # date -u -d"Jan 1, 2013 01:00:00" +"%s.%N"
    local_timestamp = 1357002000 * 1000000
    # date -u -d"Jan 1, 2013 00:00:00" +"%s.%N"
    expected_timestamp = 1356998400 * 1000000
    self.assertEquals(
        timelib.Timestamp.LocaltimeToUTC(local_timestamp, timezone),
        expected_timestamp)

    # date -u -d"Jul 1, 2013 02:00:00" +"%s.%N"
    local_timestamp = 1372644000 * 1000000
    # date -u -d"Jul 1, 2013 00:00:00" +"%s.%N"
    expected_timestamp = 1372636800 * 1000000
    self.assertEquals(
        timelib.Timestamp.LocaltimeToUTC(local_timestamp, timezone),
        expected_timestamp)

    # In the local timezone this is a non-existent timestamp.
    # date -u -d"Mar 31, 2013 02:00:00" +"%s.%N"
    local_timestamp = 1364695200 * 1000000

    with self.assertRaises(pytz.NonExistentTimeError):
      timelib.Timestamp.LocaltimeToUTC(local_timestamp, timezone, is_dst=None)

    # date -u -d"Mar 31, 2013 00:00:00" +"%s.%N"
    expected_timestamp = 1364688000 * 1000000
    self.assertEquals(
        timelib.Timestamp.LocaltimeToUTC(
            local_timestamp, timezone, is_dst=True),
        expected_timestamp)

    # date -u -d"Mar 31, 2013 01:00:00" +"%s.%N"
    expected_timestamp = 1364691600 * 1000000
    self.assertEquals(
        timelib.Timestamp.LocaltimeToUTC(
            local_timestamp, timezone, is_dst=False),
        expected_timestamp)

    # In the local timezone this is an ambiguous timestamp.
    # date -u -d"Oct 27, 2013 02:30:00" +"%s.%N"
    local_timestamp = 1382841000 * 1000000

    with self.assertRaises(pytz.AmbiguousTimeError):
      timelib.Timestamp.LocaltimeToUTC(local_timestamp, timezone, is_dst=None)

    # date -u -d"Oct 27, 2013 00:30:00" +"%s.%N"
    expected_timestamp = 1382833800 * 1000000
    self.assertEquals(
        timelib.Timestamp.LocaltimeToUTC(
            local_timestamp, timezone, is_dst=True),
        expected_timestamp)

    # date -u -d"Oct 27, 2013 01:30:00" +"%s.%N"
    expected_timestamp = 1382837400 * 1000000
    self.assertEquals(
        timelib.Timestamp.LocaltimeToUTC(local_timestamp, timezone),
        expected_timestamp)

    # Use the UTC timezone.
    self.assertEquals(
        timelib.Timestamp.LocaltimeToUTC(local_timestamp, pytz.utc),
        local_timestamp)

    # Use a timezone in the Western Hemisphere.
    timezone = pytz.timezone('EST')

    # date -u -d"Jan 1, 2013 00:00:00" +"%s.%N"
    local_timestamp = 1356998400 * 1000000
    # date -u -d"Jan 1, 2013 05:00:00" +"%s.%N"
    expected_timestamp = 1357016400 * 1000000
    self.assertEquals(
        timelib.Timestamp.LocaltimeToUTC(local_timestamp, timezone),
        expected_timestamp)

  def testCopyToDatetime(self):
    """Test the copy to datetime object."""
    timezone = pytz.timezone('CET')

    # date -u -d"2013-03-14 20:20:08.850041+00:00" +"%s.%N"
    timestamp = (1363292408 * 1000000) + (850041000 / 1000)

    self.assertEquals(
        timelib.Timestamp.CopyToDatetime(timestamp, timezone),
        datetime.datetime(2013, 3, 14, 21, 20, 8, 850041, tzinfo=timezone))

  def testTimestampFromTimeParts(self):
    """Test the FromTimeParts function."""

    # Tue Jun 25 22:19:46 PDT 2013.
    timestamp_pdt = timelib.Timestamp.FromTimeParts(
        2013, 6, 25, 22, 19, 46, 0, pytz.timezone('PST8PDT'))
    # Wed Jun 26 05:19:46 UTC 2013.
    timestamp_utc = timelib.Timestamp.FromTimeParts(
        2013, 6, 26, 5, 19, 46)
    # Wed Jun 26 05:19:46 UTC 2013 (with microsecond precision).
    timestamp_utc_micro = timelib.Timestamp.FromTimeParts(
        2013, 6, 26, 5, 19, 46, 542)

    self.assertEquals(timestamp_pdt, 1372223986 * int(1e6))
    self.assertEquals(timestamp_utc, 1372223986 * int(1e6))
    self.assertEquals(timestamp_utc_micro, 1372223986 * int(1e6) + 542)

  def testStringToDatetime(self):
    """Test the StringToDatetime function."""
    zone = pytz.timezone('EST')
    timestring = '12-15-1984 05:13:00'
    expected = 471953580
    self.CompareTimestamps(expected, timestring, zone)

    # Swap day and month.
    zone = pytz.timezone('EST')
    # This is Oct 12th 1984, since we have DD-MM-YYYY.
    timestring = '12-10-1984 05:13:00'
    # date -u -d "Oct 12, 1984 05:13:00-05:00" +"%s"
    expected = 466423980
    self.CompareTimestamps(expected, timestring, zone, True)

    timestring = '12-15-1984 10:13:00Z'
    expected = 471953580
    self.CompareTimestamps(expected, timestring, zone)

    timestring = '15/12/1984 10:13:00Z'
    expected = 471953580
    self.CompareTimestamps(expected, timestring, zone)

    timestring = '15-12-84 10:13:00Z'
    expected = 471953580
    self.CompareTimestamps(expected, timestring, zone)

    timestring = '15-12-84 10:13:00-04'
    expected = 471967980
    self.CompareTimestamps(expected, timestring, zone)

    timestring = 'thisisnotadatetime'
    expected = 0
    self.CompareTimestamps(expected, timestring, zone)

    zone = pytz.timezone('America/Chicago')
    timestring = '12-15-1984 05:13:00'
    expected = 471957180
    self.CompareTimestamps(expected, timestring, zone)

    zone = pytz.timezone('US/Pacific')
    timestring = '12-15-1984 05:13:00'
    expected = 471964380
    self.CompareTimestamps(expected, timestring, zone)

  def CompareTimestamps(self, expected, timestring,
                        timezone=pytz.utc, dayfirst=False):
    """Compare epoch values derived from StringToDatetime.

    Args:
      expected: Excpected integer value of timestring.
      timestring: A string formatted as a timestamp.
      timezone: The timezone (pytz.timezone) object.
      dayfirst: Change precedence of day vs. month.
    Returns:
      A result object.

    """
    dt = timelib.StringToDatetime(timestring, timezone, dayfirst)
    calculated = timelib.Timetuple2Timestamp(dt.timetuple())
    self.assertEquals(calculated, expected)


if __name__ == '__main__':
  unittest.main()
