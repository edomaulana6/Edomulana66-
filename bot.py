import logging
import os
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

# States for the remaining conversations
GET_PHOTO, GET_ENHANCEMENT, GET_VIDEO, GET_RESOLUTION = range(4)

# --- Feature Imports ---
from image_enhancer import enhance_photo
from video_converter import convert_video_resolution

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
    await update.message.reply_text("Operasi dibatalkan.")
    return ConversationHandler.END

# --- Standard Command Handlers ---

async def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    await update.message.reply_html(f"👋 Halo {user.mention_html()}!\n\nGunakan `/help` untuk melihat semua perintah.")

async def help_command(update: Update, context: CallbackContext) -> None:
    await update.message.reply_markdown(
        "*Bantuan Perintah*\n\n"
        "`/search <query>` - Mencari video/musik.\n"
        "`/song <query>` - Langsung mengunduh lagu teratas.\n"
        "`/download <url>` - Mengunduh media dari sebuah URL.\n"
        "`/enhance_photo` - Meningkatkan kualitas sebuah foto (interaktif).\n"
        "`/convert_video` - Mengubah resolusi sebuah video (interaktif).\n"
        "`/cancel` - Membatalkan operasi interaktif."
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
    try:
        _, format_choice, video_id = query.data.split(':', 2)
    except ValueError:
        await query.edit_message_text("❌ Terjadi kesalahan: Callback pencarian tidak valid.")
        return

    await query.edit_message_reply_markup(reply_markup=None)
    sticker_message = await query.message.reply_sticker("CAACAgIAAxkBAAIEv2X0x4-v2-5v3e_wY_v2-5v3e_wYAAJ-BwAC-5-xS_v2-5v3e_wYHgQ")
    try:
        await download_file(video_id, format_choice, update, context)
    except Exception as e:
        logger.error(f"Error during download_file call from search: {e}")
        await query.message.reply_text("❌ Gagal mengunduh file dari hasil pencarian.")
    finally:
        if sticker_message: await sticker_message.delete()

async def handle_url_download(update: Update, context: CallbackContext) -> None:
    """Handles download callbacks from a submitted URL (using a UUID key)."""
    query = update.callback_query
    await query.answer()
    try:
        _, format_choice, url_key = query.data.split(':', 2)
    except ValueError:
        await query.edit_message_text("❌ Terjadi kesalahan: Callback URL tidak valid.")
        return

    url = context.user_data.get(url_key)
    if not url:
        await query.message.reply_text("❌ Link unduhan sudah kedaluwarsa. Silakan kirim ulang URL.")
        await query.edit_message_reply_markup(reply_markup=None)
        return

    await query.edit_message_reply_markup(reply_markup=None)
    sticker_message = await query.message.reply_sticker("CAACAgIAAxkBAAIEv2X0x4-v2-5v3e_wY_v2-5v3e_wYAAJ-BwAC-5-xS_v2-5v3e_wYHgQ")
    try:
        await download_file(url, format_choice, update, context)
    except Exception as e:
        logger.error(f"Error during download_file call from URL: {e}")
        await query.message.reply_text("❌ Gagal mengunduh file dari URL.")
    finally:
        if sticker_message: await sticker_message.delete()

async def download_file(identifier: str, format_choice: str, update: Update, context: CallbackContext):
    url = identifier if re.match(r'https?://', identifier) else f"https://www.youtube.com/watch?v={identifier}"
    download_dir = 'downloads'
    os.makedirs(download_dir, exist_ok=True)
    file_path_template = os.path.join(download_dir, '%(id)s.%(ext)s')
    ydl_opts = {'outtmpl': file_path_template, 'noplaylist': True, 'quiet': True}
    if format_choice == 'audio':
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
    else:
        ydl_opts['format'] = 'best'
    final_path, base_path = "", ""
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            base_path = ydl.prepare_filename(info_dict)
        final_path = os.path.splitext(base_path)[0] + '.mp3' if format_choice == 'audio' else base_path
        if not os.path.exists(final_path):
            if os.path.exists(base_path): final_path = base_path
            else: raise FileNotFoundError(f"File tidak ditemukan: {final_path} atau {base_path}")
        effective_update = update.callback_query or update.message
        caption_text = info_dict.get('title', 'File')
        sanitized_title = re.sub(r'[\\/*?:"<>|]', "", caption_text)
        thumbnail_data = None
        if format_choice == 'audio' and (thumbnail_url := info_dict.get('thumbnail')):
            import requests
            try:
                response = requests.get(thumbnail_url)
                response.raise_for_status()
                thumbnail_data = response.content
            except requests.RequestException as e: logger.warning(f"Gagal mengunduh thumbnail: {e}")
        sender = effective_update.message.reply_audio if format_choice == 'audio' else effective_update.message.reply_video
        with open(final_path, 'rb') as file_to_send:
            file_extension = 'mp3' if format_choice == 'audio' else info_dict.get('ext', 'mp4')
            filename = f"{sanitized_title}.{file_extension}"
            await sender(file_to_send, caption=caption_text, title=caption_text, filename=filename, thumbnail=thumbnail_data)
    finally:
        if os.path.exists(final_path): os.remove(final_path)
        if base_path and base_path != final_path and os.path.exists(base_path): os.remove(base_path)

# --- Interactive Conversation Handlers (for features that need them) ---

async def get_photo(update: Update, context: CallbackContext) -> int:
    photo_file = await update.message.photo[-1].get_file()
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
    video_file_obj = update.message.video or update.message.document
    if not video_file_obj:
        await update.message.reply_text("File tidak valid. Pastikan Anda mengirim video.")
        return GET_VIDEO
    video_file = await video_file_obj.get_file()
    download_dir = 'downloads'
    os.makedirs(download_dir, exist_ok=True)
    original_filename = video_file_obj.file_name
    video_path = os.path.join(download_dir, f"{uuid.uuid4()}_{original_filename}")
    await video_file.download_to_drive(video_path)
    context.user_data['video_path'] = video_path
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("4K", callback_data="convert:4k"), InlineKeyboardButton("2K", callback_data="convert:2k"), InlineKeyboardButton("1080p", callback_data="convert:1080p")],
        [InlineKeyboardButton("720p", callback_data="convert:720p"), InlineKeyboardButton("480p", callback_data="convert:480p"), InlineKeyboardButton("360p", callback_data="convert:360p")],
    ])
    await update.message.reply_text("Pilih resolusi target:", reply_markup=keyboard)
    return GET_RESOLUTION

