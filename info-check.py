#!/usr/bin/env python3
"""Info Check CLI - Message verification tool.

Usage:
    python info-check.py "message to verify"
    ./info-check.sh "message to verify"
"""

import sys
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.workflows.check import create_workflow


def main():
    parser = argparse.ArgumentParser(
        description="Info Check - Verify message accuracy through multi-channel research"
    )
    parser.add_argument(
        "message",
        nargs="?",
        help="Message to verify"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    if not args.message:
        parser.print_help()
        print("\n请提供要核查的消息，例如：")
        print('  python info-check.py "马斯克的 Starship 正式发射了"')
        sys.exit(1)
    
    print("=" * 60)
    print("🔍 消息核查器 (Info Check)")
    print("=" * 60)
    print(f"\n正在核查: {args.message}\n")
    
    try:
        workflow = create_workflow()
        report = workflow.run(args.message)
        
        print("\n" + "=" * 60)
        print("📋 核查报告")
        print("=" * 60)
        print(report)
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
