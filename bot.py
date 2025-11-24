import logging
import os
import re
import uuid
import sys
import shutil
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.helpers import escape_markdown
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

async def download_media(identifier: str, format_choice: str, effective_message, ydl_opts_override=None):
    status_message = await effective_message.reply_text("⏳ Memproses...")
    download_dir = 'downloads'
    os.makedirs(download_dir, exist_ok=True)

    final_ydl_opts = {
        'outtmpl': os.path.join(download_dir, '%(id)s.%(ext)s'),
        'noplaylist': True,
        'quiet': True,
        'noprogress': True,
        'format': 'bestvideo+bestaudio/best' if format_choice == 'video' else 'bestaudio/best',
    }

    if format_choice == 'audio':
        final_ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}]

    if ydl_opts_override:
        final_ydl_opts.update(ydl_opts_override)

    path, base_path = "", ""
    try:
        with yt_dlp.YoutubeDL(final_ydl_opts) as ydl:
            info = ydl.extract_info(identifier, download=True)
            base_path = ydl.prepare_filename(info)

        path_ext = '.mp3' if format_choice == 'audio' else f".{info.get('ext', 'mp4')}"
        path = os.path.splitext(base_path)[0] + path_ext

        if not os.path.exists(path):
             raise FileNotFoundError(f"File hasil unduhan tidak ditemukan: {path}")

        title = info.get('title', 'media')
        safe_title = re.sub(r'[\\/*?:"<>|]', '', title)
        filename = f"{safe_title}{path_ext}"

        with open(path, 'rb') as f:
            if format_choice == 'audio':
                await effective_message.reply_audio(f, title=title, filename=filename, caption=title)
            else:
                await effective_message.reply_video(f, filename=filename, caption=title, write_timeout=60)

    except yt_dlp.utils.DownloadError as e:
        logger.error(f"DownloadError for '{identifier}': {e}", exc_info=True)
        error_msg = f"❌ Gagal: {e}"
        if "is not a valid URL" in str(e): error_msg = "❌ Gagal: Link tidak valid."
        elif "Unsupported URL" in str(e): error_msg = "❌ Gagal: Link tidak didukung."
        await effective_message.reply_text(error_msg)
    except Exception as e:
        logger.error(f"Unexpected error for '{identifier}': {e}", exc_info=True)
        await effective_message.reply_text("❌ Gagal: Terjadi error internal yang tidak terduga.")

    finally:
        if status_message: await status_message.delete()
        for p in [path, base_path]:
            if p and os.path.exists(p):
                try: os.remove(p)
                except OSError as e: logger.error(f"Error removing file {p}: {e}")

async def cancel(update: Update, context: CallbackContext):
    context.user_data.clear()
    await update.message.reply_text("Operasi dibatalkan.")
    return ConversationHandler.END

async def start(update: Update, context: CallbackContext):
    context.bot_data.setdefault('user_ids', set()).add(update.effective_chat.id)
    await update.message.reply_html(f"👋 Halo {update.effective_user.mention_html()}! /help untuk bantuan.")

async def collect_user_id(update: Update, context: CallbackContext):
    """Collects user IDs silently in the background without replying."""
    context.bot_data.setdefault('user_ids', set()).add(update.effective_chat.id)

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
        with yt_dlp.YoutubeDL({'quiet': True, 'noplaylist': True}) as ydl:
            info = ydl.extract_info(url, download=False)

        video_id = info.get('id')
        title = info.get('title', 'Tanpa Judul')
        thumbnail = info.get('thumbnail')

        context.user_data['url_info'] = {'url': url, 'title': title, 'id': video_id}

        keyboard = [[
            InlineKeyboardButton("🎧 Audio", callback_data=f"dl_url:audio:{video_id}"),
            InlineKeyboardButton("🎬 Video", callback_data=f"dl_url:video:{video_id}")
        ]]

        safe_title = escape_markdown(title, version=2)
        await update.message.reply_photo(
            photo=thumbnail,
            caption=f"Pilih format untuk:\n*{safe_title}*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='MarkdownV2'
        )
    except Exception as e:
        logger.error(f"Gagal memproses URL {url}: {e}", exc_info=True)
        await download_media(url, 'video', update.message)

    return CHOOSE_FORMAT

