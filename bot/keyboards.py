from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from db.models import Source

THEMES = [
    "chemistry", "music", "rap", "history", "news", "programming",
    "vlog", "games", "diy", "technica", "travel"
]


def themes_keyboard():
    keyboard = []
    row = []
    for i, theme in enumerate(THEMES):
        row.append(InlineKeyboardButton(theme.capitalize(), callback_data=f"theme:{theme}"))
        if (i + 1) % 3 == 0 or i == len(THEMES) - 1:
            keyboard.append(row)
            row = []
    return InlineKeyboardMarkup(keyboard)


def sources_keyboard(sources):
    keyboard = []
    for src in sources:
        keyboard.append([InlineKeyboardButton(src.title, callback_data=f"source:{src.id}")])
    return InlineKeyboardMarkup(keyboard)


def confirm_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("Yes", callback_data="confirm:yes"),
            InlineKeyboardButton("No", callback_data="confirm:no"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def subscriptions_keyboard(subscriptions):
    """
    Build an inline keyboard listing user's subscriptions.
    subscriptions: list of Source objects or dicts with 'id' and 'title'
    """
    keyboard = []
    for sub in subscriptions:
        # Each subscription gets a button to unsubscribe
        keyboard.append([
            InlineKeyboardButton(
                f"❌ {sub.title}",  # assuming sub has 'title' attribute
                callback_data=f"unsub_{sub.id}"
            )
        ])
    # Optional: add a back button
    keyboard.append([InlineKeyboardButton("🔙 Back to themes", callback_data="back_to_themes")])
    return InlineKeyboardMarkup(keyboard)