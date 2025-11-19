#
# trace_log_util.py
#
# This source file is part of the FoundationDB open source project
#
# Copyright 2013-2024 Apple Inc. and the FoundationDB project authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import Iterator, Dict
from .event import Event, TestPlan, Test, Severity


class TraceLogUtil:
    @staticmethod
    def identify_failed_test_plans(events: Iterator[Event]) -> Iterator[Event]:
        """
        Identify test plans that started but never completed.
        Yields all events, plus synthetic FailedTestPlan events for incomplete tests.
        """
        failed_plans: Dict[str, TestPlan] = {}

        for ev in events:
            if not isinstance(ev, TestPlan) or not ev.TestUID:
                yield ev
                continue

            if isinstance(ev, Test):
                # Test completed, remove from failed plans
                key = ev.TestUID + (ev.TraceFile or '')
                failed_plans.pop(key, None)
                # Also remove the -1.txt variant if this is -2.txt
                if ev.TraceFile and ev.TraceFile.endswith('-2.txt'):
                    alt_key = ev.TestUID + ev.TraceFile.split('-')[0] + '-1.txt'
                    failed_plans.pop(alt_key, None)
                yield ev
            else:
                # TestPlan started
                key = ev.TestUID + (ev.TraceFile or '')
                if key not in failed_plans:
                    failed_plans[key] = ev

        # Yield failed test plans
        for plan in failed_plans.values():
            yield Test(
                Type='FailedTestPlan',
                Time=plan.Time,
                Machine=plan.Machine,
                TestUID=plan.TestUID,
                TestFile=plan.TestFile,
                randomSeed=plan.randomSeed,
                Buggify=plan.Buggify,
                DeterminismCheck=plan.DeterminismCheck,
                OldBinary=plan.OldBinary,
                events=[
                    Event(
                        Severity=Severity.SevWarnAlways,
                        Type='TestNotSummarized',
                        Time=plan.Time,
                        Machine=plan.Machine
                    )
                ]
            )
