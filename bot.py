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
)
import yt_dlp

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# States for conversation
SEARCH_TITLE, SEARCH_ARTIST, SONG_TITLE, SONG_ARTIST = range(4)

# --- Helper Functions ---

async def perform_search(query: str, update: Update, context: CallbackContext):
    """Performs the actual YouTube search and sends results."""
    await update.message.reply_text(f"🔎 Mencari 5 teratas untuk: *{query}*...", parse_mode='Markdown')
    ydl_opts = {
        'format': 'bestaudio/best', 'noplaylist': True, 'quiet': True,
        'default_search': 'ytsearch5', 'extract_flat': 'in_playlist',
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(query, download=False)
            videos = [v for v in result.get('entries', []) if v.get('duration', 0) < 600]

            if not videos:
                await update.message.reply_text("Tidak ada lagu (durasi di bawah 10 menit) yang ditemukan.")
                return

            await update.message.reply_text(f"Berikut {len(videos)} hasil teratas:")
            for video in videos:
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
    except Exception as e:
        logger.error(f"Error during search: {e}")
        await update.message.reply_text("Maaf, terjadi kesalahan saat melakukan pencarian.")

async def perform_song_download(query: str, update: Update, context: CallbackContext):
    """Finds the top song on YouTube and sends it as audio."""
    message = await update.message.reply_text(f"🔎 Mencari lagu teratas untuk: *{query}*...", parse_mode='Markdown')
    try:
        with yt_dlp.YoutubeDL({'default_search': 'ytsearch1', 'quiet': True}) as ydl:
            info = ydl.extract_info(query, download=False)['entries'][0]

        caption = f"🎵 *{info.get('title', 'Tanpa Judul')}*\n\n⬇️ Mengunduh audio..."
        if thumbnail := info.get('thumbnail'):
            await update.message.reply_photo(photo=thumbnail, caption=caption, parse_mode='Markdown')
        else:
            await update.message.reply_text(caption, parse_mode='Markdown')

        await message.delete() # Clean up the "Searching..." message
        await download_file(info.get('id'), 'audio', update, context)
    except Exception as e:
        logger.error(f"Error during song download: {e}")
        await message.edit_text("Maaf, terjadi kesalahan saat mencari atau mengunduh lagu.")

# --- Conversation Handlers ---

# /search conversation
async def search_start(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Tentu, mari kita cari beberapa lagu. Siapa nama artisnya? (Ketik /cancel untuk batal)")
    return SEARCH_ARTIST

async def search_get_artist(update: Update, context: CallbackContext) -> int:
    context.user_data['artist'] = update.message.text
    await update.message.reply_text("Oke, artis dicatat. Sekarang, apa judul lagunya?")
    return SEARCH_TITLE

async def search_get_title_and_execute(update: Update, context: CallbackContext) -> int:
    artist = context.user_data.pop('artist', '')
    title = update.message.text
    query = f"{artist} {title}".strip()
    await perform_search(query, update, context)
    return ConversationHandler.END

# /song conversation
async def song_start(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Oke, saya akan carikan lagunya. Siapa nama artisnya? (Ketik /cancel untuk batal)")
    return SONG_ARTIST

async def song_get_artist(update: Update, context: CallbackContext) -> int:
    context.user_data['artist'] = update.message.text
    await update.message.reply_text("Artis dicatat. Sekarang, apa judul lagunya?")
    return SONG_TITLE

async def song_get_title_and_execute(update: Update, context: CallbackContext) -> int:
    artist = context.user_data.pop('artist', '')
    title = update.message.text
    query = f"{artist} {title}".strip()
    await perform_song_download(query, update, context)
    return ConversationHandler.END

# General conversation commands
async def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversation."""
    await update.message.reply_text("Pencarian dibatalkan.")
    context.user_data.clear()
    return ConversationHandler.END

# --- Standard Command Handlers ---

async def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    await update.message.reply_html(
        f"👋 Halo {user.mention_html()}!\n\n"
        "Bot ini sekarang lebih interaktif.\n"
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
    # The filter ensures we have at least one URL entity. We'll take the first one.
    entities = update.message.entities
    url_entity = next((e for e in entities if e.type in ("url", "text_link")), None)

    if not url_entity:
        # This should not happen due to the filter, but as a safeguard:
        return

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
    try:
        _, format_choice, source_type, value = query.data.split(':', 3)
    except ValueError:
        await query.edit_message_text("❌ Terjadi kesalahan: Callback tidak valid.")
        return

    identifier = context.user_data.get(value) if source_type == 'urlkey' else value
    if not identifier:
        await query.edit_message_text("❌ Link unduhan sudah kedaluwarsa. Silakan kirim ulang URL atau lakukan pencarian lagi.")
        return

    original_message = await query.edit_message_text(text=f"⏳ Mempersiapkan unduhan {format_choice}...")
    try:
        await download_file(identifier, format_choice, update, context)
        await original_message.edit_text(text=f"✅ Unduhan {format_choice} selesai!")
    except Exception as e:
        logger.error(f"Error during download_file call: {e}")
        await original_message.edit_text(text="❌ Gagal mengunduh file.")

async def download_file(identifier: str, format_choice: str, update: Update, context: CallbackContext):
    url = identifier if re.match(r'https?://', identifier) else f"https://www.youtube.com/watch?v={identifier}"
    download_dir = 'downloads'
    os.makedirs(download_dir, exist_ok=True)

    with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True}) as ydl:
        info = ydl.extract_info(url, download=False)
        sanitized_title = re.sub(r'[\\/*?:"<>|]', "", info.get('title', 'video'))

    file_path_template = os.path.join(download_dir, f'{sanitized_title}.%(ext)s')
    ydl_opts = {
        'outtmpl': file_path_template, 'noplaylist': True, 'quiet': True,
        'progress_hooks': [lambda d: None],
    }
    ydl_opts.update({
        'format': 'bestaudio/best',
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}],
    } if format_choice == 'audio' else {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
    })

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        downloaded_path = ydl.prepare_filename(info_dict)
        if format_choice == 'audio':
            downloaded_path = os.path.splitext(downloaded_path)[0] + '.mp3'

    if not os.path.exists(downloaded_path):
        raise FileNotFoundError(f"File not found after download: {downloaded_path}")

    effective_update = update.callback_query or update.message
    caption_text = info_dict.get('title', 'File')
    sender = effective_update.message.reply_audio if format_choice == 'audio' else effective_update.message.reply_video
    with open(downloaded_path, 'rb') as file:
        await sender(file, caption=caption_text, title=caption_text)
    os.remove(downloaded_path)

def main() -> None:
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN environment variable not set.")
        return

    application = Application.builder().token(token).build()

    # Conversation handlers
    search_conv = ConversationHandler(
        entry_points=[CommandHandler("search", search_start)],
        states={
            SEARCH_ARTIST: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_get_artist)],
            SEARCH_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_get_title_and_execute)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    song_conv = ConversationHandler(
        entry_points=[CommandHandler("song", song_start)],
        states={
            SONG_ARTIST: [MessageHandler(filters.TEXT & ~filters.COMMAND, song_get_artist)],
            SONG_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, song_get_title_and_execute)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(search_conv)
    application.add_handler(song_conv)

    # Other handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(download_button, pattern="^dl:"))
    # This handler is now specific to URLs, so it won't conflict with conversations.
    application.add_handler(MessageHandler(filters.Entity("url") | filters.Entity("text_link"), handle_url))

    application.run_polling()

if __name__ == "__main__":
    main()