"""Legacy debug entrypoint.

Prefer: python src/main.py --llm-debug
"""

from main import run_llm_debug_mode


def main() -> None:
    run_llm_debug_mode()


if __name__ == "__main__":
    main()
