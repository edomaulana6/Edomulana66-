import logging
import os
import re
import uuid
import sys
import shutil
import time
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

# --- States ---
(
    GET_URL, GET_SEARCH_QUERY, GET_SONG_TITLE, GET_PHOTO,
    GET_ENHANCEMENT, GET_VIDEO, GET_PROCESS_ACTION, CHOOSE_FORMAT
) = range(8)

# --- Pre-flight Checks ---
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

# --- Main Logic ---
async def download_media(identifier: str, format_choice: str, effective_message, search_prefix: str = ""):
    status_message = await effective_message.reply_text("⏳ Memproses...")
    download_dir = 'downloads'
    os.makedirs(download_dir, exist_ok=True)

    ydl_opts = {
        'outtmpl': os.path.join(download_dir, '%(id)s.%(ext)s'),
        'noplaylist': True,
        'quiet': True
    }

    if format_choice == 'audio':
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}],
            'match_filter': 'duration < 600', # 10 minutes for songs
        })
        if search_prefix:
            ydl_opts['default_search'] = search_prefix
    else:
        ydl_opts.update({'format': 'bestvideo+bestaudio/best'})

    path, base_path = "", ""
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(identifier, download=True)
            if 'entries' in result:
                if not result['entries']:
                    raise IndexError("Tidak ada hasil yang cocok dengan filter.")
                info = result['entries'][0]
            else:
                info = result
            base_path = ydl.prepare_filename(info)

        path = os.path.splitext(base_path)[0] + '.mp3' if format_choice == 'audio' else base_path
        if not os.path.exists(path): raise FileNotFoundError(f"File not found: {path}")

        filename = f"{re.sub(r'[\\/*?:\"<>|]', '', info.get('title', 'media'))}.{'mp3' if format_choice == 'audio' else info.get('ext', 'mp4')}"

        with open(path, 'rb') as f:
            if format_choice == 'audio':
                await effective_message.reply_audio(f, title=info.get('title'), filename=filename, caption=info.get('title'))
            else:
                await effective_message.reply_video(f, filename=filename, caption=info.get('title'))
    except IndexError:
        await effective_message.reply_text("❌ Gagal: Tidak ada hasil yang cocok dengan filter (durasi < 10 menit).")
    except Exception as e:
        logger.error(f"Download failed for '{identifier}': {e}", exc_info=True)
        await effective_message.reply_text(f"❌ Gagal: Link tidak didukung atau error internal.")
    finally:
        if status_message: await status_message.delete()
        for p in [path, base_path]:
            if p and os.path.exists(p): os.remove(p)

async def cancel(update: Update, context: CallbackContext):
    for key in ['photo_path', 'video_path']: context.user_data.pop(key, None)
    await update.message.reply_text("Operasi dibatalkan.")
    return ConversationHandler.END

# --- Commands ---
async def start(update: Update, context: CallbackContext):
    await update.message.reply_html(f"👋 Halo {update.effective_user.mention_html()}! /help untuk bantuan.")

async def help_command(update: Update, context: CallbackContext):
    await update.message.reply_markdown(
        "*Perintah Bot Interaktif*\n\n"
        "`/search` - Cari media.\n`/song` - Unduh lagu.\n`/download` - Unduh dari URL.\n"
        "`/enhance_photo` - Tingkatkan kualitas foto.\n`/convert_video` - Proses video.\n"
        "`/cancel` - Batalkan perintah."
    )

