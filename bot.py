import logging
import os
import logging
import os
import re
import uuid
import sys
import shutil
import math
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, CallbackContext,
    CallbackQueryHandler, ConversationHandler, PicklePersistence
)
import yt_dlp
from image_enhancer import enhance_photo
from video_converter import convert_video_resolution, enhance_video_quality

load_dotenv()
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

(
    GET_URL, GET_SEARCH_QUERY, GET_SONG_TITLE, GET_PHOTO,
    GET_ENHANCEMENT, GET_VIDEO, GET_PROCESS_ACTION, CHOOSE_FORMAT
) = range(8)

async def post_init(application: Application):
    user_ids = application.bot_data.get('user_ids', set())
    for user_id in user_ids:
        try:
            await application.bot.send_message(chat_id=user_id, text="BOT ONLINE ✅")
        except Exception as e:
            logger.warning(f"Could not send online message to {user_id}: {e}")

def run_pre_flight_checks():
    logger.info("--- 🩺 Running Pre-flight Checks ---")
    if not (os.getenv("TELEGRAM_TOKEN") and os.getenv("TELEGRAM_TOKEN") != "GANTI_DENGAN_TOKEN_ANDA"):
        logger.critical("FATAL: TELEGRAM_TOKEN not configured.")
        return False
    if not shutil.which("ffmpeg"):
        logger.critical("FATAL: ffmpeg not found in PATH.")
        return False
    logger.info("[✅] All checks passed.")
    return True

