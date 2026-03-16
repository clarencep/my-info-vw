#!/usr/bin/env python3
"""Info Check CLI - Message verification tool.

Usage:
    python info-check.py "message to verify"
    ./info-check.sh "message to verify"
    python info-check.py "message" --jsonl
"""

import sys
import json
import logging
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging for all modules
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

from src.workflows.check import create_workflow


class JSONLLogger:
    """JSONL output logger."""
    
    def __init__(self, output_file=None):
        self.output_file = output_file
        self.entries = []
    
    def log(self, level: str, msg_type: str, message: str, **kwargs):
        """Log a JSONL entry."""
        entry = {
            "level": level,
            "type": msg_type,
            "message": message,
            **kwargs
        }
        self.entries.append(entry)
        
        # Output to stdout or file
        json_line = json.dumps(entry, ensure_ascii=False)
        if self.output_file:
            with open(self.output_file, "a", encoding="utf-8") as f:
                f.write(json_line + "\n")
        else:
            print(json_line)
    
    def info(self, msg_type: str, message: str, **kwargs):
        self.log("INFO", msg_type, message, **kwargs)
    
    def warning(self, msg_type: str, message: str, **kwargs):
        self.log("WARNING", msg_type, message, **kwargs)
    
    def error(self, msg_type: str, message: str, **kwargs):
        self.log("ERROR", msg_type, message, **kwargs)
    
    def success(self, msg_type: str, message: str, **kwargs):
        self.log("SUCCESS", msg_type, message, **kwargs)


def run_with_jsonl(message: str, logger: JSONLLogger):
    """Run workflow with JSONL output."""
    try:
        logger.info("workflow", f"开始核查消息: {message[:50]}...")
        
        workflow = create_workflow()
        
        logger.info("workflow", "工作流创建成功")
        
        # Run the workflow
        report = workflow.run(message)
        
        logger.success("complete", "核查完成", report=report)
        
        return 0
        
    except Exception as e:
        logger.error("error", f"执行出错: {str(e)}")
        return 1


def run_normal(message: str, verbose: bool = False):
    """Run workflow with normal text output."""
    print("=" * 60)
    print("🔍 消息核查器 (Info Check)")
    print("=" * 60)
    print(f"\n正在核查: {message}\n")
    
    try:
        workflow = create_workflow()
        report = workflow.run(message)
        
        print("\n" + "=" * 60)
        print("📋 核查报告")
        print("=" * 60)
        print(report)
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return 1
    
    return 0


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
    parser.add_argument(
        "--jsonl",
        action="store_true",
        help="Output JSONL format for programmatic consumption"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output file for JSONL (default: stdout)"
    )
    
    args = parser.parse_args()
    
    if not args.message:
        parser.print_help()
        print("\n请提供要核查的消息，例如：")
        print('  python info-check.py "马斯克的 Starship 正式发射了"')
        print('  python info-check.py "消息" --jsonl')
        sys.exit(1)
    
    if args.jsonl:
        logger = JSONLLogger(args.output)
        sys.exit(run_with_jsonl(args.message, logger))
    else:
        sys.exit(run_normal(args.message, args.verbose))


if __name__ == "__main__":
    main()
