import logging
import os
from dotenv import load_dotenv

# Muat variabel lingkungan dari file .env
load_dotenv()
import re
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
    CallbackQueryHandler,
    ConversationHandler,
    PicklePersistence,
)
import yt_dlp
import shutil
import sys

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# States for conversations
(
    GET_DOWNLOAD_URL,
    GET_SEARCH_QUERY,
    GET_SONG_TITLE,
    GET_PHOTO,
    GET_ENHANCEMENT,
    GET_VIDEO,
    GET_RESOLUTION,
) = range(7)

# --- Feature Imports ---
from image_enhancer import enhance_photo
from video_converter import convert_video_resolution, enhance_video_quality

# --- Helper Functions ---

async def perform_search(query: str, update: Update, context: CallbackContext):
    """Performs a more resilient YouTube search and sends results."""
    await update.message.reply_text(f"🔎 Mencari 5 teratas untuk: *{query}*...", parse_mode='Markdown')
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'default_search': 'ytsearch5',
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(query, download=False)
            videos = [v for v in result.get('entries', []) if v.get('duration', 0) < 600]

            if not videos:
                await update.message.reply_text("Tidak ada lagu (durasi di bawah 10 menit) yang ditemukan.")
                return

            await update.message.reply_text("Menampilkan hasil yang valid:")
            for video in videos:
                try:
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
                    logger.error(f"Failed to process and send one search result ({video.get('id')}): {e}")
                    continue
    except Exception as e:
        logger.error(f"Error during initial yt-dlp search: {e}")
        await update.message.reply_text("Maaf, terjadi kesalahan fatal saat melakukan pencarian.")

async def perform_song_download(query: str, update: Update, context: CallbackContext):
    """Finds the top song, downloads it as MP3, and sends it."""
    message = await update.message.reply_text(f"🔎 Mencari & mengunduh: *{query}*...", parse_mode='Markdown')
    download_dir = 'downloads'
    os.makedirs(download_dir, exist_ok=True)
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
        'noplaylist': True,
        'quiet': True,
        'default_search': 'ytsearch1',
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
    }
    final_path, base_path = "", ""
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(f"ytsearch1:{query}", download=True)
            if not result.get('entries'):
                await message.edit_text("Tidak ada lagu yang ditemukan untuk query tersebut.")
                return
            info_dict = result['entries'][0]
            base_path = ydl.prepare_filename(info_dict)
        final_path = os.path.splitext(base_path)[0] + '.mp3'
        if not os.path.exists(final_path):
            raise FileNotFoundError(f"File MP3 tidak ditemukan setelah konversi: {final_path}")
        await message.edit_text(f"✅ Unduhan selesai. Mengirim *{info_dict.get('title', 'file')}*...", parse_mode='Markdown')
        sanitized_title = re.sub(r'[\\/*?:"<>|]', "", info_dict.get('title', 'video'))
        telegram_filename = f"{sanitized_title}.mp3"
        thumbnail_data = None
        if thumbnail_url := info_dict.get('thumbnail'):
            import requests
            try:
                response = requests.get(thumbnail_url)
                response.raise_for_status()
                thumbnail_data = response.content
            except requests.RequestException as e:
                logger.warning(f"Gagal mengunduh thumbnail: {e}")
        with open(final_path, 'rb') as file_to_send:
            await update.message.reply_audio(file_to_send, caption=info_dict.get('title'), title=info_dict.get('title'), filename=telegram_filename, thumbnail=thumbnail_data)
        await message.delete()
    except Exception as e:
        logger.error(f"Error during song download for query '{query}': {e}")
        await message.edit_text("Maaf, terjadi kesalahan fatal saat mengunduh lagu.")
    finally:
        if os.path.exists(final_path): os.remove(final_path)
        if base_path and base_path != final_path and os.path.exists(base_path): os.remove(base_path)