async def _display_search_page(update: Update, context: CallbackContext, query: str, page: int, is_edit: bool = False):
    effective_message = update.message if not is_edit else update.callback_query.message
    status_message_text = "⏳ Mencari..." if page == 0 else f"⏳ Mencari halaman {page + 1}..."

    status_message = None
    if is_edit:
        try:
            await update.callback_query.edit_message_text(status_message_text, reply_markup=None)
        except Exception:
            pass
    else:
        status_message = await effective_message.reply_text(status_message_text)

    try:
        results_per_page = 10
        start_index = page * results_per_page
        end_index = start_index + results_per_page

        search_term = f"ytsearch{end_index + 1}:{query}"
        ydl_opts = {'quiet': True, 'noplaylist': True, 'match_filter': 'duration < 600'}

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(search_term, download=False)

        all_entries = [e for e in result.get('entries', []) if e.get('duration')]

        if not all_entries or len(all_entries) <= start_index:
            message_text = "Tidak ada hasil lebih lanjut atau pencarian tidak valid."
            if is_edit: await update.callback_query.edit_message_text(message_text)
            else: await status_message.edit_text(message_text)
            return

        has_next_page = len(all_entries) > end_index
        page_results = all_entries[start_index:end_index]

        message_text = f"Hasil pencarian untuk: `{escape_markdown(query, version=2)}`\n\n"
        keyboard_buttons, row = [], []
        for i, entry in enumerate(page_results):
            num_on_page = i + 1
            duration_in_seconds = int(entry.get('duration', 0))
            duration = f"{(duration_in_seconds // 60):02d}:{(duration_in_seconds % 60):02d}"
            safe_title = escape_markdown(entry.get('title', 'Tanpa Judul'), version=2)
            message_text += f"{num_on_page}. ({duration}) *{safe_title}*\n\n"
            row.append(InlineKeyboardButton(str(num_on_page), callback_data=f"search:select:{entry['id']}:{page}"))
            if len(row) >= 5:
                keyboard_buttons.append(row)
                row = []
        if row: keyboard_buttons.append(row)

        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton("<<", callback_data=f"search:page:{page - 1}"))
        nav_row.append(InlineKeyboardButton(f"Hal {page + 1}", callback_data="search:noop"))
        if has_next_page:
            nav_row.append(InlineKeyboardButton(">>", callback_data=f"search:page:{page + 1}"))
        keyboard_buttons.append(nav_row)
        keyboard_buttons.append([InlineKeyboardButton("❌ Tutup", callback_data="search:cancel")])

        reply_markup = InlineKeyboardMarkup(keyboard_buttons)
        if is_edit:
            await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode='MarkdownV2')
        else:
            await status_message.edit_text(message_text, reply_markup=reply_markup, parse_mode='MarkdownV2')

    except Exception as e:
        logger.error(f"Search display failed for query '{query}' on page {page}: {e}", exc_info=True)
        error_message = "❌ Terjadi kesalahan saat melakukan pencarian."
        if is_edit: await update.callback_query.edit_message_text(error_message)
        elif status_message: await status_message.edit_text(error_message)
        else: await effective_message.reply_text(error_message)


async def _display_download_choice_search(update: Update, context: CallbackContext, video_id: str, page: int):
    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'noplaylist': True}) as ydl:
            info = ydl.extract_info(video_id, download=False)

        title = info.get('title', 'Tanpa Judul')
        safe_title = escape_markdown(title, version=2)
        caption = f"Pilih format untuk:\n*{safe_title}*"

        keyboard = [
            [
                InlineKeyboardButton("🎧 Audio", callback_data=f"dl_search:audio:{video_id}"),
                InlineKeyboardButton("🎬 Video", callback_data=f"dl_search:video:{video_id}")
            ],
            [InlineKeyboardButton("⬅️ Kembali", callback_data=f"search:page:{page}")]
        ]

        await update.callback_query.edit_message_text(
            caption,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='MarkdownV2'
        )
    except Exception as e:
        logger.error(f"Failed to display download choice for video_id '{video_id}': {e}", exc_info=True)
        await update.callback_query.edit_message_text("❌ Terjadi kesalahan saat mengambil detail video.")

    return CHOOSE_FORMAT

