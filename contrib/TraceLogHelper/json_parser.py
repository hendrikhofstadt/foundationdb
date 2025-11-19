#
# json_parser.py
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

import json
import random
from typing import Iterator, Optional, Callable, IO
from .event import Event, Severity


class JsonParser:
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
        Parse JSON trace log stream.

        Args:
            stream: Input stream to read from
            file: Source file name for tracking
            keep_original_element: Whether to keep original parsed element
            start_time: Filter events before this time
            end_time: Filter events after this time
            sampling_factor: Probability of including each event (0-1)
            non_fatal_error_message: Callback for non-fatal errors
        """
        for line in stream:
            try:
                line_str = line.decode('utf-8') if isinstance(line, bytes) else line
                root = json.loads(line_str)
                ev = JsonParser._parse_event(
                    root, file, keep_original_element,
                    start_time, end_time, sampling_factor
                )
                if ev is not None:
                    yield ev
            except Exception as e:
                raise Exception(f"Failed to parse JSON {line}") from e

    @staticmethod
    def _parse_event(
        event_dict: dict,
        file: str,
        keep_original_element: bool,
        start_time: float,
        end_time: float,
        sampling_factor: float
    ) -> Optional[Event]:
        """Parse a single JSON event."""
        if sampling_factor != 1.0 and JsonParser._random.random() > sampling_factor:
            return None

        # Check for rolled events
        track_latest_type = event_dict.get('TrackLatestType')
        rolled_event = track_latest_type == 'Rolled'
        time_key = 'OriginalTime' if rolled_event else 'Time'

        event_time = float(event_dict.get(time_key, 0))

        if event_time < start_time or event_time > end_time:
            return None

        # Build details dictionary, excluding standard fields
        excluded_fields = {'Type', 'Time', 'Machine', 'ID', 'Severity'}
        if rolled_event:
            excluded_fields.add('OriginalTime')

        details = {
            k: v for k, v in event_dict.items()
            if k not in excluded_fields
        }

        return Event(
            Severity=Severity(int(event_dict.get('Severity', 40))),
            Type=event_dict.get('Type', ''),
            Time=event_time,
            Machine=event_dict.get('Machine', ''),
            ID=event_dict.get('ID', '0'),
            TraceFile=file,
            DDetails=details,
            original=event_dict if keep_original_element else None
        )
