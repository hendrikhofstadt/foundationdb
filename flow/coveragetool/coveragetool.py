#!/usr/bin/env python3
#
# coveragetool.py
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

import os
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set, Optional


@dataclass
class CoverageCase:
    file: str
    line: int
    comment: str
    condition: str


class ParseException(Exception):
    pass


def parse_output(filename: str) -> tuple[List[CoverageCase], List[str]]:
    """Parse existing coverage XML file."""
    tree = ET.parse(filename)
    root = tree.getroot()

    cases = []
    coverage_cases = root.find('CoverageCases')
    if coverage_cases is not None:
        for case in coverage_cases.findall('Case'):
            cases.append(CoverageCase(
                file=case.get('File', ''),
                line=int(case.get('Line', '0')),
                comment=case.get('Comment', ''),
                condition=case.get('Condition', '')
            ))

    args = []
    inputs = root.find('Inputs')
    if inputs is not None:
        for input_elem in inputs.findall('Input'):
            if input_elem.text:
                args.append(input_elem.text)

    return cases, args


def write_output(filename: str, cases: List[CoverageCase], args: List[str]) -> None:
    """Write coverage cases to XML file."""
    root = ET.Element('CoverageTool')

    coverage_cases = ET.SubElement(root, 'CoverageCases')
    for case in cases:
        case_elem = ET.SubElement(coverage_cases, 'Case')
        case_elem.set('File', case.file)
        case_elem.set('Line', str(case.line))
        case_elem.set('Comment', case.comment)
        case_elem.set('Condition', case.condition)

    inputs = ET.SubElement(root, 'Inputs')
    for arg in args:
        input_elem = ET.SubElement(inputs, 'Input')
        input_elem.text = arg

    tree = ET.ElementTree(root)
    ET.indent(tree, space='  ')
    tree.write(filename, encoding='utf-8', xml_declaration=True)


def find_comment(line: str) -> str:
    """Extract comment from line."""
    comment_idx = line.find('//')
    if comment_idx == -1:
        return ''
    return line[comment_idx + 2:].strip()


def parse_source(filename: str) -> List[CoverageCase]:
    """Parse a source file for coverage cases."""
    regex = re.compile(r'^([^/]|/[^/])*\s+(TEST|INJECT_FAULT|SHOULD_INJECT_FAULT)[ \t]*\(([^)]*)\)')

    with open(filename, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()

    results = []
    for i, line in enumerate(lines):
        match = regex.match(line)
        if match and not line.startswith('#define'):
            comment = find_comment(line)
            condition = match.group(3)
            results.append(CoverageCase(
                file=filename,
                line=i + 1,
                comment=comment,
                condition=condition
            ))

    # Validate unique comments
    comments: Dict[str, CoverageCase] = {}
    failed = False
    for case in results:
        if not case.comment or case.comment.strip() == '':
            failed = True
            print(f'Error at {case.file}:{case.line}: Empty or missing comment', file=sys.stderr)
        elif case.comment in comments:
            failed = True
            prev = comments[case.comment]
            print(f'Error at {case.file}:{case.line}: {case.comment} is not a unique comment', file=sys.stderr)
            print(f'\tPreviously seen in {prev.file} at {prev.line}', file=sys.stderr)
        else:
            comments[case.comment] = case

    if failed:
        raise ParseException()

    return results


def main() -> int:
    if len(sys.argv) < 2:
        print('Usage:')
        print('  coveragetool [coveragefile] [inputpath]*')
        return 100

    quiet = os.environ.get('VERBOSE') is None

    if not quiet:
        print(f'coveragetool {" ".join(sys.argv)}')

    output = sys.argv[1]
    input_paths = [p for p in sys.argv[2:] if '.g.' not in p and '.amalgamation.' not in p]

    output_file = Path(output)

    # Parse existing output if it exists
    cases: List[CoverageCase] = []
    output_time = datetime.min
    if output_file.exists():
        try:
            old_cases, old_args = parse_output(output)
            # Check if args match
            if old_args == input_paths:
                output_time = datetime.fromtimestamp(output_file.stat().st_mtime)
                cases = old_cases
        except Exception:
            # If parsing fails, start fresh
            pass

    # Find changed files
    exists_set = set(input_paths)
    changed_files: Set[str] = set()

    for file_path in input_paths:
        try:
            file_mtime = datetime.fromtimestamp(Path(file_path).stat().st_mtime)
            if file_mtime > output_time:
                changed_files.add(file_path)
        except OSError:
            # If file doesn't exist, skip it
            pass

    try:
        # Keep cases from unchanged files
        cases = [c for c in cases if c.file in exists_set and c.file not in changed_files]

        # Parse changed files
        for file_path in changed_files:
            cases.extend(parse_source(file_path))
    except ParseException:
        return 1

    if not quiet:
        print(f'  {len(changed_files)}/{len(input_paths)} files scanned')
        print(f'  {len(cases)} coverage cases found')

    write_output(output, cases, input_paths)

    return 0


if __name__ == '__main__':
    sys.exit(main())
