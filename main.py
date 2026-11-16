"""Morning brief, evening message and weekly summary, sent to Telegram.

    python main.py             # morning: verse, self-talk, weather, agenda,
                               # deadlines, word of the day
    python main.py --evening   # evening: challenge reminder, verse, tomorrow's
                               # agenda and deadlines, bedtime note
    python main.py --weekly    # Sunday: events and deadlines of the coming week

Add --dry-run to print the message instead of sending it.
"""

from brief.cli import main

if __name__ == "__main__":
    main()
