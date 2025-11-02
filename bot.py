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

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# States for conversations
GET_TITLE, GET_PHOTO, GET_ENHANCEMENT, GET_VIDEO, GET_RESOLUTION, GET_URL = range(6)

# --- Feature Imports ---
from image_enhancer import enhance_photo
from video_converter import convert_video_resolution

# --- Helper Functions ---

async def perform_search(query: str, update: Update, context: CallbackContext):
    """Performs a more resilient YouTube search and sends results."""
    await update.message.reply_text(f"🔎 Mencari 5 teratas untuk: *{query}*...", parse_mode='Markdown')
    # By removing 'extract_flat', we ask for full metadata, which is more reliable
    # even if slightly slower.
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
            sent_count = 0
            for video in videos:
                try:
                    video_id = video.get('id')
                    title = video.get('title', 'Tanpa Judul')
                    duration = f"{video.get('duration', 0) // 60}:{video.get('duration', 0) % 60:02d}"
                    caption = f"🎵 *{title}*\n⏱️ Durasi: {duration}"
                    keyboard = InlineKeyboardMarkup([[
                        InlineKeyboardButton("🎧 Audio", callback_data=f"dl:audio:id:{video_id}"),
                        InlineKeyboardButton("🎬 Video", callback_data=f"dl:video:id:{video_id}"),
                    ]])
                    if thumbnail := video.get('thumbnail'):
                        await update.message.reply_photo(photo=thumbnail, caption=caption, reply_markup=keyboard, parse_mode='Markdown')
                    else:
                        await update.message.reply_text(caption, reply_markup=keyboard, parse_mode='Markdown')
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Failed to process and send one search result ({video.get('id')}): {e}")
                    # Skip this item and continue with the next one
                    continue

            if sent_count == 0:
                await update.message.reply_text("Maaf, semua hasil pencarian gagal ditampilkan. Mungkin ada masalah dengan data dari YouTube.")

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
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    }

    final_path = ""
    base_path = ""
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

        # Baca thumbnail ke dalam memori jika ada
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
            await update.message.reply_audio(
                file_to_send,
                caption=info_dict.get('title'),
                title=info_dict.get('title'),
                filename=telegram_filename,
                thumbnail=thumbnail_data
            )

        await message.delete()

    except Exception as e:
        logger.error(f"Error during song download for query '{query}': {e}")
        await message.edit_text("Maaf, terjadi kesalahan fatal saat mengunduh lagu.")
    finally:
        if os.path.exists(final_path):
            os.remove(final_path)
        if base_path and base_path != final_path and os.path.exists(base_path):
            os.remove(base_path)

# --- Conversation Handlers ---

async def search_start(update: Update, context: CallbackContext) -> int:
    """Starts the /search conversation by asking for the title."""
    await update.message.reply_text("Apa judul lagu yang ingin Anda cari? (Ketik /cancel untuk batal)")
    return GET_TITLE

async def song_start(update: Update, context: CallbackContext) -> int:
    """Starts the /song conversation by asking for the title."""
    await update.message.reply_text("Tentu, apa judul lagu yang ingin diunduh? (Ketik /cancel untuk batal)")
    return GET_TITLE

async def get_title_and_search(update: Update, context: CallbackContext) -> int:
    """Gets title, performs search, and ends conversation."""
    query = update.message.text
    await perform_search(query, update, context)
    return ConversationHandler.END