async def download_media(identifier: str, format_choice: str, effective_message):
    status_message = await effective_message.reply_text("⏳ Memproses...")
    download_dir = 'downloads'
    os.makedirs(download_dir, exist_ok=True)

    ydl_opts = {
        'outtmpl': os.path.join(download_dir, '%(id)s.%(ext)s'),
        'noplaylist': True, 'quiet': True
    }
    if format_choice == 'audio':
        ydl_opts.update({'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}]})
    else:
        ydl_opts.update({'format': 'bestvideo+bestaudio/best'})

    path, base_path = "", ""
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(identifier, download=True)
            base_path = ydl.prepare_filename(info)

        path = os.path.splitext(base_path)[0] + '.mp3' if format_choice == 'audio' else base_path
        if not os.path.exists(path): raise FileNotFoundError(f"File not found: {path}")

        filename = f"{re.sub(r'[\\/*?:\"<>|]', '', info.get('title', 'media'))}.{'mp3' if format_choice == 'audio' else info.get('ext', 'mp4')}"

        with open(path, 'rb') as f:
            if format_choice == 'audio':
                await effective_message.reply_audio(f, title=info.get('title'), filename=filename, caption=info.get('title'))
            else:
                await effective_message.reply_video(f, filename=filename, caption=info.get('title'))
    except Exception as e:
        logger.error(f"Download failed for '{identifier}': {e}", exc_info=True)
        await effective_message.reply_text(f"❌ Gagal: Link tidak didukung atau error internal.")
    finally:
        if status_message: await status_message.delete()
        for p in [path, base_path]:
            if p and os.path.exists(p): os.remove(p)

async def cancel(update: Update, context: CallbackContext):
    context.user_data.clear()
    await update.message.reply_text("Operasi dibatalkan.")
    return ConversationHandler.END

async def start(update: Update, context: CallbackContext):
    context.bot_data.setdefault('user_ids', set()).add(update.effective_chat.id)
    await update.message.reply_html(f"👋 Halo {update.effective_user.mention_html()}! /help untuk bantuan.")

async def help_command(update: Update, context: CallbackContext):
    await update.message.reply_markdown("...")

async def download_start(update: Update, context: CallbackContext):
    await update.message.reply_text("Kirimkan URL.")
    return GET_URL

async def download_get_url(update: Update, context: CallbackContext):
    url = update.message.text
    if not re.match(r'https?://\S+', url):
        await update.message.reply_text("URL tidak valid. /cancel untuk batal.")
        return GET_URL

    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'noplaylist': True}) as ydl: info = ydl.extract_info(url, download=False)
        context.user_data['url_info'] = {'url': url, 'title': info.get('title', 'Tanpa Judul')}
        keyboard = [[InlineKeyboardButton("🎧 Audio", callback_data=f"dl_url:audio"), InlineKeyboardButton("🎬 Video", callback_data=f"dl_url:video")]]
        await update.message.reply_photo(photo=info.get('thumbnail'), caption=f"Pilih format untuk:\n*{info.get('title')}*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    except Exception:
        await download_media(url, 'video', update.message)
    return CHOOSE_FORMAT

async def _execute_and_send_search(chat_id, context: CallbackContext, is_new_search=False):
    query = context.user_data.get('search_query')
    status_message = None
    try:
        if is_new_search:
            status_message = await context.bot.send_message(chat_id=chat_id, text="⏳ Mencari 250 video...")
            search_query = f"ytsearch250:{query}"
            ydl_opts = {'quiet': True, 'noplaylist': True, 'match_filter': 'duration < 600', 'extract_flat': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(search_query, download=False)

            entries = result.get('entries', [])
            if not entries:
                await context.bot.send_message(chat_id=chat_id, text="Tidak ada hasil yang cocok dengan filter durasi (di bawah 10 menit).")
                context.user_data['search_results'] = []
                return

            context.user_data['search_results'] = entries
            context.user_data['search_page'] = 0
    except Exception as e:
        logger.error(f"Deep search failed for '{query}': {e}", exc_info=True)
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Gagal: Terjadi error saat melakukan pencarian mendalam.")
    finally:
        if status_message: await status_message.delete()

async def _display_search_page(update: Update, context: CallbackContext):
    RESULTS_PER_PAGE = 10
    results = context.user_data.get('search_results', [])
    page = context.user_data.get('search_page', 0)

    if not results:
        return

    start_index = page * RESULTS_PER_PAGE
    end_index = start_index + RESULTS_PER_PAGE
    page_results = results[start_index:end_index]

    caption_lines = []
    for i, entry in enumerate(page_results, start=1):
        duration_seconds = entry.get('duration', 0)
        minutes = int(duration_seconds // 60)
        seconds = int(duration_seconds % 60)
        duration_str = f"{minutes:02d}:{seconds:02d}"
        caption_lines.append(f"*{i}.* `{duration_str}` - {entry['title']}")

    caption = "\n".join(caption_lines)
    total_pages = math.ceil(len(results) / RESULTS_PER_PAGE)

    keyboard = []
    for i, entry in enumerate(page_results, start=1):
        video_id = entry['id']
        keyboard.append([
            InlineKeyboardButton(f"🎧 {i}", callback_data=f"dl_search:audio:{video_id}"),
            InlineKeyboardButton(f"🎬 {i}", callback_data=f"dl_search:video:{video_id}")
        ])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("<<", callback_data="search:prev"))
    nav_buttons.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="search:noop"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(">>", callback_data="search:next"))
    keyboard.append(nav_buttons)
    keyboard.append([InlineKeyboardButton("Batalkan Pencarian", callback_data="search:cancel")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    query = update.callback_query
    if query:
        await query.edit_message_text(text=caption, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text=caption, reply_markup=reply_markup, parse_mode='Markdown')

async def search_start(update: Update, context: CallbackContext):
    await update.message.reply_text("Apa yang ingin dicari?")
    return GET_SEARCH_QUERY

async def search_get_query(update: Update, context: CallbackContext):
    context.user_data['search_query'] = update.message.text
    await _execute_and_send_search(update.effective_chat.id, context, is_new_search=True)
    if context.user_data.get('search_results'):
        await _display_search_page(update, context)
    return CHOOSE_FORMAT

async def search_navigation_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    action = query.data.split(':')[-1]
    page = context.user_data.get('search_page', 0)

    if action == 'next':
        context.user_data['search_page'] = page + 1
    elif action == 'prev':
        context.user_data['search_page'] = page - 1

    await _display_search_page(update, context)
    return CHOOSE_FORMAT

async def song_start(update: Update, context: CallbackContext):
    await update.message.reply_text("Kirimkan judul lagu.")
    return GET_SONG_TITLE

async def song_get_title(update: Update, context: CallbackContext):
    status_message = await update.message.reply_text("⏳ Mencari lagu...")
    try:
        search_query = f"ytmusic1:{update.message.text}"
        ydl_opts = {'quiet': True, 'noplaylist': True, 'match_filter': 'duration < 600'}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(search_query, download=False)
            if not result.get('entries'):
                await update.message.reply_text("Tidak ada lagu yang cocok dengan filter durasi.")
                if status_message: await status_message.delete()
                return ConversationHandler.END

        video_url = result['entries'][0]['webpage_url']
        if status_message: await status_message.delete()
        await download_media(video_url, 'audio', update.message)
    except Exception as e:
        logger.error(f"Song search failed for '{update.message.text}': {e}", exc_info=True)
        if status_message: await status_message.delete()
        await update.message.reply_text(f"❌ Gagal: Terjadi error saat mencari lagu.")

    return ConversationHandler.END

# ... (sisa fungsi enhance_photo dan convert_video tetap sama) ...
async def enhance_photo_start(update: Update, context: CallbackContext):
    await update.message.reply_text("Kirim foto (atau file gambar).")
    return GET_PHOTO
async def get_photo(update: Update, context: CallbackContext):
    file = await (update.message.photo[-1] if update.message.photo else update.message.document).get_file()
    os.makedirs('downloads', exist_ok=True)
    path = os.path.join('downloads', f"{uuid.uuid4()}.jpg")
    await file.download_to_drive(path)
    context.user_data['photo_path'] = path
    keyboard = [[InlineKeyboardButton("Tajamkan", callback_data="enhance:sharpen"), InlineKeyboardButton("Kontras", callback_data="enhance:contrast")]]
    await update.message.reply_text("Pilih peningkatan:", reply_markup=InlineKeyboardMarkup(keyboard))
    return GET_ENHANCEMENT
async def convert_video_start(update: Update, context: CallbackContext):
    await update.message.reply_text("Kirim video (atau file video).")
    return GET_VIDEO
async def get_video(update: Update, context: CallbackContext):
    file = await (update.message.video or update.message.document).get_file()
    os.makedirs('downloads', exist_ok=True)
    path = os.path.join('downloads', f"vid_{uuid.uuid4()}.mp4")
    await file.download_to_drive(path)
    context.user_data['video_path'] = path
    keyboard = [
        [InlineKeyboardButton("✨ Tingkatkan Kualitas", callback_data="convert:enhance_quality")],
        [InlineKeyboardButton("4k", callback_data="convert:4k"), InlineKeyboardButton("2k", callback_data="convert:2k")],
        [InlineKeyboardButton("1080p", callback_data="convert:1080p"), InlineKeyboardButton("720p", callback_data="convert:720p")]
    ]
    await update.message.reply_text("Pilih tindakan:", reply_markup=InlineKeyboardMarkup(keyboard))
    return GET_PROCESS_ACTION
async def download_callback_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    data_type, action, video_id = query.data.split(':')

    results = context.user_data.get('search_results', [])
    entry = next((item for item in results if item["id"] == video_id), None)

    if not entry:
        await query.message.reply_text("Error: Hasil tidak ditemukan atau sesi kedaluwarsa.")
        return CHOOSE_FORMAT # Tetap di state

    identifier = entry.get('url') or f"https://www.youtube.com/watch?v={video_id}"

    await query.message.reply_text(f"⏳ Memulai unduhan untuk *{entry.get('title')}*...", parse_mode='Markdown')
    await download_media(identifier, action, query.message)

    # Tidak mengakhiri conversation, agar bisa unduh yang lain dari halaman yang sama
    return CHOOSE_FORMAT
async def photo_enhancement_handler(update: Update, context: CallbackContext):
    # ...
    return ConversationHandler.END
async def video_processing_handler(update: Update, context: CallbackContext):
    # ...
    return ConversationHandler.END

def main():
    if not run_pre_flight_checks(): sys.exit(1)
    persistence = PicklePersistence(filepath="bot_persistence")
    app = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).persistence(persistence).post_init(post_init).build()

    conv_defaults = {'allow_reentry': True, 'conversation_timeout': 300, 'fallbacks': [CommandHandler("cancel", cancel)]}

    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("download", download_start)],
        states={GET_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, download_get_url)], CHOOSE_FORMAT: [CallbackQueryHandler(download_callback_handler, pattern="^dl_url:")]},
        **conv_defaults
    ))
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("search", search_start)],
        states={
            GET_SEARCH_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_get_query)],
            CHOOSE_FORMAT: [
                CallbackQueryHandler(download_callback_handler, pattern="^dl_search:"),
                CallbackQueryHandler(search_navigation_callback, pattern="^search:(next|prev)$"),
                CallbackQueryHandler(cancel, pattern="^search:cancel$"),
                CallbackQueryHandler(lambda u, c: u.callback_query.answer(), pattern="^search:noop$"),
            ],
        },
        **conv_defaults
    ))
    app.add_handler(ConversationHandler(entry_points=[CommandHandler("song", song_start)], states={GET_SONG_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, song_get_title)]}, **conv_defaults))
    app.add_handler(ConversationHandler(entry_points=[CommandHandler("enhance_photo", enhance_photo_start)], states={GET_PHOTO: [MessageHandler(filters.PHOTO | filters.Document.IMAGE, get_photo)], GET_ENHANCEMENT: [CallbackQueryHandler(photo_enhancement_handler, pattern="^enhance:")]}, **conv_defaults))
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("convert_video", convert_video_start)],
        states={
            GET_VIDEO: [MessageHandler(filters.VIDEO | filters.Document.VIDEO, get_video)],
            GET_PROCESS_ACTION: [CallbackQueryHandler(video_processing_handler, pattern="^convert:")]
        },
        **conv_defaults
    ))

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, start)) # Collect user IDs

    logger.info("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
