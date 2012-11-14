#!/bin/bash
# A small script that submits a code for code review.
#
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

# Check usage
if [ $# -ne 1 ]
then
  echo "Wrong USAGE: `basename $0` REVIEWER"
  exit 1
fi

REVIEWER=$1

if [ ! -f "utils/common.sh" ]
then
  echo "Missing common functions, are you in the wrong directory?"
  exit 1
fi

. utils/common.sh

# First find all files that need linter
linter

if [ $? -ne 0 ]
then
  exit 1
fi

echo "Linter clear."

echo "Run tests."
./utils/run_tests.sh

if [ $? -ne 0 ]
then
  echo "Tests failed, not submitting for review."
  exit 2
fi

echo "Tests all came up clean. Send for review."
python utils/upload.py -y --cc log2timeline-dev@googlegroups.com -r $REVIEWER --send_mail
