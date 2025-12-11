import logging
from hydrogram import Client, filters
from hydrogram.errors import InvalidQueryType
from hydrogram.types import (
    InlineQueryResultCachedDocument,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from database.ia_filterdb import get_search_results
from utils import is_premium, get_size, temp
from info import CACHE_TIME, IS_PREMIUM

logger = logging.getLogger(__name__)

@Client.on_inline_query()
async def answer(client, query):
    """Handles Inline Search (@BotName MovieName)"""
    
    # 1. Check if query is empty
    if query.query == "":
        return

    # 2. Check Premium (Optional - If you want strict premium on inline too)
    if IS_PREMIUM:
        if not await is_premium(query.from_user.id, client):
            # Show "Upgrade to Premium" button if not premium
            results = [
                InlineQueryResultArticle(
                    title="💎 Premium Only",
                    description="You need a Premium Plan to use Inline Search.",
                    input_message_content=InputTextMessageContent(
                        message_text="<b>❌ Access Denied</b>\n\nInline search is restricted to Premium users only.\n\nType /plan to upgrade."
                    ),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("💎 Upgrade Plan", url=f"https://t.me/{temp.U_NAME}?start=plan")]
                    ])
                )
            ]
            await query.answer(results, cache_time=CACHE_TIME, is_personal=True)
            return

    results = []
    search_query = query.query.strip()
    offset = int(query.offset or 0)

    # 3. Search Database
    files, next_offset, total = await get_search_results(search_query, offset=offset)

    # 4. Generate Results
    if files:
        for file in files:
            f_caption = file.get('caption', '')
            f_name = file.get('file_name', '')
            f_size = get_size(file.get('file_size', 0))
            
            # Create Result Item
            results.append(
                InlineQueryResultCachedDocument(
                    title=f_name,
                    document_file_id=file['file_id'],
                    caption=f_caption,
                    description=f"Size: {f_size}",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🤖 Search via Bot", url=f"https://t.me/{temp.U_NAME}")]
                    ])
                )
            )
    else:
        # No Results Found
        if offset == 0:
            results.append(
                InlineQueryResultArticle(
                    title="❌ No Results Found",
                    description=f"Could not find: {search_query}",
                    input_message_content=InputTextMessageContent(
                        message_text=f"<b>❌ No results found for:</b> <code>{search_query}</code>"
                    )
                )
            )

    # 5. Send Answer
    try:
        await query.answer(
            results=results,
            cache_time=CACHE_TIME,
            next_offset=str(next_offset) if next_offset else "",
            is_personal=True
        )
    except InvalidQueryType:
        pass
    except Exception as e:
        logger.error(f"Inline Error: {e}")
