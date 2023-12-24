import os
import logging
from dotenv import load_dotenv
from proglog import ProgressBarLogger
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from pytube import YouTube
from moviepy.editor import VideoFileClip
from threading import Thread
import traceback
from tqdm import tqdm

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
    chat_id = update.effective_chat.id

    # Remove the message containing the title of the video
    context.bot.delete_message(chat_id=chat_id, message_id=update.message.message_id)

    # Show a processing message while the request is being processed
    context.bot.send_message(chat_id=chat_id, text="Processing your request...")

    video_url = update.message.text

    try:
        yt = YouTube(video_url)

        # Get available video formats
        formats = yt.streams.filter(file_extension="mp4")
        formats = [stream for stream in formats if stream.resolution and stream.mime_type]

        # Remove repetitive formats
        unique_formats = {stream.resolution: stream for stream in formats}.values()

        # Retrieve the exact formats like mkv and mp4
        exact_formats = [stream for stream in unique_formats if stream.mime_type.split('/')[1] in ['mkv', 'mp4']]

        available_formats = [
            [InlineKeyboardButton(f"{stream.resolution} - {stream.mime_type.split('/')[1]} - {format_size(stream.filesize)}",
                                  callback_data=str(i))]
            for i, stream in enumerate(exact_formats, start=1)
        ]

        # Store available formats in user_data
        user_data[chat_id] = {'formats': exact_formats}

        # Create an inline keyboard with clickable buttons for each format
        reply_markup = InlineKeyboardMarkup(available_formats, row_width=2)
        message = context.bot.send_message(chat_id=chat_id, text="Select a format:", reply_markup=reply_markup)

        # Store the message ID for later deletion
        user_data[chat_id]['message_id'] = message.message_id

    except Exception as e:
        context.bot.send_message(chat_id=chat_id, text=f'Error: {str(e)}')
        logger.error(f"Error processing video download: {str(e)}")

def button_click(update, context):
    query = update.callback_query
    chat_id = query.message.chat_id
    selected_format_index = int(query.data)

    # Remove the buttons
    context.bot.delete_message(chat_id=chat_id, message_id=user_data[chat_id]['message_id'])

    # Display a progress bar while downloading the video
    progress_message = context.bot.send_message(chat_id=chat_id, text="Downloading...")

    # Retrieve the selected format from user_data
    formats = user_data.get(chat_id, {}).get('formats')
    selected_format = formats[selected_format_index - 1]

    # Create a separate thread to download the video
    download_thread = Thread(target=download_and_send, args=(update, context, selected_format, progress_message))
    download_thread.start()

def download_and_send(update, context, selected_format, progress_message):
    try:
        chat_id = update.effective_chat.id

        # Simulate downloading action
        context.bot.send_chat_action(chat_id=chat_id, action='typing')

        # Download the selected video format
        video_path = selected_format.download()

        # Simulate converting action
        context.bot.send_chat_action(chat_id=chat_id, action='typing')

        # Convert video to a format supported by Telegram
        converted_video_path = video_path.replace(".mp4", "_converted.mp4")
        clip = VideoFileClip(video_path)

        class MyBarLogger(ProgressBarLogger):
            def __init__(self, *args, **kwargs):
        # Call the __init__ method of the parent class
                super().__init__(*args, **kwargs)
                self.base = 0
    
    
            def bars_callback(self, bar, attr, value,old_value=None):
                # Every time the logger progress is updated, this function is called 
                percentage = (value / self.bars[bar]['total']) * 100
                if (self.base != int(percentage) ):
                     context.bot.edit_message_text(chat_id=chat_id, text=f"Converting... {int(percentage)}%", message_id=progress_message.message_id)
                     self.base= int(percentage)

        logger = MyBarLogger()

        # Write video file with callback for progress tracking
        clip.write_videofile(converted_video_path, codec='libx264', audio_codec='aac', threads=4, preset='ultrafast', verbose=False, logger=logger)
        clip.close()

        # Simulate uploading action
        context.bot.send_chat_action(chat_id=chat_id, action='upload_video')

        context.bot.edit_message_text(chat_id=chat_id, text=f"Uploading...", message_id=progress_message.message_id)


        # Send the video file as a document to the user
        context.bot.send_document(chat_id=chat_id, document=open(converted_video_path, 'rb'))

        # Remove temporary files
        os.remove(video_path)
        os.remove(converted_video_path)

        # Remove the progress message
        context.bot.delete_message(chat_id=chat_id, message_id=progress_message.message_id)

    except Exception as e:
        # Get the traceback information
        trace = traceback.format_exc()
        
        # Log the error with traceback
        # Send the error message to the user
        context.bot.send_message(chat_id=chat_id, text=f'Error: Please try again')


def format_size(size):
    # Convert file size to human-readable format
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            break
        size /= 1024.0
    return f"{size:.2f} {unit}"

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