async def get_title_and_download(update: Update, context: CallbackContext) -> int:
    """Gets title, performs download, and ends conversation."""
    query = update.message.text
    await perform_song_download(query, update, context)
    return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversation."""
    await update.message.reply_text("Pencarian dibatalkan.")
    return ConversationHandler.END

# --- Standard Command Handlers ---

async def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    await update.message.reply_html(
        f"👋 Halo {user.mention_html()}!\n\n"
        "Gunakan `/search` atau `/song` untuk memulai pencarian lagu.\n"
        "Anda juga bisa mengirimkan link URL langsung untuk diunduh."
    )

async def help_command(update: Update, context: CallbackContext) -> None:
    await update.message.reply_markdown(
        "*Bantuan Perintah*\n\n"
        "`/search` - Memulai pencarian interaktif untuk 5 lagu teratas.\n"
        "`/song` - Memulai pencarian interaktif untuk mengunduh lagu teratas.\n"
        "`/cancel` - Membatalkan proses pencarian yang sedang berjalan.\n\n"
        "Anda juga bisa mengirimkan URL YouTube (atau situs lain) langsung ke saya untuk mendapatkan pilihan unduhan."
    )

# --- Download and URL handling ---

async def handle_url(update: Update, context: CallbackContext) -> None:
    """Handles messages containing a URL entity."""
    entities = update.message.entities
    url_entity = next((e for e in entities if e.type in ("url", "text_link")), None)
    if not url_entity: return

    if url_entity.type == "text_link":
        url = url_entity.url
    else:
        url = update.message.text[url_entity.offset : url_entity.offset + url_entity.length]

    message = await update.message.reply_text(f"🔎 Memproses URL: {url}...")
    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'noplaylist': True}) as ydl:
            info = ydl.extract_info(url, download=False)

        key = str(uuid.uuid4())
        context.user_data[key] = url

        caption = f"🎬 *{info.get('title', 'Tanpa Judul')}*"
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🎧 Audio", callback_data=f"dl:audio:urlkey:{key}"),
            InlineKeyboardButton("🎬 Video", callback_data=f"dl:video:urlkey:{key}"),
        ]])

        await message.delete()
        if thumbnail := info.get('thumbnail'):
            await update.message.reply_photo(photo=thumbnail, caption=caption, reply_markup=keyboard, parse_mode='Markdown')
        else:
            await update.message.reply_text(caption, reply_markup=keyboard, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error processing URL {url}: {e}")
        await message.edit_text("Gagal memproses URL. Pastikan link tersebut didukung.")

async def download_button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    sticker_message = None
    try:
        _, format_choice, source_type, value = query.data.split(':', 3)
    except ValueError:
        await query.edit_message_text("❌ Terjadi kesalahan: Callback tidak valid.")
        return

    identifier = context.user_data.get(value) if source_type == 'urlkey' else value
    if not identifier:
        # Since the original message might not be editable anymore, send a new one.
        await query.message.reply_text("❌ Link unduhan sudah kedaluwarsa. Silakan kirim ulang URL atau lakukan pencarian lagi.")
        # Also remove the buttons from the old message
        await query.edit_message_reply_markup(reply_markup=None)
        return

    # Remove buttons from the original message to prevent re-clicks
    await query.edit_message_reply_markup(reply_markup=None)
    # Send a sticker as a loading indicator
    sticker_message = await query.message.reply_sticker("CAACAgIAAxkBAAIEv2X0x4-v2-5v3e_wY_v2-5v3e_wYAAJ-BwAC-5-xS_v2-5v3e_wYHgQ")

    try:
        # This function will now send the file as a new message
        await download_file(identifier, format_choice, update, context)
    except Exception as e:
        logger.error(f"Error during download_file call from button: {e}")
        await query.message.reply_text("❌ Gagal mengunduh file.")
    finally:
        # Clean up the sticker
        if sticker_message:
            await sticker_message.delete()

async def download_file(identifier: str, format_choice: str, update: Update, context: CallbackContext):
    """Mengunduh file berdasarkan URL atau ID, mengirimkannya, dan membersihkan."""
    url = identifier if re.match(r'https?://', identifier) else f"https://www.youtube.com/watch?v={identifier}"
    download_dir = 'downloads'
    os.makedirs(download_dir, exist_ok=True)

    # Gunakan template nama file yang aman untuk sistem file.
    file_path_template = os.path.join(download_dir, '%(id)s.%(ext)s')

    ydl_opts = {
        'outtmpl': file_path_template,
        'noplaylist': True,
        'quiet': True,
    }

    if format_choice == 'audio':
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    else:
        ydl_opts['format'] = 'best'

    final_path = ""
    base_path = ""
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Unduh dan dapatkan info dalam satu langkah
            info_dict = ydl.extract_info(url, download=True)
            base_path = ydl.prepare_filename(info_dict)

        # Tentukan path akhir setelah potensi konversi
        final_path = os.path.splitext(base_path)[0] + '.mp3' if format_choice == 'audio' else base_path

        if not os.path.exists(final_path):
            if os.path.exists(base_path):
                final_path = base_path  # Fallback jika konversi gagal
            else:
                raise FileNotFoundError(f"File tidak ditemukan setelah diunduh: {final_path} atau {base_path}")

        effective_update = update.callback_query or update.message
        caption_text = info_dict.get('title', 'File')

        # Bersihkan judul untuk nama file yang dikirim ke Telegram
        sanitized_title = re.sub(r'[\\/*?:"<>|]', "", caption_text)

        # Siapkan thumbnail untuk audio
        thumbnail_data = None
        if format_choice == 'audio' and (thumbnail_url := info_dict.get('thumbnail')):
            import requests
            try:
                response = requests.get(thumbnail_url)
                response.raise_for_status()
                thumbnail_data = response.content
            except requests.RequestException as e:
                logger.warning(f"Gagal mengunduh thumbnail: {e}")

        sender = effective_update.message.reply_audio if format_choice == 'audio' else effective_update.message.reply_video

        with open(final_path, 'rb') as file_to_send:
            # Gunakan judul yang bersih untuk nama file di Telegram
            file_extension = 'mp3' if format_choice == 'audio' else info_dict.get('ext', 'mp4')
            filename = f"{sanitized_title}.{file_extension}"
            await sender(
                file_to_send,
                caption=caption_text,
                title=caption_text,
                filename=filename,
                thumbnail=thumbnail_data
            )

    finally:
        # Pembersihan: Pastikan semua file yang diunduh dihapus
        if os.path.exists(final_path):
            os.remove(final_path)
        if base_path and base_path != final_path and os.path.exists(base_path):
            os.remove(base_path)

def main() -> None:
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN environment variable not set.")
        return

    # --- Persistensi ---
    # Membuat objek persistensi untuk menyimpan data bot
    persistence = PicklePersistence(filepath="bot_persistence")

    application = Application.builder().token(token).persistence(persistence).build()

    # Conversation handlers
    search_conv = ConversationHandler(
        entry_points=[CommandHandler("search", search_start)],
        states={ GET_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_title_and_search)] },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    song_conv = ConversationHandler(
        entry_points=[CommandHandler("song", song_start)],
        states={ GET_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_title_and_download)] },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(search_conv)
    application.add_handler(song_conv)

    # Other handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(download_button, pattern="^dl:"))
    # application.add_handler(MessageHandler(filters.Entity("url") | filters.Entity("text_link"), handle_url)) # REMOVED to implement /download command

    # --- URL Download Conversation ---
    async def download_start(update: Update, context: CallbackContext) -> int:
        """Starts the /download conversation."""
        await update.message.reply_text("Silakan kirim URL yang ingin Anda unduh. Kirim /cancel untuk berhenti.")
        return GET_URL

    async def get_url_and_process(update: Update, context: CallbackContext) -> int:
        """Receives a URL and passes it to the handler."""
        await handle_url(update, context)
        return ConversationHandler.END

    download_conv = ConversationHandler(
        entry_points=[CommandHandler("download", download_start)],
        states={
            GET_URL: [MessageHandler(filters.Entity("url") | filters.Entity("text_link"), get_url_and_process)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(download_conv)

    # --- Photo Enhancement Conversation ---
    async def enhance_start(update: Update, context: CallbackContext) -> int:
        """Starts the photo enhancement conversation."""
        await update.message.reply_text("Silakan kirim foto yang ingin Anda tingkatkan. Kirim /cancel untuk berhenti.")
        return GET_PHOTO

    async def get_photo(update: Update, context: CallbackContext) -> int:
        """Receives the photo and asks for the enhancement type."""
        photo_file = await update.message.photo[-1].get_file()

        # We need a unique path for each photo
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
        """Applies the selected enhancement and sends the photo back."""
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
            await query.message.reply_photo(photo=open(enhanced_path, 'rb'))
            await query.edit_message_text("Berikut adalah foto yang telah ditingkatkan:")
        except Exception as e:
            logger.error(f"Error during photo enhancement: {e}")
            await query.edit_message_text("Maaf, terjadi kesalahan saat meningkatkan foto.")
        finally:
            # Clean up both original and enhanced files
            if os.path.exists(photo_path):
                os.remove(photo_path)
            if enhanced_path and os.path.exists(enhanced_path):
                os.remove(enhanced_path)

            # Clear the path from user_data
            if 'photo_path' in context.user_data:
                del context.user_data['photo_path']

        return ConversationHandler.END

    enhance_conv = ConversationHandler(
        entry_points=[CommandHandler("enhance_photo", enhance_start)],
        states={
            GET_PHOTO: [MessageHandler(filters.PHOTO, get_photo)],
            GET_ENHANCEMENT: [CallbackQueryHandler(apply_enhancement, pattern="^enhance:")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(enhance_conv)

    # --- Video Conversion Conversation ---
    async def convert_start(update: Update, context: CallbackContext) -> int:
        """Starts the video conversion conversation."""
        await update.message.reply_text("Silakan kirim file video yang ingin Anda konversi. Kirim /cancel untuk berhenti.")
        return GET_VIDEO

    async def get_video(update: Update, context: CallbackContext) -> int:
        """Receives the video and asks for the target resolution."""
        # Note: This handles videos sent as 'video' or 'document'
        video_file_obj = update.message.video or update.message.document
        if not video_file_obj:
            await update.message.reply_text("File tidak valid. Pastikan Anda mengirim video.")
            return GET_VIDEO # Ask again

        video_file = await video_file_obj.get_file()

        download_dir = 'downloads'
        os.makedirs(download_dir, exist_ok=True)
        # Preserve original filename and extension
        original_filename = video_file_obj.file_name
        video_path = os.path.join(download_dir, f"{uuid.uuid4()}_{original_filename}")

        await video_file.download_to_drive(video_path)
        context.user_data['video_path'] = video_path

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("4K", callback_data="convert:4k"),
                InlineKeyboardButton("2K", callback_data="convert:2k"),
                InlineKeyboardButton("1080p", callback_data="convert:1080p"),
            ],
            [
                InlineKeyboardButton("720p", callback_data="convert:720p"),
                InlineKeyboardButton("480p", callback_data="convert:480p"),
                InlineKeyboardButton("360p", callback_data="convert:360p"),
            ],
        ])
        await update.message.reply_text("Pilih resolusi target:", reply_markup=keyboard)
        return GET_RESOLUTION

    async def apply_conversion(update: Update, context: CallbackContext) -> int:
        """Applies the selected resolution conversion."""
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
            await query.message.reply_video(video=open(converted_path, 'rb'), caption=f"Video dikonversi ke {target_resolution}")
            await query.delete_message() # Clean up the "Pilih resolusi" message
        except Exception as e:
            logger.error(f"Error during video conversion: {e}")
            await query.edit_message_text("Maaf, terjadi kesalahan saat mengonversi video.")
        finally:
            # Clean up both original and converted files
            if os.path.exists(video_path):
                os.remove(video_path)
            if converted_path and os.path.exists(converted_path):
                os.remove(converted_path)

            if 'video_path' in context.user_data:
                del context.user_data['video_path']

        return ConversationHandler.END

    convert_conv = ConversationHandler(
        entry_points=[CommandHandler("convert_video", convert_start)],
        states={
            GET_VIDEO: [MessageHandler(filters.VIDEO | filters.Document.VIDEO, get_video)],
            GET_RESOLUTION: [CallbackQueryHandler(apply_conversion, pattern="^convert:")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(convert_conv)


    application.run_polling()


if __name__ == "__main__":
    main()