import os
import logging
from dotenv import load_dotenv
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram.error import BadRequest, RetryAfter
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from pytube import YouTube
from moviepy.editor import VideoFileClip
from threading import Thread
import requests
from tqdm import tqdm
from io import BytesIO
import time  # Import the time module

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

    video_url = update.message.text

    try:
        # Get available video formats
        formats = get_video_formats(video_url)

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
    progress_message = context.bot.send_message(chat_id=chat_id, text="Downloading... 0%")

    # Retrieve the selected format from user_data
    formats = user_data.get(chat_id, {}).get('formats')
    selected_format = formats[selected_format_index - 1]

    # Create a separate thread to download the video
    total_size = get_total_size(selected_format.url)
    download_thread = Thread(target=download_and_send, args=(context.bot, chat_id, selected_format, progress_message, total_size))
    download_thread.start()

def download_and_send(bot, chat_id, selected_format, progress_message, total_size):
    try:
        # Download the selected video format
        video_path = download_with_progress(selected_format.url, lambda chunk, remaining_bytes: download_progress_callback(chat_id, progress_message, total_size, total_size - remaining_bytes, bot))

        # Update the progress bar for downloading
        bot.edit_message_text(chat_id=chat_id, text="Downloading... 100%", message_id=progress_message.message_id)

        # Introduce a delay to avoid flood control
        time.sleep(2)

        # Display a progress bar while converting the video
        convert_progress_message = bot.send_message(chat_id=chat_id, text="Converting... 0%")

        # Convert video to a format supported by Telegram
        converted_video_path = video_path.replace(".mp4", "_converted.mp4")
        clip = VideoFileClip(video_path)

        def callback(progress):
            # Update the progress bar for converting
            bot.edit_message_text(chat_id=chat_id, text=f"Converting... {int(progress)}%", message_id=convert_progress_message.message_id)

        # Write video file with callback for progress tracking
        clip.write_videofile(converted_video_path, codec='libx264', audio_codec='aac', threads=4, preset='ultrafast', verbose=False, progress_bar_callback=callback)
        clip.close()

        # Remove temporary files
        os.remove(video_path)

        # Remove the progress bar for converting
        bot.delete_message(chat_id=chat_id, message_id=convert_progress_message.message_id)

        # Display a progress bar while uploading the video
        upload_progress_message = bot.send_message(chat_id=chat_id, text="Uploading... 0%")

        # Send the video file as a document to the user
        bot.send_document(chat_id=chat_id, document=open(converted_video_path, 'rb'), timeout=500)

        # Remove the progress bar for uploading
        bot.delete_message(chat_id=chat_id, message_id=upload_progress_message.message_id)

        # Remove temporary files
        os.remove(converted_video_path)

    except Exception as e:
        if isinstance(e, RetryAfter):
            # RetryAfter exception, wait for the specified time
            time.sleep(e.retry_after)
        else:
            # Handle other exceptions
            bot.send_message(chat_id=chat_id, text=f'Error: {str(e)}')
            logger.error(f"Error processing video download: {str(e)}")

def format_size(size):
    # Convert file size to human-readable format
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            break
        size /= 1024.0
    return f"{size:.2f} {unit}"

def download_progress_callback(chat_id, progress_message, total_size, bytes_downloaded, bot):
    percent_downloaded = (bytes_downloaded / total_size) * 100

    # Avoid updating the progress bar if there is no significant change
    if abs(percent_downloaded - int(percent_downloaded)) > 0.5:
        try:
            bot.edit_message_text(chat_id=chat_id, text=f"Downloading... {int(percent_downloaded)}%", message_id=progress_message.message_id)
        except BadRequest as e:
            # Handle the case where the message has been deleted
            pass

def download_with_progress(url, progress_callback=None):
    response = requests.get(url, stream=True)

    # Retrieve file size from the Content-Length header
    total_size = int(response.headers.get('Content-Length', 0))

    # Use tqdm to display a progress bar
    with tqdm(total=total_size, unit='B', unit_scale=True, unit_divisor=1024) as pbar:
        with BytesIO() as video_buffer:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    video_buffer.write(chunk)
                    pbar.update(len(chunk))
                    if progress_callback:
                        progress_callback(chunk, video_buffer.tell())

            video_path = "temp_video.mp4"
            with open(video_path, 'wb') as video_file:
                video_file.write(video_buffer.getvalue())

    return video_path

def get_video_formats(video_url):
    yt = YouTube(video_url)
    # Get available video formats
    formats = yt.streams.filter(file_extension="mp4")
    formats = [stream for stream in formats if stream.resolution and stream.mime_type]
    return formats

def get_total_size(url):
    response = requests.head(url)
    return int(response.headers.get('Content-Length', 0))

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
