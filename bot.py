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

# --- Local Imports ---
from image_enhancer import enhance_photo
from video_converter import convert_video_resolution, enhance_video_quality

# --- Initial Setup ---
load_dotenv()
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Conversation States ---
(
    GET_DOWNLOAD_URL, GET_SEARCH_QUERY, GET_SONG_TITLE, GET_PHOTO,
    GET_ENHANCEMENT, GET_VIDEO, GET_RESOLUTION
) = range(7)

# --- Pre-flight Checks ---
def run_pre_flight_checks() -> bool:
    logger.info("--- 🩺 Running Bot Pre-flight Checks 🩺 ---")
    token = os.getenv("TELEGRAM_TOKEN")
    if not token or token == "GANTI_DENGAN_TOKEN_ANDA":
        logger.error(" [❌] FATAL: TELEGRAM_TOKEN is not set or is a placeholder.")
        return False
    logger.info("[✅] Token Check: Passed")

    if not shutil.which("ffmpeg"):
        logger.error(" [❌] FATAL: ffmpeg is not installed or not in PATH.")
        return False
    logger.info("[✅] FFmpeg Check: Passed")

    logger.info("[🎉] All pre-flight checks passed! Bot is ready.")
    return True

# --- Helper Functions ---
async def perform_search(query: str, update: Update, context: CallbackContext):
    await update.message.reply_text(f"🔎 Mencari 5 teratas untuk: *{query}*...", parse_mode='Markdown')
    ydl_opts = {'format': 'bestaudio/best', 'noplaylist': True, 'quiet': True, 'default_search': 'ytsearch5'}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(query, download=False)
            videos = [v for v in result.get('entries', []) if v]

            if not videos:
                await update.message.reply_text("Tidak ada media yang ditemukan.")
                return

            await update.message.reply_text("Menampilkan hasil:")
            for video in videos[:5]:
                video_id = video.get('id')
                title = video.get('title', 'Tanpa Judul')
                duration = f"{video.get('duration', 0) // 60}:{video.get('duration', 0) % 60:02d}"
                caption = f"🎵 *{title}*\n⏱️ Durasi: {duration}"
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("🎧 Audio", callback_data=f"dl_search:audio:{video_id}"),
                    InlineKeyboardButton("🎬 Video", callback_data=f"dl_search:video:{video_id}"),
                ]])
                if thumbnail := video.get('thumbnail'):
                    await update.message.reply_photo(photo=thumbnail, caption=caption, reply_markup=keyboard, parse_mode='Markdown')
                else:
                    await update.message.reply_text(caption, reply_markup=keyboard, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error during yt-dlp search: {e}", exc_info=True)
        await update.message.reply_text("Maaf, terjadi kesalahan saat melakukan pencarian.")

async def download_file(identifier: str, format_choice: str, update: Update, context: CallbackContext):
    effective_update = update.callback_query or update.message
    url = identifier if re.match(r'https?://', identifier) else f"https://www.youtube.com/watch?v={identifier}"
    download_dir = 'downloads'
    os.makedirs(download_dir, exist_ok=True)

    ydl_opts = {
        'outtmpl': os.path.join(download_dir, '%(id)s.%(ext)s'),
        'noplaylist': True, 'quiet': True, 'noprogress': True
    }
    if format_choice == 'audio':
        ydl_opts.update({'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]})
    else:
        ydl_opts.update({'format': 'best'})

    final_path, base_path = "", ""
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            base_path = ydl.prepare_filename(info_dict)

        final_path = os.path.splitext(base_path)[0] + '.mp3' if format_choice == 'audio' else base_path
        if not os.path.exists(final_path):
            if os.path.exists(base_path): final_path = base_path
            else: raise FileNotFoundError(f"Downloaded file not found at expected paths: {final_path} or {base_path}")

        caption_text = info_dict.get('title', 'File')
        sanitized_title = re.sub(r'[\\/*?:"<>|]', "", caption_text)
        file_extension = 'mp3' if format_choice == 'audio' else info_dict.get('ext', 'mp4')
        filename = f"{sanitized_title}.{file_extension}"

        with open(final_path, 'rb') as file_to_send:
            if format_choice == 'audio':
                await effective_update.message.reply_audio(audio=file_to_send, caption=caption_text, title=caption_text, filename=filename)
            else:
                await effective_update.message.reply_video(video=file_to_send, caption=caption_text, filename=filename)
    finally:
        if os.path.exists(final_path): os.remove(final_path)
        if base_path and base_path != final_path and os.path.exists(base_path): os.remove(base_path)

# --- Universal Cancel Function ---
async def cancel(update: Update, context: CallbackContext) -> int:
    if 'photo_path' in context.user_data: del context.user_data['photo_path']
    if 'video_path' in context.user_data: del context.user_data['video_path']
    await update.message.reply_text("Operasi dibatalkan.")
    return ConversationHandler.END

# --- Standard Commands ---
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_html(f"👋 Halo {update.effective_user.mention_html()}! Gunakan `/help` untuk bantuan.")

async def help_command(update: Update, context: CallbackContext) -> None:
    await update.message.reply_markdown(
        "*Bantuan Perintah Interaktif*\n\n"
        "`/search` - Cari media di YouTube.\n"
        "`/song` - Unduh lagu dari YouTube.\n"
        "`/download` - Unduh dari URL (YouTube, Instagram, dll).\n"
        "`/enhance_photo` - Tingkatkan kualitas foto.\n"
        "`/convert_video` - Ubah resolusi atau tingkatkan kualitas video.\n"
        "`/cancel` - Batalkan perintah yang sedang berjalan."
    )

# --- Download from URL ---
async def download_start(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Silakan kirimkan URL yang ingin Anda unduh.")
    return GET_DOWNLOAD_URL

async def download_get_url(update: Update, context: CallbackContext) -> int:
    url = update.message.text
    if not re.match(r'https?://\S+', url):
        await update.message.reply_text("URL tidak valid. Silakan kirimkan URL yang benar atau batalkan dengan /cancel.")
        return GET_DOWNLOAD_URL

    message = await update.message.reply_text(f"🔎 Memproses URL...")
    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'noplaylist': True}) as ydl:
            info = ydl.extract_info(url, download=False)

        key = str(uuid.uuid4())
        context.user_data[key] = url
        caption = f"🎬 *{info.get('title', 'Tanpa Judul')}*"
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🎧 Audio", callback_data=f"dl_url:audio:{key}"),
            InlineKeyboardButton("🎬 Video", callback_data=f"dl_url:video:{key}"),
        ]])

        await message.delete()
        if thumbnail := info.get('thumbnail'):
            await update.message.reply_photo(photo=thumbnail, caption=caption, reply_markup=keyboard, parse_mode='Markdown')
        else:
            await update.message.reply_text(caption, reply_markup=keyboard, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error processing URL {url}: {e}", exc_info=True)
        await message.edit_text("Gagal memproses URL. Pastikan link didukung.")

    return ConversationHandler.END

# --- Search Command ---
async def search_start(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Apa yang ingin Anda cari?")
    return GET_SEARCH_QUERY

async def search_get_query(update: Update, context: CallbackContext) -> int:
    await perform_search(update.message.text, update, context)
    return ConversationHandler.END

# --- Song Command ---
async def song_start(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Silakan kirimkan judul lagu yang ingin Anda unduh.")
    return GET_SONG_TITLE

async def song_get_title(update: Update, context: CallbackContext) -> int:
    message = await update.message.reply_text(f"🔎 Mencari & mengunduh: *{update.message.text}*...", parse_mode='Markdown')
    await download_file(f"ytsearch1:{update.message.text}", 'audio', update, context)
    await message.delete()
    return ConversationHandler.END

# --- Photo Enhancement ---
async def enhance_photo_start(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Silakan kirim foto yang ingin ditingkatkan (bisa sebagai file untuk kualitas asli).")
    return GET_PHOTO

async def get_photo(update: Update, context: CallbackContext) -> int:
    photo_obj = update.message.photo[-1] if update.message.photo else update.message.document
    photo_file = await photo_obj.get_file()

    download_dir = 'downloads'
    os.makedirs(download_dir, exist_ok=True)
    photo_path = os.path.join(download_dir, f"{uuid.uuid4()}.jpg")
    await photo_file.download_to_drive(photo_path)
    context.user_data['photo_path'] = photo_path

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Tajamkan", callback_data="enhance:sharpen")],
        [InlineKeyboardButton("Kontras", callback_data="enhance:contrast")],
    ])
    await update.message.reply_text("Pilih jenis peningkatan:", reply_markup=keyboard)
    return GET_ENHANCEMENT

async def apply_enhancement(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    enhancement_type = query.data.split(':')[1]
    photo_path = context.user_data.get('photo_path')

    if not photo_path or not os.path.exists(photo_path):
        await query.edit_message_text("Maaf, file foto tidak ditemukan. Silakan mulai lagi.")
        return ConversationHandler.END

    await query.edit_message_text(f"Menerapkan peningkatan {enhancement_type}...")
    enhanced_path = ""
    try:
        enhanced_path = enhance_photo(photo_path, enhancement_type)
        with open(enhanced_path, 'rb') as photo_file:
            await query.message.reply_document(document=photo_file)
        await query.edit_message_text("Berikut adalah foto yang telah ditingkatkan:")
    except Exception as e:
        logger.error(f"Error during photo enhancement: {e}", exc_info=True)
        await query.edit_message_text("Maaf, terjadi kesalahan saat meningkatkan foto.")
    finally:
        if os.path.exists(photo_path): os.remove(photo_path)
        if enhanced_path and os.path.exists(enhanced_path): os.remove(enhanced_path)
        if 'photo_path' in context.user_data: del context.user_data['photo_path']

    return ConversationHandler.END

# --- Video Conversion ---
async def convert_video_start(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Silakan kirim video yang ingin diproses (bisa sebagai file untuk kualitas asli).")
    return GET_VIDEO

async def get_video(update: Update, context: CallbackContext) -> int:
    if update.message.video:
        video_file_obj = update.message.video
    elif update.message.document and 'video' in update.message.document.mime_type:
        video_file_obj = update.message.document
    else:
        await update.message.reply_text("File tidak valid. Kirim video atau file video, atau batalkan dengan /cancel.")
        return GET_VIDEO

    video_file = await video_file_obj.get_file()
    download_dir = 'downloads'
    os.makedirs(download_dir, exist_ok=True)
    original_filename = video_file_obj.file_name or f"video_{uuid.uuid4()}.mp4"
    video_path = os.path.join(download_dir, f"{uuid.uuid4()}_{original_filename}")

    await video_file.download_to_drive(video_path)
    context.user_data['video_path'] = video_path

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ Tingkatkan Kualitas", callback_data="convert:enhance_quality")],
        [InlineKeyboardButton("1080p", callback_data="convert:1080p"), InlineKeyboardButton("720p", callback_data="convert:720p")],
        [InlineKeyboardButton("480p", callback_data="convert:480p"), InlineKeyboardButton("360p", callback_data="convert:360p")],
    ])
    await update.message.reply_text("Pilih tindakan untuk video:", reply_markup=keyboard)
    return GET_RESOLUTION

async def apply_conversion(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    action = query.data.split(':')[1]
    video_path = context.user_data.get('video_path')

    if not video_path or not os.path.exists(video_path):
        await query.edit_message_text("Maaf, file video tidak ditemukan. Silakan mulai lagi.")
        return ConversationHandler.END

    processed_path = ""
    try:
        if action == "enhance_quality":
            await query.edit_message_text("✨ Meningkatkan kualitas video, ini bisa memakan waktu lama...")
            processed_path = enhance_video_quality(video_path)
            caption = "Kualitas video telah ditingkatkan."
        else:
            await query.edit_message_text(f"Mengonversi video ke {action}...")
            processed_path = convert_video_resolution(video_path, action)
            caption = f"Video dikonversi ke {action}."

        with open(processed_path, 'rb') as video_file:
            await query.message.reply_video(video=video_file, caption=caption)
        await query.delete_message()
    except Exception as e:
        logger.error(f"Error during video processing: {e}", exc_info=True)
        await query.edit_message_text("Maaf, terjadi kesalahan saat memproses video. File mungkin rusak.")
    finally:
        if os.path.exists(video_path): os.remove(video_path)
        if processed_path and os.path.exists(processed_path): os.remove(processed_path)
        if 'video_path' in context.user_data: del context.user_data['video_path']

    return ConversationHandler.END

# --- Main Application Setup ---
def main() -> None:
    if not run_pre_flight_checks():
        sys.exit(1)

    persistence = PicklePersistence(filepath="bot_persistence")
    application = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).persistence(persistence).build()

    # --- Conversation Handlers ---
    conv_handler_defaults = {'allow_reentry': True, 'conversation_timeout': 300}

    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler("download", download_start)],
        states={GET_DOWNLOAD_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, download_get_url)]},
        fallbacks=[CommandHandler("cancel", cancel)], **conv_handler_defaults
    ))
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler("search", search_start)],
        states={GET_SEARCH_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_get_query)]},
        fallbacks=[CommandHandler("cancel", cancel)], **conv_handler_defaults
    ))
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler("song", song_start)],
        states={GET_SONG_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, song_get_title)]},
        fallbacks=[CommandHandler("cancel", cancel)], **conv_handler_defaults
    ))
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler("enhance_photo", enhance_photo_start)],
        states={
            GET_PHOTO: [MessageHandler(filters.PHOTO | filters.Document.IMAGE, get_photo)],
            GET_ENHANCEMENT: [CallbackQueryHandler(apply_enhancement, pattern="^enhance:")],
        },
        fallbacks=[CommandHandler("cancel", cancel)], **conv_handler_defaults
    ))
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler("convert_video", convert_video_start)],
        states={
            GET_VIDEO: [MessageHandler(filters.VIDEO | filters.Document.MimeType("video/*"), get_video)],
            GET_RESOLUTION: [CallbackQueryHandler(apply_conversion, pattern="^convert:")],
        },
        fallbacks=[CommandHandler("cancel", cancel)], **conv_handler_defaults
    ))

    # --- Other Handlers ---
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    logger.info("Bot started and is now polling.")
    application.run_polling()

if __name__ == "__main__":
    main()