async def apply_conversion(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    target_resolution = query.data.split(':')[1]
    video_path = context.user_data.get('video_path')
    if not video_path or not os.path.exists(video_path):
        await query.edit_message_text("Maaf, file video tidak ditemukan. Silakan mulai lagi.")
        return ConversationHandler.END
    await query.edit_message_text(f"Mengonversi video ke {target_resolution}, ini mungkin memakan waktu...")
    converted_path = ""
    try:
        converted_path = convert_video_resolution(video_path, target_resolution)
        with open(converted_path, 'rb') as video_file:
            await query.message.reply_video(video=video_file, caption=f"Video dikonversi ke {target_resolution}")
        await query.delete_message()
    except Exception as e:
        logger.error(f"Error during video conversion: {e}")
        await query.edit_message_text("Maaf, terjadi kesalahan saat mengonversi video.")
    finally:
        if os.path.exists(video_path): os.remove(video_path)
        if converted_path and os.path.exists(converted_path): os.remove(converted_path)
        if 'video_path' in context.user_data: del context.user_data['video_path']
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

    # --- Direct Command Handlers (No Conversation) ---
    async def search_command(update: Update, context: CallbackContext) -> None:
        query = " ".join(context.args)
        if not query:
            await update.message.reply_text("Gunakan: `/search <query>`")
            return
        await perform_search(query, update, context)

    async def download_command(update: Update, context: CallbackContext) -> None:
        if not context.args:
            await update.message.reply_text("Gunakan: `/download <url>`")
            return
        url = context.args[0]
        if not re.match(r'https?://\S+', url):
            await update.message.reply_text("URL tidak valid.")
            return
        await handle_url(url, update, context)

    async def song_command(update: Update, context: CallbackContext) -> None:
        query = " ".join(context.args)
        if not query:
            await update.message.reply_text("Gunakan: `/song <query>`")
            return
        await perform_song_download(query, update, context)

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("download", download_command))
    application.add_handler(CommandHandler("song", song_command))

    # --- Specific Callback Handlers ---
    application.add_handler(CallbackQueryHandler(handle_search_download, pattern="^dl_search:"))
    application.add_handler(CallbackQueryHandler(handle_url_download, pattern="^dl_url:"))

    # --- User ID Storage ---
    async def store_user_id(update: Update, context: CallbackContext) -> None:
        if 'user_ids' not in context.bot_data:
            context.bot_data['user_ids'] = set()
        context.bot_data['user_ids'].add(update.effective_chat.id)
    application.add_handler(MessageHandler(filters.ALL, store_user_id), group=1)

    enhance_conv = ConversationHandler(
        entry_points=[CommandHandler("enhance_photo", lambda u, c: u.message.reply_text("Kirim foto untuk ditingkatkan.") or GET_PHOTO)],
        states={
            GET_PHOTO: [MessageHandler(filters.PHOTO, get_photo)],
            GET_ENHANCEMENT: [CallbackQueryHandler(apply_enhancement, pattern="^enhance:")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    convert_conv = ConversationHandler(
        entry_points=[CommandHandler("convert_video", lambda u, c: u.message.reply_text("Kirim video untuk dikonversi.") or GET_VIDEO)],
        states={
            GET_VIDEO: [MessageHandler(filters.VIDEO | filters.Document.VIDEO, get_video)],
            GET_RESOLUTION: [CallbackQueryHandler(apply_conversion, pattern="^convert:")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(enhance_conv)
    application.add_handler(convert_conv)

    application.run_polling()

if __name__ == "__main__":
    main()
