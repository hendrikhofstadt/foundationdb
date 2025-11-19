#
# xml_parser.py
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

import random
import xml.etree.ElementTree as ET
from typing import Iterator, Optional, Callable, IO
from .event import Event, TestPlan, Test, Severity


class XmlParser:
    _random = random.Random()

    @staticmethod
    def parse(
        stream: IO[bytes],
        file: str,
        keep_original_element: bool = False,
        start_time: float = -1.0,
        end_time: float = float('inf'),
        sampling_factor: float = 1.0,
        non_fatal_error_message: Optional[Callable[[str], None]] = None
    ) -> Iterator[Event]:
        """
        Parse XML trace log stream.

        Args:
            stream: Input stream to read from
            file: Source file name for tracking
            keep_original_element: Whether to keep original parsed element
            start_time: Filter events before this time
            end_time: Filter events after this time
            sampling_factor: Probability of including each event (0-1)
            non_fatal_error_message: Callback for non-fatal errors
        """
        try:
            # Parse XML iteratively to handle large files
            for event, elem in ET.iterparse(stream, events=('end',)):
                if elem.tag == 'Trace':
                    continue

                ev = None
                try:
                    if elem.tag == 'Event':
                        ev = XmlParser._parse_event(
                            elem, file, keep_original_element,
                            start_time, end_time, sampling_factor
                        )
                    elif elem.tag == 'Test':
                        ev = XmlParser._parse_test(elem, file, keep_original_element)
                    elif elem.tag == 'TestPlan':
                        ev = XmlParser._parse_test_plan(elem, file, keep_original_element)
                except Exception as e:
                    raise Exception(f"Failed to parse XML {ET.tostring(elem)}") from e

                if ev is not None:
                    yield ev

                # Clear element to free memory
                elem.clear()

        except Exception as e:
            if non_fatal_error_message:
                non_fatal_error_message(str(e))

    @staticmethod
    def _get_attr(elem: ET.Element, name: str, default: str = '') -> str:
        """Get attribute value with default."""
        return elem.get(name, default)

    @staticmethod
    def _parse_event(
        elem: ET.Element,
        file: str,
        keep_original_element: bool,
        start_time: float,
        end_time: float,
        sampling_factor: float
    ) -> Optional[Event]:
        """Parse an Event element."""
        if sampling_factor != 1.0 and XmlParser._random.random() > sampling_factor:
            return None

        # Check for rolled events
        track_latest_attr = elem.get('TrackLatestType')
        rolled_event = track_latest_attr == 'Rolled'
        time_attr = 'OriginalTime' if rolled_event else 'Time'

        event_time_str = elem.get(time_attr)
        if not event_time_str:
            return None
        event_time = float(event_time_str)

        if event_time < start_time or event_time > end_time:
            return None

        # Build details dictionary, excluding standard fields
        excluded_attrs = {'Type', 'Time', 'Machine', 'ID', 'Severity'}
        if rolled_event:
            excluded_attrs.add('OriginalTime')

        details = {
            k: v for k, v in elem.attrib.items()
            if k not in excluded_attrs
        }

        return Event(
            Severity=Severity(int(elem.get('Severity', '40'))),
            Type=elem.get('Type', ''),
            Time=event_time,
            Machine=elem.get('Machine', ''),
            ID=elem.get('ID', '0'),
            TraceFile=file,
            DDetails=details,
            original=elem if keep_original_element else None
        )

    @staticmethod
    def _parse_test_plan(
        elem: ET.Element,
        file: str,
        keep_original_element: bool
    ) -> TestPlan:
        """Parse a TestPlan element."""
        time = float(XmlParser._get_attr(elem, 'Time', '0'))
        machine = XmlParser._get_attr(elem, 'Machine', '')

        return TestPlan(
            TraceFile=file,
            Type='TestPlan',
            Time=time,
            Machine=machine,
            TestUID=XmlParser._get_attr(elem, 'TestUID', ''),
            TestFile=XmlParser._get_attr(elem, 'TestFile', ''),
            randomSeed=int(XmlParser._get_attr(elem, 'RandomSeed', '0')),
            Buggify=XmlParser._get_attr(elem, 'BuggifyEnabled', '1') != '0',
            DeterminismCheck=XmlParser._get_attr(elem, 'DeterminismCheck', '1') != '0',
            OldBinary=XmlParser._get_attr(elem, 'OldBinary', ''),
            original=elem if keep_original_element else None
        )

    @staticmethod
    def _parse_test(
        elem: ET.Element,
        file: str,
        keep_original_element: bool
    ) -> Test:
        """Parse a Test element."""
        time = float(XmlParser._get_attr(elem, 'Time', '0'))
        machine = XmlParser._get_attr(elem, 'Machine', '')

        # Parse child events
        events = []
        for child in elem:
            excluded_attrs = {'Type', 'Time', 'Machine', 'Severity'}
            details = {
                k: v for k, v in child.attrib.items()
                if k not in excluded_attrs
            }
            events.append(Event(
                Severity=Severity(int(child.get('Severity', '0'))),
                Type=child.tag,
                Time=time,
                Machine=machine,
                DDetails=details
            ))

        return Test(
            TraceFile=file,
            Type='Test',
            Time=time,
            Machine=machine,
            TestUID=XmlParser._get_attr(elem, 'TestUID', ''),
            TestFile=XmlParser._get_attr(elem, 'TestFile', ''),
            SourceVersion=XmlParser._get_attr(elem, 'SourceVersion', ''),
            ok=XmlParser._get_attr(elem, 'OK', 'false').lower() == 'true',
            randomSeed=int(XmlParser._get_attr(elem, 'RandomSeed', '0')),
            randomUnseed=int(XmlParser._get_attr(elem, 'RandomUnseed', '0')),
            SimElapsedTime=float(XmlParser._get_attr(elem, 'SimElapsedTime', '0')),
            RealElapsedTime=float(XmlParser._get_attr(elem, 'RealElapsedTime', '0')),
            passed=int(XmlParser._get_attr(elem, 'Passed', '0')),
            failed=int(XmlParser._get_attr(elem, 'Failed', '0')),
            peakMemUsage=int(XmlParser._get_attr(elem, 'PeakMemory', '0')),
            Buggify=XmlParser._get_attr(elem, 'BuggifyEnabled', '1') != '0',
            DeterminismCheck=XmlParser._get_attr(elem, 'DeterminismCheck', '1') != '0',
            OldBinary=XmlParser._get_attr(elem, 'OldBinary', ''),
            original=elem if keep_original_element else None,
            events=events
        )