async def search_start(update: Update, context: CallbackContext):
    await update.message.reply_text("Apa yang ingin dicari?")
    return GET_SEARCH_QUERY

async def search_get_query(update: Update, context: CallbackContext):
    query = update.message.text
    await _display_search_page(update, context, query=query, page=0, is_edit=False)
    return CHOOSE_FORMAT

def _extract_query_from_message(text: str) -> str or None:
    match = re.search(r"Hasil pencarian untuk: `(.*?)`", text)
    if match:
        return re.sub(r'\\(.)', r'\1', match.group(1))
    return None

async def search_callback_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    parts = query.data.split(':')
    action = parts[1]

    search_query = _extract_query_from_message(query.message.text_markdown_v2)

    if not search_query:
        await query.edit_message_text("❌ Error: Sesi pencarian ini sudah tidak valid. Silakan /search lagi.")
        return ConversationHandler.END

    if action == 'page':
        page = int(parts[2])
        await _display_search_page(update, context, query=search_query, page=page, is_edit=True)

    elif action == 'select':
        video_id = parts[2]
        page = int(parts[3])
        await _display_download_choice_search(update, context, video_id, page)

    elif action == 'cancel':
        await query.message.delete()
        return ConversationHandler.END

    return CHOOSE_FORMAT

async def song_start(update: Update, context: CallbackContext):
    await update.message.reply_text("Kirimkan judul lagu.")
    return GET_SONG_TITLE

async def song_get_title(update: Update, context: CallbackContext):
    status_message = await update.message.reply_text("⏳ Mencari lagu di YouTube Music...")
    try:
        ydl_opts = {'quiet': True, 'noplaylist': True, 'default_search': 'ytmusic'}

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(update.message.text, download=False)

            # Handle kasus di mana hasil pencarian adalah playlist
            video_info = result.get('entries', [result])[0]

            duration = int(video_info.get('duration', 9999))
            if duration > 600:
                await status_message.edit_text(f"❌ Gagal: Lagu '{video_info.get('title', '')}' ditemukan, tapi durasinya lebih dari 10 menit.")
                return ConversationHandler.END

        video_url = video_info['webpage_url']
        await status_message.delete()
        await download_media(video_url, 'audio', update.message)

    except Exception as e:
        logger.error(f"Song search failed for '{update.message.text}': {e}", exc_info=True)
        await status_message.edit_text("❌ Gagal: Tidak dapat menemukan lagu atau terjadi error internal.")

    return ConversationHandler.END

async def enhance_photo_start(update: Update, context: CallbackContext):
    await update.message.reply_text("Kirim foto (atau file gambar).")
    return GET_PHOTO

async def get_photo(update: Update, context: CallbackContext):
    status_message = await update.message.reply_text("⏳ Mengunduh foto...")
    try:
        if update.message.photo:
            file = await update.message.photo[-1].get_file()
        elif update.message.document and update.message.document.mime_type.startswith('image'):
            file = await update.message.document.get_file()
        else:
            await status_message.edit_text("❌ File tidak valid. Mohon kirim gambar.")
            return GET_PHOTO

        os.makedirs('downloads', exist_ok=True)
        path = os.path.join('downloads', f"photo_{uuid.uuid4()}.jpg")
        await file.download_to_drive(path)
        context.user_data['photo_path'] = path

        keyboard = [[
            InlineKeyboardButton("Tajamkan", callback_data="enhance:sharpen"),
            InlineKeyboardButton("Kontras", callback_data="enhance:contrast")
        ]]
        await status_message.edit_text("Pilih jenis peningkatan:", reply_markup=InlineKeyboardMarkup(keyboard))
        return GET_ENHANCEMENT
    except Exception as e:
        logger.error(f"Failed to get photo: {e}", exc_info=True)
        await status_message.edit_text("❌ Terjadi kesalahan saat memproses foto.")
        return ConversationHandler.END

