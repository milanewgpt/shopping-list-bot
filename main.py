"""Entry point: start the shopping-list Telegram bot (long polling)."""

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)

from bot.config import TELEGRAM_BOT_TOKEN, logger
from bot.db import init_db
from bot.handlers import (
    cmd_clear,
    cmd_help,
    cmd_list,
    cmd_start,
    cmd_undo,
    handle_text,
    handle_voice,
)


def main() -> None:
    init_db()

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Slash commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(CommandHandler("undo", cmd_undo))

    # Voice messages
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    # Plain text (add items / natural-language commands)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Bot started (polling)")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
