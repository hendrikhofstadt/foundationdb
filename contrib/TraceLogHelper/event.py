#
# event.py
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

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, Any, Optional, List


class Severity(IntEnum):
    SevDebug = 5
    SevInfo = 10
    SevWarn = 20
    SevWarnAlways = 30
    SevError = 40


@dataclass
class Event:
    Time: float = 0.0
    Severity: Severity = Severity.SevError
    Type: str = ''
    Machine: str = ''
    ID: str = ''
    TraceFile: Optional[str] = None
    original: Optional[Any] = None
    DDetails: Dict[str, Any] = field(default_factory=dict)

    @property
    def WorkerDesc(self) -> str:
        return f"{self.Machine} {self.ID}"

    @property
    def Details(self) -> Dict[str, Any]:
        """Dynamic access to details."""
        return self.DDetails

    def shallow_copy(self) -> 'Event':
        """Create a shallow copy of the event."""
        return Event(
            Time=self.Time,
            Severity=self.Severity,
            Type=self.Type,
            Machine=self.Machine,
            ID=self.ID,
            TraceFile=self.TraceFile,
            original=self.original,
            DDetails=self.DDetails.copy()
        )

    def format_test_error(self, include_details: bool = False) -> str:
        """Format error message for test failures."""
        s = self.Type
        details = self.DDetails

        if self.Type == "InternalError":
            s = f"{self.Type} {details.get('File', '')} {details.get('Line', '')}"
        elif self.Type == "TestFailure":
            s = f"{self.Type} {details.get('Reason', '')}"
        elif self.Type == "ValgrindError":
            s = f"{self.Type} {details.get('What', '')}"
        elif self.Type == "ExitCode":
            code = int(details.get('Code', 0))
            s = f"{self.Type} 0x{code:x}"
        elif self.Type == "StdErrOutput":
            s = f"{self.Type}: {details.get('Output', '')}"
        elif self.Type == "BTreeIntegrityCheck":
            s = f"{self.Type}: {details.get('ErrorDetail', '')}"

        if 'Error' in details:
            s += f" {details['Error']}"
        if 'WinErrorCode' in details:
            s += f" {details['WinErrorCode']}"
        if 'LinuxErrorCode' in details:
            s += f" {details['LinuxErrorCode']}"
        if 'Status' in details:
            s += f" Status={details['Status']}"
        if 'In' in details:
            s += f" In {details['In']}"
        if 'SQLiteError' in details:
            s += f" SQLiteError={details['SQLiteError']}({details.get('SQLiteErrorCode', '')})"
        if 'Details' in details and include_details:
            s += f": {details['Details']}"

        return s


@dataclass
class TestPlan(Event):
    TestUID: str = ''
    TestFile: str = ''
    randomSeed: int = 0
    Buggify: bool = False
    DeterminismCheck: bool = False
    OldBinary: str = ''


@dataclass
class Test(TestPlan):
    SourceVersion: str = ''
    SimElapsedTime: float = 0.0
    RealElapsedTime: float = 0.0
    ok: bool = False
    passed: int = 0
    failed: int = 0
    randomUnseed: int = 0
    peakMemUsage: int = 0
    events: List[Event] = field(default_factory=list)


@dataclass
class AreaGraphPoint:
    X: float = 0.0
    Y: float = 0.0


@dataclass
class LineGraphPoint:
    X: float = 0.0
    Y: float = 0.0
    Category: Optional[Any] = None


@dataclass
class Interval:
    Begin: float = 0.0
    End: float = 0.0
    Category: str = ''
    Color: str = ''
    Detail: str = ''
    Object: Optional[Any] = None


@dataclass
class MachineRole(Interval):
    Machine: str = ''
    Role: str = ''


@dataclass
class Location:
    Name: str = ''
    Y: int = 0


class LocationTimeOp(IntEnum):
    Normal = 0
    MapId = 1


@dataclass
class LocationTime:
    id: int = 0
    Time: float = 0.0
    Loc: Optional[Location] = None
    locationTimeOp: LocationTimeOp = LocationTimeOp.Normal
    childId: int = 0