async def photo_enhancement_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    enhancement_type = query.data.split(':')[1]
    photo_path = context.user_data.get('photo_path')
    output_path = None

    if not photo_path or not os.path.exists(photo_path):
        await query.edit_message_text("❌ Error: File foto tidak ditemukan. Sesi mungkin kedaluwarsa.")
        return ConversationHandler.END

    await query.edit_message_text(f"⏳ Menerapkan peningkatan '{enhancement_type}'...")

    try:
        output_path = enhance_photo(photo_path, enhancement_type)
        if not output_path or not os.path.exists(output_path):
            raise ValueError("Gagal meningkatkan kualitas gambar.")

        with open(output_path, 'rb') as f:
            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=f,
                filename=f"enhanced_{os.path.basename(photo_path)}",
                caption=f"✅ Foto berhasil ditingkatkan ({enhancement_type})."
            )
    except Exception as e:
        logger.error(f"Photo enhancement failed for {photo_path}: {e}", exc_info=True)
        await query.message.reply_text(f"❌ Gagal meningkatkan gambar.")
    finally:
        await query.message.delete()
        for path in [photo_path, output_path]:
            if path and os.path.exists(path):
                os.remove(path)
        context.user_data.clear()

    return ConversationHandler.END

async def convert_video_start(update: Update, context: CallbackContext):
    await update.message.reply_text("Kirim video (atau file video).")
    return GET_VIDEO

async def get_video(update: Update, context: CallbackContext):
    status_message = await update.message.reply_text("⏳ Mengunduh video...")
    try:
        file_to_download = update.message.video or update.message.document
        if not file_to_download or not file_to_download.mime_type.startswith('video'):
             await status_message.edit_text("❌ File tidak valid. Mohon kirim video.")
             return GET_VIDEO

        file = await file_to_download.get_file()
        original_filename = file_to_download.file_name

        os.makedirs('downloads', exist_ok=True)
        ext = os.path.splitext(original_filename)[1] if original_filename else '.mp4'
        path = os.path.join('downloads', f"vid_{uuid.uuid4()}{ext}")

        await file.download_to_drive(path)
        context.user_data['video_path'] = path

        keyboard = [
            [InlineKeyboardButton("✨ Tingkatkan Kualitas", callback_data="convert:enhance_quality")],
            [InlineKeyboardButton("2160p (4k)", callback_data="convert:2160p"), InlineKeyboardButton("1440p (2k)", callback_data="convert:1440p")],
            [InlineKeyboardButton("1080p", callback_data="convert:1080p"), InlineKeyboardButton("720p", callback_data="convert:720p")]
        ]
        await status_message.edit_text("Pilih tindakan:", reply_markup=InlineKeyboardMarkup(keyboard))
        return GET_PROCESS_ACTION
    except Exception as e:
        logger.error(f"Failed to get video: {e}", exc_info=True)
        await status_message.edit_text("❌ Terjadi kesalahan saat memproses video.")
        return ConversationHandler.END

async def video_processing_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    action = query.data.split(':')[1]
    video_path = context.user_data.get('video_path')
    output_path = None

    if not video_path or not os.path.exists(video_path):
        await query.edit_message_text("❌ Error: File video tidak ditemukan. Sesi mungkin kedaluwarsa.")
        return ConversationHandler.END

    try:
        if action == 'enhance_quality':
            await query.edit_message_text("⏳ Meningkatkan kualitas video...")
            output_path = enhance_video_quality(video_path)
            caption = "✅ Kualitas video berhasil ditingkatkan."
        else:
            resolution = action
            await query.edit_message_text(f"⏳ Mengonversi video ke {resolution}...")
            output_path = convert_video_resolution(video_path, resolution)
            caption = f"✅ Video berhasil dikonversi ke {resolution}."

        if not output_path or not os.path.exists(output_path):
             raise ValueError("Proses video gagal menghasilkan output.")

        with open(output_path, 'rb') as f:
            await context.bot.send_video(
                chat_id=query.message.chat_id, video=f, caption=caption, write_timeout=120
            )
    except Exception as e:
        logger.error(f"Video processing/sending failed: {e}", exc_info=True)
        await query.message.reply_text(f"❌ Gagal memproses video: {e}")
    finally:
        await query.message.delete()
        for path in [video_path, output_path]:
            if path and os.path.exists(path):
                os.remove(path)
        context.user_data.clear()

    return ConversationHandler.END