async def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversation, clearing any temporary user data."""
    logger.info("-> CANCEL: User triggered cancel command.")

    # Proactively clear any temporary data to prevent state bleeding
    if 'photo_path' in context.user_data:
        del context.user_data['photo_path']
        logger.info("-> CANCEL: Cleared temporary photo_path from user_data.")
    if 'video_path' in context.user_data:
        del context.user_data['video_path']
        logger.info("-> CANCEL: Cleared temporary video_path from user_data.")

    await update.message.reply_text("Operasi dibatalkan.")
    logger.info("-> CANCEL: Conversation ended successfully.")
    return ConversationHandler.END

# --- Standard Command Handlers ---

async def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    await update.message.reply_html(f"👋 Halo {user.mention_html()}!\n\nGunakan `/help` untuk melihat semua perintah.")

async def help_command(update: Update, context: CallbackContext) -> None:
    await update.message.reply_markdown(
        "*Bantuan Perintah (Semua Interaktif)*\n\n"
        "`/search` - Mencari video/musik.\n"
        "`/song` - Mengunduh sebuah lagu.\n"
        "`/download` - Mengunduh media dari sebuah URL.\n"
        "`/enhance_photo` - Meningkatkan kualitas foto.\n"
        "`/convert_video` - Mengubah resolusi video.\n"
        "`/cancel` - Membatalkan operasi yang sedang berjalan."
    )

# --- Download and URL handling ---

async def handle_url(url: str, update: Update, context: CallbackContext) -> None:
    message = await update.message.reply_text(f"🔎 Memproses URL: {url}...")
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
        logger.error(f"Error processing URL {url}: {e}")
        await message.edit_text("Gagal memproses URL. Pastikan link tersebut didukung.")

async def handle_search_download(update: Update, context: CallbackContext) -> None:
    """Handles download callbacks from search results (using video ID)."""
    query = update.callback_query
    await query.answer()
    logger.info(f"-> SEARCH_DL: Received search callback: {query.data}")
    try:
        _, format_choice, video_id = query.data.split(':', 2)
    except ValueError:
        logger.error(f"-> SEARCH_DL: Invalid search callback format: {query.data}")
        await query.edit_message_text("❌ Terjadi kesalahan: Callback pencarian tidak valid.")
        return

    logger.info(f"-> SEARCH_DL: Parsed callback. Format: {format_choice}, Video ID: {video_id}")
    await query.edit_message_reply_markup(reply_markup=None)
    logger.info("-> SEARCH_DL: Removed inline keyboard.")
    status_message = await query.message.reply_text("⏳ Memproses permintaan Anda...")
    try:
        logger.info(f"-> SEARCH_DL: Calling download_file for Video ID: {video_id}")
        await download_file(video_id, format_choice, update, context)
        logger.info("-> SEARCH_DL: download_file completed successfully.")
    except Exception as e:
        logger.error(f"-> SEARCH_DL: Error during download_file call from search: {e}", exc_info=True)
        await query.message.reply_text("❌ Gagal mengunduh file dari hasil pencarian.")
    finally:
        if status_message:
            await status_message.delete()
            logger.info("-> SEARCH_DL: Deleted status message.")

async def handle_url_download(update: Update, context: CallbackContext) -> None:
    """Handles download callbacks from a submitted URL (using a UUID key)."""
    query = update.callback_query
    await query.answer()
    logger.info(f"-> URL_DL: Received URL callback: {query.data}")
    try:
        _, format_choice, url_key = query.data.split(':', 2)
    except ValueError:
        logger.error(f"-> URL_DL: Invalid URL callback format: {query.data}")
        await query.edit_message_text("❌ Terjadi kesalahan: Callback URL tidak valid.")
        return

    logger.info(f"-> URL_DL: Parsed callback. Format: {format_choice}, URL Key: {url_key}")
    url = context.user_data.get(url_key)
    if not url:
        logger.error(f"-> URL_DL: URL key not found in user_data: {url_key}")
        await query.message.reply_text("❌ Link unduhan sudah kedaluwarsa. Silakan kirim ulang URL.")
        await query.edit_message_reply_markup(reply_markup=None)
        return

    logger.info(f"-> URL_DL: Retrieved URL '{url}' from user_data.")
    await query.edit_message_reply_markup(reply_markup=None)
    logger.info("-> URL_DL: Removed inline keyboard.")
    status_message = await query.message.reply_text("⏳ Memproses permintaan Anda...")
    try:
        logger.info(f"-> URL_DL: Calling download_file for URL key: {url_key}")
        await download_file(url, format_choice, update, context)
        logger.info("-> URL_DL: download_file completed successfully.")
    except Exception as e:
        logger.error(f"-> URL_DL: Error during download_file call from URL: {e}", exc_info=True)
        await query.message.reply_text("❌ Gagal mengunduh file dari URL.")
    finally:
        if status_message:
            await status_message.delete()
            logger.info("-> URL_DL: Deleted status message.")

async def download_file(identifier: str, format_choice: str, update: Update, context: CallbackContext):
    logger.info(f"-> DOWNLOAD_FILE: Starting process for identifier: {identifier}, format: {format_choice}")
    url = identifier if re.match(r'https?://', identifier) else f"https://www.youtube.com/watch?v={identifier}"
    download_dir = 'downloads'
    os.makedirs(download_dir, exist_ok=True)
    file_path_template = os.path.join(download_dir, '%(id)s.%(ext)s')
    ydl_opts = {'outtmpl': file_path_template, 'noplaylist': True, 'quiet': True, 'noprogress': True}
    if format_choice == 'audio':
        logger.info("-> DOWNLOAD_FILE: Configuring for audio download (MP3).")
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
    else:
        logger.info("-> DOWNLOAD_FILE: Configuring for video download.")
        ydl_opts['format'] = 'best'
    final_path, base_path = "", ""
    try:
        logger.info(f"-> DOWNLOAD_FILE: Invoking yt-dlp for URL: {url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            base_path = ydl.prepare_filename(info_dict)
        logger.info(f"-> DOWNLOAD_FILE: yt-dlp finished. Base file path: {base_path}")
        final_path = os.path.splitext(base_path)[0] + '.mp3' if format_choice == 'audio' else base_path
        if not os.path.exists(final_path):
            logger.warning(f"-> DOWNLOAD_FILE: Final path {final_path} not found. Checking base path {base_path}.")
            if os.path.exists(base_path):
                final_path = base_path
            else:
                raise FileNotFoundError(f"File tidak ditemukan setelah unduhan: {final_path} atau {base_path}")
        logger.info(f"-> DOWNLOAD_FILE: Final file path determined: {final_path}")
        effective_update = update.callback_query or update.message
        caption_text = info_dict.get('title', 'File')
        sanitized_title = re.sub(r'[\\/*?:"<>|]', "", caption_text)
        thumbnail_data = None
        if format_choice == 'audio' and (thumbnail_url := info_dict.get('thumbnail')):
            import requests
            try:
                logger.info(f"-> DOWNLOAD_FILE: Downloading thumbnail from {thumbnail_url}")
                response = requests.get(thumbnail_url)
                response.raise_for_status()
                thumbnail_data = response.content
            except requests.RequestException as e:
                logger.warning(f"-> DOWNLOAD_FILE: Gagal mengunduh thumbnail: {e}")
        with open(final_path, 'rb') as file_to_send:
            file_extension = 'mp3' if format_choice == 'audio' else info_dict.get('ext', 'mp4')
            filename = f"{sanitized_title}.{file_extension}"
            logger.info(f"-> DOWNLOAD_FILE: Sending file '{filename}' (Size: {os.path.getsize(final_path)} bytes) via Telegram API.")

            if format_choice == 'audio':
                await effective_update.message.reply_audio(
                    audio=file_to_send,
                    caption=caption_text,
                    title=caption_text,
                    filename=filename,
                    thumbnail=thumbnail_data
                )
            else:
                await effective_update.message.reply_video(
                    video=file_to_send,
                    caption=caption_text,
                    filename=filename
                )

            logger.info("-> DOWNLOAD_FILE: Telegram API call completed.")
    except Exception as e:
        logger.error(f"-> DOWNLOAD_FILE: An exception occurred: {e}", exc_info=True)
        # Re-raise to be caught by the calling handler, which will notify the user.
        raise
    finally:
        logger.info("-> DOWNLOAD_FILE: Entering cleanup phase.")
        if os.path.exists(final_path):
            logger.info(f"-> DOWNLOAD_FILE: Deleting final file: {final_path}")
            os.remove(final_path)
        if base_path and base_path != final_path and os.path.exists(base_path):
            logger.info(f"-> DOWNLOAD_FILE: Deleting base file: {base_path}")
            os.remove(base_path)

# --- Interactive Conversation Handlers (for features that need them) ---

async def get_photo(update: Update, context: CallbackContext) -> int:
    """Receives a photo, either as a direct photo or as a document."""
    logger.info("-> ENHANCE: Entering get_photo state.")
    photo_obj = update.message.photo[-1] if update.message.photo else update.message.document

    if not photo_obj:
        logger.warning("-> ENHANCE: No valid photo or document object found.")
        await update.message.reply_text("File tidak valid. Pastikan Anda mengirim foto atau file gambar.")
        return GET_PHOTO

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
            await query.message.reply_photo(photo=photo_file)
        await query.edit_message_text("Berikut adalah foto yang telah ditingkatkan:")
    except Exception as e:
        logger.error(f"Error during photo enhancement: {e}")
        await query.edit_message_text("Maaf, terjadi kesalahan saat meningkatkan foto.")
    finally:
        if os.path.exists(photo_path): os.remove(photo_path)
        if enhanced_path and os.path.exists(enhanced_path): os.remove(enhanced_path)
        if 'photo_path' in context.user_data: del context.user_data['photo_path']
    return ConversationHandler.END

async def get_video(update: Update, context: CallbackContext) -> int:
    logger.info("-> CONVERT_VIDEO: Entering get_video state.")
    video_file_obj = update.message.video or update.message.document
    if not video_file_obj or (hasattr(video_file_obj, 'mime_type') and 'video' not in video_file_obj.mime_type):
        logger.warning("-> CONVERT_VIDEO: Message received is not a valid video or video document. Rejecting.")
        await update.message.reply_text("File tidak valid. Pastikan Anda mengirim video atau file video.")
        return GET_VIDEO

    logger.info(f"-> CONVERT_VIDEO: Video object received: {video_file_obj.file_name} (ID: {video_file_obj.file_id})")
    video_file = await video_file_obj.get_file()
    download_dir = 'downloads'
    os.makedirs(download_dir, exist_ok=True)

    # Menangani video tanpa nama file asli (misalnya, dari Telegram mobile)
    original_filename = video_file_obj.file_name
    if not original_filename:
        logger.warning("-> CONVERT_VIDEO: Video does not have an original filename. Assigning a default name.")
        original_filename = f"video_{uuid.uuid4()}.mp4"

    video_path = os.path.join(download_dir, f"{uuid.uuid4()}_{original_filename}")

    logger.info(f"-> CONVERT_VIDEO: Downloading video to {video_path}...")
    await video_file.download_to_drive(video_path)
    logger.info(f"-> CONVERT_VIDEO: Video downloaded successfully. Storing path in user_data.")
    context.user_data['video_path'] = video_path
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ Tingkatkan Kualitas", callback_data="convert:enhance_quality")],
        [InlineKeyboardButton("4K", callback_data="convert:4k"), InlineKeyboardButton("2K", callback_data="convert:2k"), InlineKeyboardButton("1080p", callback_data="convert:1080p")],
        [InlineKeyboardButton("720p", callback_data="convert:720p"), InlineKeyboardButton("480p", callback_data="convert:480p"), InlineKeyboardButton("360p", callback_data="convert:360p")],
    ])
    await update.message.reply_text("Pilih tindakan untuk video:", reply_markup=keyboard)
    logger.info("-> CONVERT_VIDEO: Prompted user for action. Returning GET_RESOLUTION state.")
    return GET_RESOLUTION

async def apply_conversion(update: Update, context: CallbackContext) -> int:
    logger.info("-> CONVERT_VIDEO: Entering apply_conversion state.")
    query = update.callback_query
    await query.answer()
    action = query.data.split(':')[1]
    video_path = context.user_data.get('video_path')

    logger.info(f"-> CONVERT_VIDEO: Callback received for action: {action}")
    if not video_path or not os.path.exists(video_path):
        logger.error(f"-> CONVERT_VIDEO: Video path not found in user_data or path is invalid. Path: {video_path}")
        await query.edit_message_text("Maaf, file video tidak ditemukan. Silakan mulai lagi.")
        return ConversationHandler.END

    processed_path = ""
    try:
        if action == "enhance_quality":
            logger.info(f"-> CONVERT_VIDEO: Starting quality enhancement for {video_path}.")
            await query.edit_message_text("✨ Meningkatkan kualitas video, ini mungkin memakan waktu lebih lama...")
            processed_path = enhance_video_quality(video_path)
            caption = "Kualitas video telah ditingkatkan."
        else:
            logger.info(f"-> CONVERT_VIDEO: Starting conversion for {video_path} to {action}.")
            await query.edit_message_text(f"Mengonversi video ke {action}, ini mungkin memakan waktu...")
            processed_path = convert_video_resolution(video_path, action)
            caption = f"Video dikonversi ke {action}."

        logger.info(f"-> CONVERT_VIDEO: Processing successful. New file at: {processed_path}")
        with open(processed_path, 'rb') as video_file:
            await query.message.reply_video(video=video_file, caption=caption)
        await query.delete_message()
        logger.info("-> CONVERT_VIDEO: Sent processed video to user and deleted status message.")
    except Exception as e:
        logger.error(f"-> CONVERT_VIDEO: Error during video processing call: {e}", exc_info=True)
        await query.edit_message_text("Maaf, terjadi kesalahan saat memproses video. File mungkin rusak atau tidak didukung.")
    finally:
        logger.info("-> CONVERT_VIDEO: Entering cleanup phase.")
        if os.path.exists(video_path):
            os.remove(video_path)
            logger.info(f"-> CONVERT_VIDEO: Cleaned up original file: {video_path}")
        if processed_path and os.path.exists(processed_path):
            os.remove(processed_path)
            logger.info(f"-> CONVERT_VIDEO: Cleaned up processed file: {processed_path}")
        if 'video_path' in context.user_data:
            del context.user_data['video_path']
            logger.info("-> CONVERT_VIDEO: Removed video_path from user_data.")
    logger.info("-> CONVERT_VIDEO: Exiting conversation.")
    return ConversationHandler.END


def jalankan_pemeriksaan_awal() -> bool:
    """
    Menjalankan serangkaian pemeriksaan untuk memastikan bot dapat berjalan.
    Memverifikasi token dan dependensi sistem seperti ffmpeg.
    """
    print("--- 🩺 Memulai Pemeriksaan Awal Sistem Bot 🩺 ---")

    # 1. Verifikasi Token Telegram
    token = os.getenv("TELEGRAM_TOKEN")
    if not token or token == "GANTI_DENGAN_TOKEN_ANDA" or token == "":
        logger.error("="*50)
        logger.error(" [❌] PEMERIKSAAN GAGAL: TOKEN TELEGRAM TIDAK VALID")
        logger.error("="*50)
        logger.error(" Token Anda belum diatur atau masih menggunakan placeholder.")
        logger.error(" Silakan perbaiki file '.env' Anda.")
        logger.error(" Jika file .env tidak ada, jalankan 'python3 setup.py' terlebih dahulu.")
        logger.error("="*50)
        return False
    print("[✅] Pemeriksaan Token: Lolos")

    # 2. Verifikasi FFmpeg
    if not shutil.which("ffmpeg"):
        logger.error("="*50)
        logger.error(" [❌] PEMERIKSAAN GAGAL: FFMPEG TIDAK DITEMUKAN")
        logger.error("="*50)
        logger.error(" 'ffmpeg' adalah program sistem yang wajib ada untuk fitur audio dan video.")
        logger.error(" Bot tidak dapat berjalan tanpanya.")
        logger.error(" Untuk menginstalnya di Termux, jalankan perintah:")
        logger.error("   pkg install ffmpeg")
        logger.error("="*50)
        return False
    print("[✅] Pemeriksaan FFmpeg: Lolos")

    print("\n[🎉] Semua pemeriksaan awal berhasil! Bot siap dijalankan.")
    print("="*50)
    return True


def main() -> None:
    if not jalankan_pemeriksaan_awal():
        sys.exit(1) # Hentikan bot jika pemeriksaan gagal

    token = os.getenv("TELEGRAM_TOKEN")
    persistence = PicklePersistence(filepath="bot_persistence")

    async def send_online_message(application: Application) -> None:
        user_ids = application.bot_data.get('user_ids', set())
        for user_id in user_ids:
            try:
                await application.bot.send_message(chat_id=user_id, text="BOT ONLINE ✅")
            except Exception as e: logger.warning(f"Could not send online message to {user_id}: {e}")

    async def send_offline_message(application: Application) -> None:
        user_ids = application.bot_data.get('user_ids', set())
        for user_id in user_ids:
            try:
                await application.bot.send_message(chat_id=user_id, text="BOT OFFLINE ✅")
            except Exception as e: logger.warning(f"Could not send offline message to {user_id}: {e}")

    application = Application.builder().token(token).persistence(persistence).post_init(send_online_message).post_shutdown(send_offline_message).build()

    # --- App Handlers ---
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # --- Specific Callback Handlers ---
    application.add_handler(CallbackQueryHandler(handle_search_download, pattern="^dl_search:"))
    application.add_handler(CallbackQueryHandler(handle_url_download, pattern="^dl_url:"))

    # --- User ID Storage ---
    async def store_user_id(update: Update, context: CallbackContext) -> None:
        if 'user_ids' not in context.bot_data:
            context.bot_data['user_ids'] = set()
        context.bot_data['user_ids'].add(update.effective_chat.id)
    application.add_handler(MessageHandler(filters.ALL, store_user_id), group=1)

    async def enhance_photo_start(update: Update, context: CallbackContext) -> int:
        """Starts the photo enhancement conversation."""
        await update.message.reply_text("Silakan kirim foto yang ingin Anda tingkatkan kualitasnya.")
        return GET_PHOTO

    async def convert_video_start(update: Update, context: CallbackContext) -> int:
        """Starts the video conversion conversation."""
        logger.info("-> CONVERT_VIDEO: Entering convert_video_start.")
        await update.message.reply_text("Silakan kirim video yang ingin Anda ubah resolusinya.")
        logger.info("-> CONVERT_VIDEO: Prompted user for video. Returning GET_VIDEO state.")
        return GET_VIDEO

    async def song_start(update: Update, context: CallbackContext) -> int:
        """Starts the song download conversation."""
        await update.message.reply_text("Silakan kirimkan judul lagu yang ingin Anda cari dan unduh.")
        return GET_SONG_TITLE

    async def song_get_title(update: Update, context: CallbackContext) -> int:
        """Receives the song title and starts the download."""
        query = update.message.text
        await perform_song_download(query, update, context)
        return ConversationHandler.END

    song_conv = ConversationHandler(
        entry_points=[CommandHandler("song", song_start)],
        states={
            GET_SONG_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, song_get_title)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        conversation_timeout=300,
        allow_reentry=True,
    )

    enhance_conv = ConversationHandler(
        entry_points=[CommandHandler("enhance_photo", enhance_photo_start)],
        states={
            GET_PHOTO: [MessageHandler(filters.PHOTO | filters.Document.IMAGE, get_photo)],
            GET_ENHANCEMENT: [CallbackQueryHandler(apply_enhancement, pattern="^enhance:")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        conversation_timeout=300,
        allow_reentry=True,
    )

    convert_conv = ConversationHandler(
        entry_points=[CommandHandler("convert_video", convert_video_start)],
        states={
            GET_VIDEO: [MessageHandler(filters.VIDEO | filters.Document, get_video)],
            GET_RESOLUTION: [CallbackQueryHandler(apply_conversion, pattern="^convert:")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        conversation_timeout=300,
        allow_reentry=True,
    )

    async def search_start(update: Update, context: CallbackContext) -> int:
        """Starts the search conversation."""
        await update.message.reply_text("Apa yang ingin Anda cari?")
        return GET_SEARCH_QUERY

    async def search_get_query(update: Update, context: CallbackContext) -> int:
        """Receives the search query and performs the search."""
        query = update.message.text
        await perform_search(query, update, context)
        return ConversationHandler.END

    search_conv = ConversationHandler(
        entry_points=[CommandHandler("search", search_start)],
        states={
            GET_SEARCH_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_get_query)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        conversation_timeout=300,
        allow_reentry=True,
    )

    async def download_start(update: Update, context: CallbackContext) -> int:
        """Starts the download conversation."""
        await update.message.reply_text("Silakan kirimkan URL yang ingin Anda unduh.")
        return GET_DOWNLOAD_URL

    async def download_get_url(update: Update, context: CallbackContext) -> int:
        """Receives the URL and starts the download process."""
        url = update.message.text
        if not re.match(r'https?://\S+', url):
            await update.message.reply_text("URL tidak valid. Silakan kirimkan URL yang benar.")
            return GET_DOWNLOAD_URL
        await handle_url(url, update, context)
        return ConversationHandler.END

    download_conv = ConversationHandler(
        entry_points=[CommandHandler("download", download_start)],
        states={
            GET_DOWNLOAD_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, download_get_url)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        conversation_timeout=300,
        allow_reentry=True,
    )

    application.add_handler(download_conv)
    application.add_handler(search_conv)
    application.add_handler(song_conv)
    application.add_handler(enhance_conv)
    application.add_handler(convert_conv)

    application.run_polling()

if __name__ == "__main__":
    main()