# --- Conversation Entry Points & Handlers ---
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
        thumbnail_url = info.get('thumbnail')
        caption = f"Pilih format untuk:\n*{info.get('title')}*"
        if thumbnail_url:
            await update.message.reply_photo(photo=thumbnail_url, caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            await update.message.reply_text(caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"Gagal memproses URL: {e}")
        return ConversationHandler.END
    return CHOOSE_FORMAT

async def _execute_and_send_search(effective_message, context: CallbackContext):
    query = context.user_data.get('search_query')
    page = context.user_data.get('search_page', 1)

    if not query:
        await effective_message.reply_text("Error: Sesi pencarian kedaluwarsa.")
        return

    num_to_fetch = page * 5
    search_query = f"ytsearch{num_to_fetch}:{query}"

    ydl_opts = {
        'quiet': True,
        'noplaylist': True,
        'match_filter': 'duration < 1800'
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(search_query, download=False)

        all_entries = result.get('entries', [])

        start_index = (page - 1) * 5
        page_entries = all_entries[start_index:]

        if not page_entries:
            await effective_message.reply_text("Tidak ada hasil lagi.")
            return

        for entry in page_entries:
            context.user_data[f"search_{entry['id']}"] = {'url': entry['webpage_url'], 'title': entry['title']}
            keyboard = [[InlineKeyboardButton("🎧 Audio", callback_data=f"dl_search:audio:{entry['id']}"), InlineKeyboardButton("🎬 Video", callback_data=f"dl_search:video:{entry['id']}")]]
            thumbnail_url = entry.get('thumbnail')
            caption = f"*{entry['title']}*"

            try:
                if thumbnail_url:
                    await effective_message.reply_photo(photo=thumbnail_url, caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
                else:
                    await effective_message.reply_text(caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            except Exception as e:
                logger.warning(f"Could not send thumbnail for {entry['id']} ({thumbnail_url}): {e}. Sending as text.")
                await effective_message.reply_text(caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

        if len(all_entries) == num_to_fetch:
            keyboard = [[InlineKeyboardButton("Lebih Banyak", callback_data="search:more")]]
            await effective_message.reply_text(
                "Tampilkan lebih banyak?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    except Exception as e:
        await effective_message.reply_text(f"Gagal mencari: {e}")

async def search_start(update: Update, context: CallbackContext):
    await update.message.reply_text("Apa yang ingin dicari?")
    return GET_SEARCH_QUERY

async def search_get_query(update: Update, context: CallbackContext):
    context.user_data['search_query'] = update.message.text
    context.user_data['search_page'] = 1
    await _execute_and_send_search(update.message, context)
    return CHOOSE_FORMAT

async def song_start(update: Update, context: CallbackContext):
    await update.message.reply_text("Kirimkan judul lagu.")
    return GET_SONG_TITLE

async def song_get_title(update: Update, context: CallbackContext):
    await download_media(update.message.text, 'audio', update.message, search_prefix='ytmusic1')
    return ConversationHandler.END

async def enhance_photo_start(update: Update, context: CallbackContext):
    await update.message.reply_text("Kirim foto (atau file gambar).")
    return GET_PHOTO

async def get_photo(update: Update, context: CallbackContext):
    photo_obj = update.message.photo[-1] if update.message.photo else update.message.document
    file = await photo_obj.get_file()
    os.makedirs('downloads', exist_ok=True)
    path = os.path.join('downloads', f"{uuid.uuid4()}.jpg")
    await file.download_to_drive(path)
    context.user_data['photo_path'] = path
    keyboard = [[InlineKeyboardButton("Tajamkan", callback_data="enhance:sharpen"), InlineKeyboardButton("Kontras", callback_data="enhance:contrast")]]
    await update.message.reply_text("Pilih peningkatan:", reply_markup=InlineKeyboardMarkup(keyboard))
    return GET_ENHANCEMENT

import subprocess

def generate_thumbnail(video_path, thumbnail_path):
    """Generates a thumbnail from the video file."""
    try:
        # Attempt to capture a frame from the first few seconds of the video.
        command = ['ffmpeg', '-i', video_path, '-ss', '00:00:01.500', '-vframes', '1', '-y', thumbnail_path]
        subprocess.run(command, check=True, capture_output=True, text=True)
        return os.path.exists(thumbnail_path)
    except subprocess.CalledProcessError as e:
        logger.error(f"Thumbnail generation failed for {video_path}: {e.stderr}")
        return False

async def convert_video_start(update: Update, context: CallbackContext):
    await update.message.reply_text("Kirim video (atau file video).")
    return GET_VIDEO

async def get_video(update: Update, context: CallbackContext):
    video_obj = update.message.video or update.message.document
    if not video_obj:
        await update.message.reply_text("Ini bukan video. Kirim file video atau /cancel.")
        return GET_VIDEO

    file = await video_obj.get_file()
    os.makedirs('downloads', exist_ok=True)
    path = os.path.join('downloads', f"vid_{video_obj.file_name or f'{uuid.uuid4()}.mp4'}")
    await file.download_to_drive(path)
    context.user_data['video_path'] = path

    keyboard = [
        [InlineKeyboardButton("✨ Tingkatkan Kualitas", callback_data="convert:enhance_quality")],
        [InlineKeyboardButton("4k", callback_data="convert:4k"), InlineKeyboardButton("2k", callback_data="convert:2k")],
        [InlineKeyboardButton("1080p", callback_data="convert:1080p"), InlineKeyboardButton("720p", callback_data="convert:720p")]
    ]

    thumbnail_path = os.path.join('downloads', f"{uuid.uuid4()}.jpg")
    if generate_thumbnail(path, thumbnail_path):
        context.user_data['thumbnail_path'] = thumbnail_path
        with open(thumbnail_path, 'rb') as thumb:
            await update.message.reply_photo(
                photo=thumb,
                caption="Pilih tindakan:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    else:
        await update.message.reply_text(
            "Pilih tindakan:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    return GET_PROCESS_ACTION

async def search_more_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    await query.message.delete()

    context.user_data['search_page'] = context.user_data.get('search_page', 1) + 1
    await _execute_and_send_search(query.message, context)
    return CHOOSE_FORMAT

# --- Callback Handlers ---
async def download_callback_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    data_type, action, *rest = query.data.split(':')

    info, identifier = (context.user_data.get('url_info'), context.user_data.get('url_info', {}).get('url')) if data_type == 'dl_url' else \
                       (context.user_data.get(f"search_{rest[0]}"), context.user_data.get(f"search_{rest[0]}", {}).get('url'))

    if not info or not identifier:
        await query.edit_message_text("Error: Sesi kedaluwarsa.")
        return ConversationHandler.END

    try:
        await query.edit_message_caption(caption=f"Mengunduh *{info.get('title', '')}*...", reply_markup=None, parse_mode='Markdown')
    except Exception:
        await query.edit_message_text(text=f"Mengunduh *{info.get('title', '')}*...", reply_markup=None, parse_mode='Markdown')

    await download_media(identifier, action, query.message)
    await query.message.delete()
    return ConversationHandler.END

async def photo_enhancement_handler(update: Update, context: CallbackContext):
    query, path = update.callback_query, context.user_data.get('photo_path')
    await query.answer()
    if not path: return await query.edit_message_text("Error: File tidak ditemukan.")

    await query.edit_message_text(f"Memproses...")
    enhanced_path = ""
    try:
        enhanced_path = enhance_photo(path, query.data.split(':')[1])
        with open(enhanced_path, 'rb') as f: await query.message.reply_document(f)
    finally:
        for p in [path, enhanced_path]:
            if p and os.path.exists(p): os.remove(p)
        context.user_data.pop('photo_path', None)

    await query.edit_message_text("Selesai!")
    return ConversationHandler.END

async def video_processing_handler(update: Update, context: CallbackContext):
    query, action, path = update.callback_query, update.callback_query.data.split(':')[1], context.user_data.get('video_path')
    await query.answer()
    if not path: return await query.edit_message_text("Error: File video tidak ditemukan.")

    processed_path, thumb_path = "", context.user_data.get('thumbnail_path')
    try:
        if action == 'enhance_quality':
            await query.edit_message_caption(caption="✨ Meningkatkan kualitas...")
            processed_path, caption = enhance_video_quality(path), "Kualitas video ditingkatkan."
        else:
            await query.edit_message_caption(caption=f"🎬 Mengonversi ke {action}...")
            processed_path, caption = convert_video_resolution(path, action), f"Video dikonversi ke {action}."

        with open(processed_path, 'rb') as f: await query.message.reply_video(f)
    except Exception as e:
        await query.edit_message_caption(caption=f"Gagal memproses video: {e}")
    finally:
        for p in [path, processed_path, thumb_path]:
            if p and os.path.exists(p): os.remove(p)
        context.user_data.pop('video_path', None)
        context.user_data.pop('thumbnail_path', None)

    await query.message.delete()
    return ConversationHandler.END

# --- Main Setup ---
def main():
    if not run_pre_flight_checks(): sys.exit(1)

    app = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).persistence(PicklePersistence(filepath="bot_persistence")).build()
    conv_defaults = {'allow_reentry': True, 'conversation_timeout': 300, 'fallbacks': [CommandHandler("cancel", cancel)]}

    download_conv = ConversationHandler(
        entry_points=[CommandHandler("download", download_start)],
        states={
            GET_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, download_get_url)],
            CHOOSE_FORMAT: [CallbackQueryHandler(download_callback_handler, pattern="^dl_url:")],
        },
        **conv_defaults
    )
    search_conv = ConversationHandler(
        entry_points=[CommandHandler("search", search_start)],
        states={
            GET_SEARCH_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_get_query)],
            CHOOSE_FORMAT: [
                CallbackQueryHandler(download_callback_handler, pattern="^dl_search:"),
                CallbackQueryHandler(search_more_callback, pattern="^search:more$")
            ],
        },
        **conv_defaults
    )

    app.add_handler(download_conv)
    app.add_handler(search_conv)
    app.add_handler(ConversationHandler(entry_points=[CommandHandler("song", song_start)], states={GET_SONG_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, song_get_title)]}, **conv_defaults))
    app.add_handler(ConversationHandler(entry_points=[CommandHandler("enhance_photo", enhance_photo_start)], states={GET_PHOTO: [MessageHandler(filters.PHOTO | filters.Document.IMAGE, get_photo)], GET_ENHANCEMENT: [CallbackQueryHandler(photo_enhancement_handler, pattern="^enhance:")]}, **conv_defaults))
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("convert_video", convert_video_start)],
        states={
            GET_VIDEO: [MessageHandler(filters.VIDEO | filters.Document.VIDEO, get_video)],
            GET_PROCESS_ACTION: [CallbackQueryHandler(video_processing_handler, pattern="^convert:")],
        },
        **conv_defaults
    ))

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    logger.info("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