async def download_callback_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    parts = query.data.split(':')
    data_type, action, video_id = parts[0], parts[1], parts[2]

    identifier = video_id

    if data_type == 'dl_url':
        url_info = context.user_data.get('url_info')
        if not url_info or url_info.get('id') != video_id:
            await query.message.edit_text("Error: Sesi unduhan URL kedaluwarsa. Silakan mulai lagi /download.")
            return ConversationHandler.END

        identifier = url_info['url']
        title = url_info['title']
        safe_title = escape_markdown(title, version=2)

        await query.message.edit_text(f"⏳ Memulai unduhan untuk *{safe_title}*...", parse_mode='MarkdownV2')
        await download_media(identifier, action, query.message)
        return ConversationHandler.END

    elif data_type == 'dl_search':
        title = "Video Pilihan"
        try:
            with yt_dlp.YoutubeDL({'quiet': True, 'noplaylist': True}) as ydl:
                info = ydl.extract_info(video_id, download=False)
                title = info.get('title', 'Video Pilihan')
        except Exception as e:
            logger.warning(f"Could not fetch title for {video_id} in callback: {e}")

        safe_title = escape_markdown(title, version=2)
        status_message = await context.bot.send_message(chat_id=query.message.chat_id, text=f"⏳ Mengunduh *{safe_title}*...", parse_mode='MarkdownV2')
        await download_media(identifier, action, query.message)
        if status_message: await status_message.delete()

    return CHOOSE_FORMAT

def main():
    if not run_pre_flight_checks():
        sys.exit(1)
    persistence = PicklePersistence(filepath="bot_persistence")
    app = (
        Application.builder()
        .token(os.getenv("TELEGRAM_TOKEN"))
        .persistence(persistence)
        .post_init(post_init)
        .build()
    )

    conv_defaults = {
        "allow_reentry": True,
        "conversation_timeout": 300,
        "fallbacks": [CommandHandler("cancel", cancel)],
    }

    # === DAFTARKAN SEMUA CONVERSATION HANDLER DI SINI ===
    app.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("download", download_start)],
            states={
                GET_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, download_get_url)],
                CHOOSE_FORMAT: [CallbackQueryHandler(download_callback_handler, pattern="^dl_url:")],
            },
            **conv_defaults,
        )
    )
    app.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("search", search_start)],
            states={
                GET_SEARCH_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_get_query)],
                CHOOSE_FORMAT: [
                    CallbackQueryHandler(download_callback_handler, pattern="^dl_search:"),
                    CallbackQueryHandler(search_callback_handler, pattern="^search:"),
                ],
            },
            **conv_defaults,
        )
    )
    app.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("song", song_start)],
            states={GET_SONG_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, song_get_title)]},
            **conv_defaults,
        )
    )
    app.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("enhance_photo", enhance_photo_start)],
            states={
                GET_PHOTO: [MessageHandler(filters.PHOTO | filters.Document.IMAGE, get_photo)],
                GET_ENHANCEMENT: [CallbackQueryHandler(photo_enhancement_handler, pattern="^enhance:")],
            },
            **conv_defaults,
        )
    )
    app.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("convert_video", convert_video_start)],
            states={
                GET_VIDEO: [MessageHandler(filters.VIDEO | filters.Document.VIDEO, get_video)],
                GET_PROCESS_ACTION: [CallbackQueryHandler(video_processing_handler, pattern="^convert:")],
            },
            **conv_defaults,
        )
    )
    # =======================================================

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, collect_user_id))

    logger.info("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
