import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, ConversationHandler
from sqlalchemy.ext.asyncio import AsyncSession

from db import crud
from db.session import async_session_maker
from bot.keyboards import (
    themes_keyboard,
    sources_keyboard,
    subscriptions_keyboard,
    confirm_keyboard,
)

logger = logging.getLogger(__name__)

# Conversation states for subscribe
SELECT_THEME, SELECT_SOURCE, CONFIRM = range(3)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    async with async_session_maker() as session:
        await crud.get_or_create_user(session, user_id)
    await update.message.reply_text(
        "Welcome to the Multi-Source News Aggregator Bot!\n\n"
        "Available themes: chemistry, music, rap, history, news, programming, vlog, games, diy, technica, travel.\n\n"
        "Use /subscribe to start receiving posts, /unsubscribe to remove sources, /list to see your subscriptions."
    )


async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start subscription conversation: choose a theme."""
    await update.message.reply_text(
        "Select a theme:",
        reply_markup=themes_keyboard(),
    )
    return SELECT_THEME


async def theme_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    theme_name = query.data.split(":")[1]
    context.user_data["sub_theme"] = theme_name

    async with async_session_maker() as session:
        sources = await crud.get_sources_by_theme(session, theme_name)

    if not sources:
        await query.edit_message_text(
            f"No sources available for theme '{theme_name}'. Please choose another theme.",
            reply_markup=themes_keyboard(),
        )
        return SELECT_THEME

    context.user_data["sub_sources"] = sources
    await query.edit_message_text(
        f"Sources for theme '{theme_name}':",
        reply_markup=sources_keyboard(sources),
    )
    return SELECT_SOURCE


async def source_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    source_id = int(query.data.split(":")[1])
    context.user_data["sub_source_id"] = source_id

    source = next(
        (s for s in context.user_data["sub_sources"] if s.id == source_id), None
    )
    if not source:
        await query.edit_message_text("Error: source not found. Please restart /subscribe.")
        return ConversationHandler.END

    await query.edit_message_text(
        f"Confirm subscription to '{source.title}'?\n\n"
        f"Platform: {source.platform}\n"
        f"Theme: {context.user_data['sub_theme']}",
        reply_markup=confirm_keyboard(),
    )
    return CONFIRM


async def confirm_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "confirm:yes":
        user_id = update.effective_user.id
        source_id = context.user_data["sub_source_id"]
        async with async_session_maker() as session:
            user = await crud.get_or_create_user(session, user_id)
            success = await crud.add_subscription(session, user.id, source_id)
        if success:
            await query.edit_message_text("Subscription added successfully!")
        else:
            await query.edit_message_text("You are already subscribed to this source.")
    else:
        await query.edit_message_text("Subscription cancelled.")
    return ConversationHandler.END


async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    async with async_session_maker() as session:
        user = await crud.get_or_create_user(session, user_id)
        subs = await crud.get_user_subscriptions(session, user.id)

    if not subs:
        await update.message.reply_text("You have no active subscriptions.")
        return

    keyboard = []
    for sub in subs:
        keyboard.append(
            [InlineKeyboardButton(f"Unsubscribe {sub.title}", callback_data=f"unsub:{sub.id}")]
        )
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Select a subscription to remove:", reply_markup=reply_markup)


async def handle_unsubscribe_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    source_id = int(query.data.split(":")[1])
    user_id = update.effective_user.id
    async with async_session_maker() as session:
        user = await crud.get_or_create_user(session, user_id)
        await crud.remove_subscription(session, user.id, source_id)
    await query.edit_message_text("Subscription removed.")


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    async with async_session_maker() as session:
        user = await crud.get_or_create_user(session, user_id)
        subs = await crud.get_user_subscriptions(session, user.id)

    if not subs:
        await update.message.reply_text("You are not subscribed to any sources.")
    else:
        lines = ["Your subscriptions:"]
        for s in subs:
            lines.append(f"- {s.title} ({s.platform})")
        await update.message.reply_text("\n".join(lines))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "/start - Welcome\n"
        "/subscribe - Subscribe to sources by theme\n"
        "/unsubscribe - Remove a subscription\n"
        "/list - Show your subscriptions\n"
        "/help - This message"
    )


def register_conversation_handlers(app):
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("subscribe", subscribe_command)],
        states={
            SELECT_THEME: [CallbackQueryHandler(theme_selected, pattern="^theme:")],
            SELECT_SOURCE: [CallbackQueryHandler(source_selected, pattern="^source:")],
            CONFIRM: [CallbackQueryHandler(confirm_subscription, pattern="^confirm:")],
        },
        fallbacks=[CommandHandler("cancel", lambda u,c: ConversationHandler.END)],
    )
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(handle_unsubscribe_callback, pattern="^unsub:"))