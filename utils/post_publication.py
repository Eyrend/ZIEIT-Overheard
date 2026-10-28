import asyncio
import logging
import time

from aiogram import Bot

from config import PUBLISH_CHANNEL_ID
from sqlwork.support import (
    get_post_submissions_due_for_pin,
    get_post_submissions_due_for_unpin,
    mark_post_submission_pinned,
    mark_post_submission_unpinned,
    postpone_post_submission_pin,
    postpone_post_submission_unpin,
)


logger = logging.getLogger(__name__)


async def run_post_unpin_scheduler(bot: Bot) -> None:
    while True:
        try:
            for submission in get_post_submissions_due_for_pin():
                try:
                    await bot.pin_chat_message(
                        chat_id=PUBLISH_CHANNEL_ID,
                        message_id=submission["channel_message_id"],
                        disable_notification=True,
                    )
                except Exception:
                    logger.exception(
                        "Could not pin published post for submission %s",
                        submission["id"],
                    )
                    if not postpone_post_submission_pin(
                        submission["id"],
                        int(time.time()) + 600,
                    ):
                        logger.error(
                            "Could not reschedule pin for submission %s",
                            submission["id"],
                        )
                    continue

                if not mark_post_submission_pinned(submission["id"]):
                    logger.error(
                        "Could not record pin for submission %s",
                        submission["id"],
                    )

            for submission in get_post_submissions_due_for_unpin():
                try:
                    await bot.unpin_chat_message(
                        chat_id=PUBLISH_CHANNEL_ID,
                        message_id=submission["channel_message_id"],
                    )
                except Exception:
                    logger.exception(
                        "Could not unpin published post for submission %s",
                        submission["id"],
                    )
                    if not postpone_post_submission_unpin(
                        submission["id"],
                        int(time.time()) + 600,
                    ):
                        logger.error(
                            "Could not reschedule unpin for submission %s",
                            submission["id"],
                        )
                    continue

                if not mark_post_submission_unpinned(submission["id"]):
                    logger.error(
                        "Could not record unpin for submission %s",
                        submission["id"],
                    )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Post unpin scheduler cycle failed")

        await asyncio.sleep(30)
