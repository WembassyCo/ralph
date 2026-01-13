#!/usr/bin/env python3
"""
Ralph Wiggum - Long-running AI agent loop
Usage: python ralph.py [max_iterations] [--config /path/to/config.json]
"""

import json
import sys
import os
import argparse
import subprocess
import shutil
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class LLMConfig:
    provider: str  # "auto", "amp", "claude", "ollama"
    model: str
    apiKey: str = ""
    ollamaUrl: str = "http://localhost:11434"


class RalphLLMClient:
    """Client for interacting with different LLM providers"""

    def __init__(self, config: LLMConfig):
        self.config = config
        self._detected_provider: Optional[str] = None

    def detect_provider(self) -> str:
        """Auto-detect available provider"""
        if self._detected_provider:
            return self._detected_provider

        if self.config.provider != "auto":
            self._detected_provider = self.config.provider
            return self._detected_provider

        # 1. Try Ollama
        if self._check_ollama():
            self._detected_provider = "ollama"
            return "ollama"

        # 2. Try Claude
        if self._check_claude():
            self._detected_provider = "claude"
            return "claude"

        # 3. Fall back to Amp
        if self._check_amp():
            self._detected_provider = "amp"
            return "amp"

        raise Exception("No LLM provider available. Please configure Ollama, Claude API key, or install Amp.")

    def _check_ollama(self) -> bool:
        """Check if Ollama is available"""
        try:
            import ollama
            client = ollama.Client(host=self.config.ollamaUrl)
            # Try to list models
            response = client.list()
            # Check if our model exists (with or without :latest suffix)
            model_names = [m['name'] for m in response.get('models', [])]

            # Try exact match first
            if self.config.model in model_names:
                return True

            # Try with :latest suffix
            if f"{self.config.model}:latest" in model_names:
                return True

            # Try matching base model name (e.g., "llama3.1" matches "llama3.1:latest")
            for name in model_names:
                if name.startswith(f"{self.config.model}:"):
                    return True

            return False
        except Exception as e:
            print(f"  Ollama check failed: {e}", file=sys.stderr)
            return False

    def _check_claude(self) -> bool:
        """Check if Claude API key is available"""
        api_key = self.config.apiKey or os.getenv('ANTHROPIC_API_KEY')
        return bool(api_key)

    def _check_amp(self) -> bool:
        """Check if amp CLI is available"""
        return shutil.which('amp') is not None

    def chat(self, prompt: str) -> str:
        """Send prompt to LLM and return response"""
        provider = self.detect_provider()

        if provider == "ollama":
            return self._chat_ollama(prompt)
        elif provider == "claude":
            return self._chat_claude(prompt)
        elif provider == "amp":
            return self._chat_amp(prompt)
        else:
            raise Exception(f"Unknown provider: {provider}")

    def _chat_ollama(self, prompt: str) -> str:
        """Use Ollama"""
        import ollama
        client = ollama.Client(host=self.config.ollamaUrl)

        # Use the model name as-is, Ollama will handle :latest suffix automatically
        response = client.chat(
            model=self.config.model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response['message']['content']

    def _chat_claude(self, prompt: str) -> str:
        """Use Claude API"""
        from anthropic import Anthropic
        api_key = self.config.apiKey or os.getenv('ANTHROPIC_API_KEY')
        client = Anthropic(api_key=api_key)

        response = client.messages.create(
            model=self.config.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )

        # Extract text from response blocks
        text_content = ""
        for block in response.content:
            if block.type == "text":
                text_content += block.text
        return text_content

    def _chat_amp(self, prompt: str) -> str:
        """Use Amp CLI"""
        result = subprocess.run(
            ['amp', '--dangerously-allow-all'],
            input=prompt,
            capture_output=True,
            text=True
        )
        # Combine stdout and stderr like the original bash script
        return result.stdout + result.stderr


class RalphOrchestrator:
    """Main Ralph loop orchestrator"""

    def __init__(self, script_dir: Path, config_path: Optional[str] = None):
        self.script_dir = script_dir
        self.prd_file = script_dir / "prd.json"
        self.progress_file = script_dir / "progress.txt"
        self.archive_dir = script_dir / "archive"
        self.last_branch_file = script_dir / ".last-branch"
        self.prompt_file = script_dir / "prompt.md"

        # Load config
        if config_path:
            config = load_config(config_path)
        else:
            config = load_config(str(script_dir / "config.json"))

        self.llm_client = RalphLLMClient(config)

    def archive_previous_run(self):
        """Archive previous run if branch changed"""
        if not self.prd_file.exists() or not self.last_branch_file.exists():
            return

        # Read current and last branch
        with open(self.prd_file, 'r') as f:
            prd = json.load(f)
            current_branch = prd.get('branchName', '')

        with open(self.last_branch_file, 'r') as f:
            last_branch = f.read().strip()

        if current_branch and last_branch and current_branch != last_branch:
            # Archive the previous run
            date_str = datetime.now().strftime('%Y-%m-%d')
            folder_name = last_branch.replace('ralph/', '')
            archive_folder = self.archive_dir / f"{date_str}-{folder_name}"

            print(f"Archiving previous run: {last_branch}")
            archive_folder.mkdir(parents=True, exist_ok=True)

            if self.prd_file.exists():
                shutil.copy(self.prd_file, archive_folder / "prd.json")
            if self.progress_file.exists():
                shutil.copy(self.progress_file, archive_folder / "progress.txt")

            print(f"   Archived to: {archive_folder}")

            # Reset progress file
            self.init_progress_file()

    def init_progress_file(self):
        """Initialize or reset progress file"""
        with open(self.progress_file, 'w') as f:
            f.write("# Ralph Progress Log\n")
            f.write(f"Started: {datetime.now()}\n")
            f.write("---\n")

    def track_current_branch(self):
        """Track current branch to .last-branch file"""
        if self.prd_file.exists():
            with open(self.prd_file, 'r') as f:
                prd = json.load(f)
                current_branch = prd.get('branchName', '')

            if current_branch:
                with open(self.last_branch_file, 'w') as f:
                    f.write(current_branch)

    def run_iteration(self) -> Tuple[str, bool]:
        """
        Run one Ralph iteration.
        Returns: (output, is_complete)
        """
        # Read prompt
        with open(self.prompt_file, 'r') as f:
            prompt = f.read()

        # Call LLM
        output = self.llm_client.chat(prompt)

        # Print output (mimics the tee behavior from bash)
        print(output, file=sys.stderr)

        # Check for completion signal
        is_complete = '<promise>COMPLETE</promise>' in output

        return output, is_complete

    def run(self, max_iterations: int) -> int:
        """Run Ralph loop. Returns exit code."""
        # Setup
        self.archive_previous_run()
        self.track_current_branch()

        if not self.progress_file.exists():
            self.init_progress_file()

        # Detect and announce provider
        try:
            provider = self.llm_client.detect_provider()
            print(f"Starting Ralph - Max iterations: {max_iterations}")
            print(f"Using provider: {provider} (model: {self.llm_client.config.model})")
            print()
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

        # Main loop
        for i in range(1, max_iterations + 1):
            print()
            print("═" * 55)
            print(f"  Ralph Iteration {i} of {max_iterations}")
            print("═" * 55)

            try:
                output, is_complete = self.run_iteration()

                if is_complete:
                    print()
                    print("Ralph completed all tasks!")
                    print(f"Completed at iteration {i} of {max_iterations}")
                    return 0

                print(f"Iteration {i} complete. Continuing...")
            except Exception as e:
                print(f"Error in iteration {i}: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                # Continue to next iteration

            # Sleep between iterations
            time.sleep(2)

        print()
        print(f"Ralph reached max iterations ({max_iterations}) without completing all tasks.")
        print(f"Check {self.progress_file} for status.")
        return 1


def load_config(config_path: str) -> LLMConfig:
    """Load config from file"""
    try:
        with open(config_path, 'r') as f:
            data = json.load(f)
            llm_data = data.get('llm', {})
            return LLMConfig(
                provider=llm_data.get('provider', 'auto'),
                model=llm_data.get('model', 'llama3.1'),
                apiKey=llm_data.get('apiKey', ''),
                ollamaUrl=llm_data.get('ollamaUrl', 'http://localhost:11434')
            )
    except FileNotFoundError:
        # Return default config
        print(f"Warning: Config file not found at {config_path}, using defaults", file=sys.stderr)
        return LLMConfig(
            provider="auto",
            model="llama3.1",
            apiKey="",
            ollamaUrl="http://localhost:11434"
        )
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in config file: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Ralph Wiggum - Long-running AI agent loop"
    )
    parser.add_argument(
        'max_iterations',
        type=int,
        nargs='?',
        default=10,
        help='Maximum number of iterations (default: 10)'
    )
    parser.add_argument(
        '--config',
        help='Path to config.json file (default: ./config.json)'
    )
    args = parser.parse_args()

    # Determine script directory
    script_dir = Path(__file__).parent.resolve()

    # Create orchestrator
    orchestrator = RalphOrchestrator(script_dir, args.config)

    # Run Ralph
    exit_code = orchestrator.run(args.max_iterations)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
