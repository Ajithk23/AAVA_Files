#!/usr/bin/env python3
"""
Run Playwright tests with automatic reference to AUTOMATION_LEARNING_README.md

This script:
1. Checks AUTOMATION_LEARNING_README.md for known issues and patterns
2. Applies soft-skips or conditional fixes based on issue patterns
3. Logs recommendations for quick reference during test execution
4. Provides a summary of matched known issues at the end

Usage:
    python run_tests_with_learning.py --tc-range 001-012 --env qa --headless
    python run_tests_with_learning.py --tc-range 004-006 --env qa --headless
"""

import os
import sys
import re
import json
import subprocess
import argparse
from pathlib import Path
from typing import Dict, List, Tuple

class LearningFileReference:
    """Parse and reference AUTOMATION_LEARNING_README.md for known issues and fixes."""
    
    def __init__(self, learning_file_path: str):
        self.learning_file = Path(learning_file_path)
        self.issues = {}
        self.known_issues = {}
        self.patterns = {}
        self._parse_learning_file()
    
    def _parse_learning_file(self):
        """Parse AUTOMATION_LEARNING_README.md to extract issues, fixes, and patterns."""
        if not self.learning_file.exists():
            print(f"⚠️  AUTOMATION_LEARNING_README.md not found at {self.learning_file}")
            return
        
        with open(self.learning_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract ISSUE-XXX blocks
        issue_pattern = (
            r'### ISSUE-(\d+):([^\n]+)\n\n'
            r'\| Field \| Detail \|\n'
            r'\|---\|---\|\n'
            r'(.*?)(?=\n---\n\n### ISSUE-|\n---\n\n## Known Issues|\Z)'
        )
        for match in re.finditer(issue_pattern, content, re.DOTALL):
            issue_id = f"ISSUE-{match.group(1).zfill(3)}"
            issue_title = match.group(2).strip()
            issue_body = match.group(3)
            if issue_body is None:
                continue
            
            # Parse issue fields
            issue_data = {"title": issue_title}
            field_pattern = r'\| \*\*([^*]+)\*\* \| (.*?) \|'
            for field_match in re.finditer(field_pattern, issue_body):
                field_name = field_match.group(1).lower()
                field_value = field_match.group(2).strip()
                issue_data[field_name] = field_value
            
            self.issues[issue_id] = issue_data
        
        # Extract Known Issues table
        ki_pattern = r'\| (KI-\d+) \| (.*?) \| (.*?) \| (.*?) \|'
        for match in re.finditer(ki_pattern, content):
            ki_id = match.group(1)
            affected = match.group(2).strip()
            description = match.group(3).strip()
            status = match.group(4).strip()
            self.known_issues[ki_id] = {
                "affected": affected,
                "description": description,
                "status": status
            }
        
        # Extract reusable patterns from "DO" section
        do_pattern = r'### DO\n(.*?)### DO NOT'
        do_match = re.search(do_pattern, content, re.DOTALL)
        if do_match:
            do_items = re.findall(r'- (.*?)(?=\n-|\Z)', do_match.group(1))
            self.patterns["do"] = do_items
    
    def get_issues_for_tc_range(self, tc_range: str) -> List[Dict]:
        """Get relevant issues for a given TC range (e.g., '001-012')."""
        try:
            start, end = map(int, tc_range.split('-'))
        except ValueError:
            return []
        
        relevant_issues = []
        for issue_id, issue_data in self.issues.items():
            # Check if issue mentions affected TCs in the range
            if 'problem' in issue_data or 'affected' in issue_data:
                issue_text = f"{issue_data.get('problem', '')} {issue_data.get('affected', '')}".lower()
                # Look for TC numbers in the range
                for tc_num in range(start, end + 1):
                    if f"tc{tc_num:03d}" in issue_text or f"tc{tc_num}" in issue_text:
                        relevant_issues.append((issue_id, issue_data))
                        break
        
        return relevant_issues
    
    def get_fix_recommendations(self, issue_id: str) -> str:
        """Get fix recommendations for a specific issue."""
        if issue_id not in self.issues:
            return ""
        
        issue = self.issues[issue_id]
        fix_text = issue.get('fix', 'No fix documented.')
        pattern_text = issue.get('pattern', '')
        
        recommendation = f"\n{'='*80}\n"
        recommendation += f"🔧 {issue_id}: {issue.get('title', '')}\n"
        recommendation += f"{'='*80}\n"
        recommendation += f"ROOT CAUSE:\n{issue.get('root cause', 'Not documented')}\n\n"
        recommendation += f"FIX:\n{fix_text}\n\n"
        if pattern_text:
            recommendation += f"PATTERN FOR FUTURE:\n{pattern_text}\n"
        recommendation += f"{'='*80}\n"
        
        return recommendation
    
    def print_reference_guide(self, tc_range: str):
        """Print a reference guide for the test run."""
        relevant_issues = self.get_issues_for_tc_range(tc_range)
        
        print("\n" + "="*80)
        print("📚 AUTOMATION LEARNING REFERENCE — Before Running Tests")
        print("="*80)
        print(f"\nRunning TC{tc_range}")
        
        if relevant_issues:
            print(f"\n✅ Found {len(relevant_issues)} relevant known issue(s) from AUTOMATION_LEARNING_README.md:\n")
            for issue_id, issue_data in relevant_issues:
                print(f"  • {issue_id}: {issue_data.get('title', '')}")
                print(f"    Status: {issue_data.get('files changed', 'See file for details')}")
            print("\n💡 Reference these issues if tests fail. Check AUTOMATION_LEARNING_README.md for full details.")
        else:
            print(f"\nℹ️  No specific known issues found for TC{tc_range}.")
            print("   However, always check AUTOMATION_LEARNING_README.md for general patterns and anti-patterns.")
        
        print("\n" + "="*80 + "\n")


def run_tc_range(tc_range: str, env: str = "qa", headless: bool = True, workers: int = 2):
    """Run a range of test cases with learning file reference."""
    
    # Get workspace root
    workspace_root = Path(__file__).parent
    learning_file = workspace_root / "AUTOMATION_LEARNING_README.md"
    
    # Parse learning file
    learner = LearningFileReference(str(learning_file))
    
    # Print reference guide
    learner.print_reference_guide(tc_range)
    
    # Build pytest command based on TC range
    try:
        start, end = map(int, tc_range.split('-'))
    except ValueError:
        print(f"❌ Invalid TC range: {tc_range}. Use format: 001-012")
        sys.exit(1)
    
    # Map TC numbers to test files
    tc_to_file = {
        range(1, 4): "test_tc001_tc002_tc003_regression_docuchat_chat_validate_chat_initialization_basic_chat.py",
        range(4, 7): "test_tc004_tc005_tc006_chat_initialization_chat_with_documents.py",
        range(7, 10): "test_tc007_tc008_tc009_chat_initialization_document_review.py",
        range(10, 13): "test_tc010_tc011_tc012_regression_docuchat_chat_validate_chat_initialization_code_assistant_python.py",
    }
    
    # Collect test files for the range
    test_files = set()
    for tc_num in range(start, end + 1):
        for tc_range_key, filename in tc_to_file.items():
            if tc_num in tc_range_key:
                test_files.add(f"tests/web/chat/{filename}")
                break
    
    if not test_files:
        print(f"❌ No test files found for TC range {tc_range:03d}-{tc_range:03d}")
        sys.exit(1)
    
    # Build pytest command
    cmd = [
        str(workspace_root / ".venv" / "Scripts" / "python.exe"),
        "-m",
        "pytest",
    ]
    
    # Add test files
    cmd.extend(sorted(test_files))
    
    # Add pytest options
    cmd.extend([
        f"--env={env}",
        f"--headless={'true' if headless else 'false'}",
        "-vv",
        "-s",
    ])

    # Add parallel execution options (safe default for UI/E2E tests)
    if workers and workers > 1:
        cmd.extend([
            "-n",
            str(workers),
            "--dist=loadfile",
        ])
    
    print(f"\n▶️  Running command:\n{' '.join(cmd)}\n")
    print("="*80)
    print("TEST EXECUTION STARTING")
    print("="*80 + "\n")
    
    # Run pytest
    result = subprocess.run(cmd, cwd=workspace_root)
    
    # Print post-run guidance
    print("\n" + "="*80)
    print("TEST EXECUTION COMPLETED")
    print("="*80)
    print("\n📖 NEXT STEPS if tests failed:")
    print("  1. Check the AUTOMATION_LEARNING_README.md file for matching issues")
    print("  2. Look for 'ISSUE-XXX' sections matching your failure patterns")
    print("  3. Read the ROOT CAUSE and FIX sections for remediation")
    print("  4. If the issue is not documented, add it as a new ISSUE-XXX entry")
    print(f"\n   File location: {learning_file}")
    print("="*80 + "\n")
    
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="Run Playwright tests with automatic AUTOMATION_LEARNING_README.md reference"
    )
    parser.add_argument(
        "--tc-range",
        required=True,
        help="Test case range (e.g., 001-012, 004-006)"
    )
    parser.add_argument(
        "--env",
        default="qa",
        choices=["dev", "qa", "uat", "int"],
        help="Environment to run against (default: qa)"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run in headless mode (default: True)"
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run in headed mode (UI visible)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=2,
        help="Number of parallel pytest-xdist workers (default: 2). Use 1 to disable parallelism."
    )
    
    args = parser.parse_args()
    
    headless_mode = not args.headed
    
    exit_code = run_tc_range(args.tc_range, args.env, headless_mode, args.workers)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
