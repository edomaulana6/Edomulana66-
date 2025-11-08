import logging
import os
import re
import uuid
import sys
import shutil
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

# --- Conversation States ---
(
    GET_URL, GET_SEARCH_QUERY, GET_SONG_TITLE, GET_PHOTO,
    GET_ENHANCEMENT, GET_VIDEO, GET_PROCESS_ACTION
) = range(7)

# --- Pre-flight Checks ---
def run_pre_flight_checks():
    logger.info("--- 🩺 Running Pre-flight Checks ---")
    if not (os.getenv("TELEGRAM_TOKEN") and os.getenv("TELEGRAM_TOKEN") != "GANTI_DENGAN_TOKEN_ANDA"):
        logger.critical("FATAL: TELEGRAM_TOKEN is not configured in .env file.")
        return False
    if not shutil.which("ffmpeg"):
        logger.critical("FATAL: ffmpeg is not installed or not in PATH.")
        return False
    logger.info("[✅] All checks passed. Bot is ready.")
    return True

# --- Main Logic & Helpers ---
async def download_media(identifier: str, format_choice: str, effective_message):
    status_message = await effective_message.reply_text("⏳ Memproses permintaan Anda...")
    download_dir = 'downloads'
    os.makedirs(download_dir, exist_ok=True)

    ydl_opts = {'outtmpl': os.path.join(download_dir, '%(id)s.%(ext)s'), 'noplaylist': True, 'quiet': True}
    if format_choice == 'audio':
        ydl_opts.update({'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}]})
    else:
        ydl_opts.update({'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'})

    final_path, base_path = "", ""
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(identifier, download=True)
            base_path = ydl.prepare_filename(info_dict)

        final_path = os.path.splitext(base_path)[0] + '.mp3' if format_choice == 'audio' else base_path
        if not os.path.exists(final_path): raise FileNotFoundError(f"File not found after download: {final_path}")

        sanitized_title = re.sub(r'[\\/*?:"<>|]', "", info_dict.get('title', 'media'))
        ext = 'mp3' if format_choice == 'audio' else info_dict.get('ext', 'mp4')
        filename = f"{sanitized_title}.{ext}"

        with open(final_path, 'rb') as file_to_send:
            if format_choice == 'audio':
                await effective_message.reply_audio(audio=file_to_send, title=info_dict.get('title'), filename=filename, caption=info_dict.get('title'))
            else:
                await effective_message.reply_video(video=file_to_send, filename=filename, caption=info_dict.get('title'))
    except Exception as e:
        logger.error(f"Download failed for '{identifier}': {e}", exc_info=True)
        await effective_message.reply_text(f"❌ Gagal memproses permintaan Anda. Link mungkin tidak didukung atau terjadi error internal.")
    finally:
        if status_message: await status_message.delete()
        for path in [final_path, base_path]:
            if path and os.path.exists(path): os.remove(path)

async def cancel(update: Update, context: CallbackContext):
    for key in ['photo_path', 'video_path']:
        context.user_data.pop(key, None)
    await update.message.reply_text("Operasi dibatalkan.")
    return ConversationHandler.END

async def start(update: Update, context: CallbackContext):
    await update.message.reply_html(f"👋 Halo {update.effective_user.mention_html()}! Gunakan /help untuk melihat daftar perintah.")

async def help_command(update: Update, context: CallbackContext):
    await update.message.reply_markdown(
        "*Perintah Bot Interaktif*\n\n"
        "`/search` - Cari video/audio dari YouTube.\n"
        "`/song` - Cari dan unduh lagu dari YouTube.\n"
        "`/download` - Unduh dari URL (YT, IG, dll).\n"
        "`/enhance_photo` - Tingkatkan kualitas foto.\n"
        "`/convert_video` - Proses video (ubah resolusi/tingkatkan kualitas).\n"
        "`/cancel` - Batalkan perintah saat ini."
    )

# --- Conversation Entry Points & Handlers ---
async def download_start(update: Update, context: CallbackContext):
    await update.message.reply_text("Kirimkan URL untuk diunduh.")
    return GET_URL

async def download_get_url(update: Update, context: CallbackContext):
    url = update.message.text
    if not re.match(r'https?://\S+', url):
        await update.message.reply_text("URL tidak valid. Coba lagi atau /cancel.")
        return GET_URL

    try:
        await update.message.reply_text(f"🔎 Memproses URL...")
        with yt_dlp.YoutubeDL({'quiet': True, 'noplaylist': True}) as ydl:
            info = ydl.extract_info(url, download=False)

        context.user_data['url_info'] = {'url': url, 'title': info.get('title', 'Tanpa Judul')}
        keyboard = [[
            InlineKeyboardButton("🎧 Audio", callback_data=f"dl_url:audio"),
            InlineKeyboardButton("🎬 Video", callback_data=f"dl_url:video"),
        ]]
        await update.message.reply_text(f"Pilih format untuk:\n*{info.get('title')}*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"Gagal memproses URL: {e}")
    return ConversationHandler.END

async def search_start(update: Update, context: CallbackContext):
    await update.message.reply_text("Apa yang ingin Anda cari?")
    return GET_SEARCH_QUERY

async def search_get_query(update: Update, context: CallbackContext):
    query = update.message.text
    await update.message.reply_text(f"🔎 Mencari *{query}*...", parse_mode='Markdown')
    try:
        with yt_dlp.YoutubeDL({'default_search': 'ytsearch5', 'quiet': True, 'noplaylist': True}) as ydl:
            result = ydl.extract_info(query, download=False)

        if not result.get('entries'):
            await update.message.reply_text("Tidak ada hasil ditemukan.")
            return ConversationHandler.END

        for entry in result['entries'][:5]:
            context.user_data[f"search_{entry['id']}"] = {'url': entry['webpage_url'], 'title': entry['title']}
            keyboard = [[
                InlineKeyboardButton("🎧 Audio", callback_data=f"dl_search:audio:{entry['id']}"),
                InlineKeyboardButton("🎬 Video", callback_data=f"dl_search:video:{entry['id']}"),
            ]]
            await update.message.reply_text(f"*{entry['title']}*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"Gagal melakukan pencarian: {e}")
    return ConversationHandler.END

async def song_start(update: Update, context: CallbackContext):
    await update.message.reply_text("Kirimkan judul lagu.")
    return GET_SONG_TITLE

async def song_get_title(update: Update, context: CallbackContext):
    await download_media(f"ytsearch1:{update.message.text}", 'audio', update.message)
    return ConversationHandler.END

async def enhance_photo_start(update: Update, context: CallbackContext):
    await update.message.reply_text("Kirim foto (atau file gambar untuk kualitas asli).")
    return GET_PHOTO

async def get_photo(update: Update, context: CallbackContext):
    photo_obj = update.message.photo[-1] if update.message.photo else update.message.document
    file = await photo_obj.get_file()
    os.makedirs('downloads', exist_ok=True)
    path = os.path.join('downloads', f"{uuid.uuid4()}.jpg")
    await file.download_to_drive(path)
    context.user_data['photo_path'] = path

    keyboard = [[
        InlineKeyboardButton("Tajamkan", callback_data="enhance:sharpen"),
        InlineKeyboardButton("Kontras", callback_data="enhance:contrast"),
    ]]
    await update.message.reply_text("Pilih jenis peningkatan:", reply_markup=InlineKeyboardMarkup(keyboard))
    return GET_ENHANCEMENT

async def convert_video_start(update: Update, context: CallbackContext):
    await update.message.reply_text("Kirim video (atau file video untuk kualitas asli).")
    return GET_VIDEO

async def get_video(update: Update, context: CallbackContext):
    video_obj = None
    if update.message.video:
        video_obj = update.message.video
    elif update.message.document and 'video' in (update.message.document.mime_type or ''):
        video_obj = update.message.document
    else:
        await update.message.reply_text("Ini bukan video. Kirim file video atau /cancel.")
        return GET_VIDEO

    file = await video_obj.get_file()
    os.makedirs('downloads', exist_ok=True)
    filename = video_obj.file_name or f"{uuid.uuid4()}.mp4"
    path = os.path.join('downloads', f"vid_{filename}")
    await file.download_to_drive(path)
    context.user_data['video_path'] = path

    keyboard = [[
        InlineKeyboardButton("✨ Tingkatkan Kualitas", callback_data="convert:enhance_quality"),
        InlineKeyboardButton("1080p", callback_data="convert:1080p"),
        InlineKeyboardButton("720p", callback_data="convert:720p"),
        InlineKeyboardButton("480p", callback_data="convert:480p"),
    ]]
    await update.message.reply_text("Pilih tindakan untuk video:", reply_markup=InlineKeyboardMarkup(keyboard))
    return GET_PROCESS_ACTION

# --- Callback Handlers ---
async def download_callback_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    data_type, action, *rest = query.data.split(':')
    identifier = ""

    if data_type == 'dl_url':
        info = context.user_data.get('url_info')
        if not info: return await query.edit_message_text("Error: Sesi unduh kedaluwarsa.")
        identifier = info['url']

    elif data_type == 'dl_search':
        video_id = rest[0]
        info = context.user_data.get(f"search_{video_id}")
        if not info: return await query.edit_message_text("Error: Sesi pencarian kedaluwarsa.")
        identifier = info['url']

    await query.edit_message_text(f"Mengunduh *{info.get('title', '')}*...", parse_mode='Markdown')
    await download_media(identifier, action, query.message)

async def photo_enhancement_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    enhancement_type = query.data.split(':')[1]
    path = context.user_data.get('photo_path')
    if not path: return await query.edit_message_text("Error: File foto tidak ditemukan.")

    await query.edit_message_text(f"Memproses {enhancement_type}...")
    enhanced_path = ""
    try:
        enhanced_path = enhance_photo(path, enhancement_type)
        with open(enhanced_path, 'rb') as f:
            await query.message.reply_document(f)
    finally:
        if os.path.exists(path): os.remove(path)
        if os.path.exists(enhanced_path): os.remove(enhanced_path)
        context.user_data.pop('photo_path', None)

    await query.edit_message_text("Selesai!")
    return ConversationHandler.END

async def video_processing_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    action = query.data.split(':')[1]
    path = context.user_data.get('video_path')
    if not path: return await query.edit_message_text("Error: File video tidak ditemukan.")

    processed_path = ""
    try:
        if action == 'enhance_quality':
            await query.edit_message_text("✨ Meningkatkan kualitas video...")
            processed_path = enhance_video_quality(path)
            caption = "Kualitas video ditingkatkan."
        else:
            await query.edit_message_text(f"🎬 Mengonversi ke {action}...")
            processed_path = convert_video_resolution(path, action)
            caption = f"Video dikonversi ke {action}."

        with open(processed_path, 'rb') as f:
            await query.message.reply_video(f, caption=caption)
    except Exception as e:
        await query.edit_message_text(f"Gagal memproses video: {e}")
    finally:
        if os.path.exists(path): os.remove(path)
        if os.path.exists(processed_path): os.remove(processed_path)
        context.user_data.pop('video_path', None)

    await query.message.delete()
    return ConversationHandler.END

# --- Main Application Setup ---
def main():
    if not run_pre_flight_checks(): sys.exit(1)

    persistence = PicklePersistence(filepath="bot_persistence")
    application = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).persistence(persistence).build()

    conv_defaults = {'allow_reentry': True, 'conversation_timeout': 300}

    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler("download", download_start)],
        states={GET_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, download_get_url)]},
        fallbacks=[CommandHandler("cancel", cancel)], **conv_defaults
    ))
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler("search", search_start)],
        states={GET_SEARCH_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_get_query)]},
        fallbacks=[CommandHandler("cancel", cancel)], **conv_defaults
    ))
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler("song", song_start)],
        states={GET_SONG_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, song_get_title)]},
        fallbacks=[CommandHandler("cancel", cancel)], **conv_defaults
    ))
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler("enhance_photo", enhance_photo_start)],
        states={
            GET_PHOTO: [MessageHandler(filters.PHOTO | filters.Document.IMAGE, get_photo)],
            GET_ENHANCEMENT: [CallbackQueryHandler(photo_enhancement_handler, pattern="^enhance:")],
        },
        fallbacks=[CommandHandler("cancel", cancel)], **conv_defaults
    ))
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler("convert_video", convert_video_start)],
        states={
            GET_VIDEO: [MessageHandler(filters.VIDEO | filters.Document.MimeType("video/*"), get_video)],
            GET_PROCESS_ACTION: [CallbackQueryHandler(video_processing_handler, pattern="^convert:")],
        },
        fallbacks=[CommandHandler("cancel", cancel)], **conv_defaults
    ))

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(download_callback_handler, pattern="^dl_"))

    logger.info("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
