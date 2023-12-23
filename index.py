import os
import logging
from dotenv import load_dotenv
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from pytube import YouTube
from moviepy.editor import VideoFileClip

# Load environment variables from .env
load_dotenv()

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Access the variables
telegram_bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')

# Dictionary to store user data
user_data = {}

def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Hello! I'm your YouTube video downloader bot.")

def download_video(update, context):
    video_url = update.message.text

    try:
        yt = YouTube(video_url)
        video_title = yt.title
        context.bot.send_message(chat_id=update.effective_chat.id, text=f'The video title is: {video_title}')

        # Get available video formats
        formats = yt.streams.filter(file_extension="mp4")
        available_formats = [f"{i}. {stream.resolution}" for i, stream in enumerate(formats, start=1)]
        formats_message = "Available formats:\n" + "\n".join(available_formats)
        context.bot.send_message(chat_id=update.effective_chat.id, text=formats_message)

        # Store available formats in user_data
        user_data[update.effective_chat.id] = {'formats': formats}

        # Create an inline keyboard with clickable buttons for each format
        keyboard = [[InlineKeyboardButton(f"{i}", callback_data=str(i))] for i in range(1, len(formats) + 1)]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(chat_id=update.effective_chat.id, text="Select a format:", reply_markup=reply_markup)

    except Exception as e:
        context.bot.send_message(chat_id=update.effective_chat.id, text=f'Error: {str(e)}')
        logger.error(f"Error processing video download: {str(e)}")

def button_click(update, context):
    query = update.callback_query
    chat_id = query.message.chat_id
    selected_format_index = int(query.data)

    # Retrieve the selected format from user_data
    formats = user_data.get(chat_id, {}).get('formats')
    selected_format = formats[selected_format_index - 1]

    # Download the selected video format
    video_path = selected_format.download()

    # Convert video to a format supported by Telegram
    converted_video_path = video_path.replace(".mp4", "_converted.mp4")
    clip = VideoFileClip(video_path)
    clip.write_videofile(converted_video_path, codec='libx264', audio_codec='aac', threads=4, preset='ultrafast')
    clip.close()

    # Send the video file as a document to the user
    context.bot.send_document(chat_id=chat_id, document=open(converted_video_path, 'rb'))

    # Remove temporary files
    os.remove(video_path)
    os.remove(converted_video_path)

def main():
    updater = Updater(token=telegram_bot_token, use_context=True)
    dp = updater.dispatcher

    # Log a message when the server is running
    logger.info("Server is running.")

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, download_video))
    dp.add_handler(CallbackQueryHandler(button_click))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
