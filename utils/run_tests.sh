#!/bin/bash
# A small script that runs all tests
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

EXIT_FAILURE=1;
EXIT_SUCCESS=0;

TEST_FILES=`find . -name "*_test.py" | grep -v "\/build\/"`;

# TODO: add an ordering of tests, e.g. lib first.
for TEST_FILE in ${TEST_FILES};
do
  # TODO: black listing this test for now.
  if [ "${TEST_FILE}" = "./frontend/psort_test.py" ];
  then
    continue;
  fi
  # TODO: disabled since this test is flaky at the moment.
  # Upcoming changes to fix this so that the test can be re-enabled.
  if [ "${TEST_FILE}" = "./parsers/lnk_test.py" ];
  then
    continue;
  fi

  echo "---+ ${TEST_FILE} +---"
  PYTHONPATH=../ /usr/bin/python ${TEST_FILE}

  if [ $? -ne 0 ]
  then
    echo "TEST FAILED: ${TEST_FILE}.";
    echo "";
    echo "Stopping further testing.";
    echo "";
    exit ${EXIT_FAILURE};
  fi
  echo "";
done

exit ${EXIT_SUCCESS};

