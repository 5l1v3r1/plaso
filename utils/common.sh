#!/bin/bash
# A small script that contains common functions for code review checks.
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

linter()
{
  # TODO fix this for newly added files
  AWK_SCRIPT="if ($1 == 'M') { print $2; } else if ($1 == 'RM') { print $4; }";

  # First find all files that need linter
  echo "Run through pychecker."
  git status -s | grep -v "^?" | awk "{ ${AWK_SCRIPT} }" | grep -v "utils/upload.py" | grep "\.py$" | while read lint_file
  do
    echo "  -- Checking ${lint_file} --"
    if [ "${lint_file}" == "setup.py" ]
    then
      echo "Skipping setup.py"
      continue
    fi

    if [ `echo ${lint_file} | tail -c8` == "_pb2.py" ]
    then
      echo "Skipping compiled protobufs: ${lint_file}"
      continue
    fi

    pychecker -Q -f --only -6  "$lint_file"

    if [ $? -ne 0 ]
    then
      echo "Fix linter errors before proceeding."
      exit 1
    fi

    # Run through "line width" checker since that is not covered by the linter.
    python utils/linecheck.py "$lint_file"

    if [ $? -ne 0 ]
    then
      echo "Fix line width errors before proceeding."
      exit 1
    fi
  done

  if [ $? -ne 0 ]
  then
    exit 1
  fi
}
