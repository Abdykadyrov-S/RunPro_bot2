import asyncio, logging

from core.bot import create_bot
from core.dispatcher import create_dispatcher
from core.logging import setup_logging

from db.database import *


async def main():
    setup_logging()
    logging.info("Bot starting...")

    bot = create_bot()
    dp = create_dispatcher()
    await init_db()

    # Keep pending updates so the bot will process messages received while it was offline
    await bot.delete_webhook(drop_pending_updates=False)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
