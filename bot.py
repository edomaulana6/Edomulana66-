import logging
import os
import re
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
import yt_dlp

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Command Handlers ---

async def start(update: Update, context: CallbackContext) -> None:
    """Sends a welcome message when the /start command is issued."""
    user = update.effective_user
    welcome_message = (
        f"👋 Halo {user.mention_html()}!\n\n"
        "Selamat datang di bot pengunduh YouTube.\n\n"
        "Berikut perintah yang bisa Anda gunakan:\n"
        "• Kirimkan saya link YouTube untuk mengunduh video atau audio.\n"
        "• `/search <judul>` - Mencari 5 video teratas di YouTube.\n"
        "• `/song <judul>` - Langsung mengunduh lagu dari hasil teratas.\n\n"
        "Gunakan /help untuk melihat pesan ini lagi."
    )
    await update.message.reply_html(welcome_message)

async def help_command(update: Update, context: CallbackContext) -> None:
    """Sends a help message when the /help command is issued."""
    help_message = (
        "🤔 *Butuh Bantuan?*\n\n"
        "Ini yang bisa saya lakukan:\n\n"
        "1. *Unduh dari URL*:\n"
        "   Kirimkan saja URL dari YouTube (atau situs lain yang didukung), dan saya akan memberi Anda pilihan untuk mengunduh sebagai video atau audio.\n\n"
        "2. *Pencarian Detail (Top 5)*:\n"
        "   Gunakan perintah `/search <judul lagu>`.\n"
        "   Contoh: `/search Alan Walker Faded`\n"
        "   Saya akan menampilkan 5 hasil teratas lengkap dengan tombol unduhan.\n\n"
        "3. *Unduh Cepat (Lagu)*:\n"
        "   Gunakan perintah `/song <judul lagu>`.\n"
        "   Contoh: `/song Alan Walker Faded`\n"
        "   Saya akan otomatis mencari, mengunduh, dan mengirimkan file audio dari hasil teratas."
    )
    await update.message.reply_markdown(help_message)

async def search(update: Update, context: CallbackContext) -> None:
    """Searches YouTube for top 5 videos based on a query."""
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("Silakan berikan judul untuk dicari. Contoh: `/search Alan Walker Faded`")
        return

    await update.message.reply_text(f"🔎 Mencari lagu untuk: *{query}*...", parse_mode='Markdown')

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

async def song(update: Update, context: CallbackContext) -> None:
    """Finds the top song on YouTube and sends it as audio."""
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("Silakan berikan judul lagu. Contoh: `/song Alan Walker Faded`")
        return

    message = await update.message.reply_text(f"🔎 Mencari lagu teratas untuk: *{query}*...", parse_mode='Markdown')
    try:
        with yt_dlp.YoutubeDL({'default_search': 'ytsearch1', 'quiet': True}) as ydl:
            info = ydl.extract_info(query, download=False)['entries'][0]

        caption = f"🎵 *{info.get('title', 'Tanpa Judul')}*\n\n⬇️ Mengunduh audio..."
        if thumbnail := info.get('thumbnail'):
            await update.message.reply_photo(photo=thumbnail, caption=caption, parse_mode='Markdown')
        else:
            await update.message.reply_text(caption, parse_mode='Markdown')

        await download_file(info.get('id'), 'audio', update, context)
    except Exception as e:
        logger.error(f"Error during /song command: {e}")
        await message.edit_text("Maaf, terjadi kesalahan saat mencari atau mengunduh lagu.")

async def handle_url(update: Update, context: CallbackContext) -> None:
    """Handles messages containing a URL."""
    url = update.message.text.strip()
    if not re.match(r'https?://', url):
        await update.message.reply_text("Tolong kirimkan URL yang valid.")
        return

    message = await update.message.reply_text("🔎 Memproses URL...")
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
    """Handles the download button press."""
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

    await query.edit_message_text(text=f"⏳ Mempersiapkan unduhan {format_choice}...")
    try:
        await download_file(identifier, format_choice, update, context)
        await query.edit_message_text(text=f"✅ Unduhan {format_choice} selesai!")
    except Exception as e:
        logger.error(f"Error during download_file call: {e}")
        await query.edit_message_text(text="❌ Gagal mengunduh file.")

async def download_file(identifier: str, format_choice: str, update: Update, context: CallbackContext):
    """Downloads the file using yt-dlp and sends it."""
    url = identifier if re.match(r'https?://', identifier) else f"https://www.youtube.com/watch?v={identifier}"

    download_dir = 'downloads'
    os.makedirs(download_dir, exist_ok=True)

    # Sanitize title for filename
    pre_info_opts = {'quiet': True, 'extract_flat': True}
    with yt_dlp.YoutubeDL(pre_info_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        title = info.get('title', 'video')
        sanitized_title = re.sub(r'[\\/*?:"<>|]', "", title)

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
    """Start the bot."""
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN environment variable not set.")
        print("Please set TELEGRAM_TOKEN environment variable.")
        return

    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(CommandHandler("song", song))
    application.add_handler(CallbackQueryHandler(download_button, pattern="^dl:"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))

    application.run_polling()

if __name__ == "__main__":
    main()