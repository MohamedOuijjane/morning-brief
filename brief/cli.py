"""Command line entry point (used by main.py)."""

import argparse

from brief import config, messages, telegram


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Send the daily Telegram messages.")
    parser.add_argument(
        "--dry-run", action="store_true", help="print the message instead of sending it"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--evening", action="store_true", help="evening message")
    mode.add_argument("--weekly", action="store_true", help="weekly summary")
    args = parser.parse_args(argv)

    if args.evening and not config.ENABLE_EVENING:
        print("Evening message disabled (ENABLE_EVENING=false).")
        return
    if args.weekly and not config.ENABLE_WEEKLY:
        print("Weekly summary disabled (ENABLE_WEEKLY=false).")
        return

    if args.weekly:
        sections = messages.build_weekly_sections()
    else:
        sections = messages.build_sections(evening=args.evening)

    if args.dry_run or config.DRY_RUN:
        if config.IN_CI:  # Actions logs are public: never print private sections
            sections = [messages.redact(s) for s in sections]
        parts = telegram.split_messages(sections)
        for i, part in enumerate(parts, 1):
            if len(parts) > 1:
                print(f"----- message {i}/{len(parts)} ({len(part)} chars) -----")
            print(part)
        return

    for part in telegram.split_messages(sections):
        telegram.send(part)
    if args.weekly:
        print("Weekly summary sent.")
    elif args.evening:
        print("Evening message sent.")
    else:
        print("Brief sent.")
