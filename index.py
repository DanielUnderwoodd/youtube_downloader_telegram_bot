import os
import subprocess
import logging
from dotenv import load_dotenv
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from pytube import YouTube
from threading import Thread

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


    # Show a processing message while the request is being processed
    context.bot.send_message(chat_id=chat_id, text="Processing your request...")

    video_url = update.message.text

    try:
        yt = YouTube(video_url)

        
        # get high quality videos with no audio
        all_streams = yt.streams.filter(only_video=True,file_extension="mp4")
    
        test = [stream for stream in all_streams if  stream.video_codec.startswith("avc1") and stream.resolution is not None  ]

        # getting high bitrate
        audio_streams = yt.streams.filter(only_audio=True,file_extension="mp4").all()
        target_audio = [stream for stream in audio_streams if  stream.abr == "128kbps"  ]
 
     

        exact_formats =  test + target_audio
     


        available_formats = [
            [InlineKeyboardButton(f"{stream.resolution if  stream.resolution  else stream.abr} - { stream.mime_type.split('/')[1]  if stream.resolution else 'mp3' } - {format_size(stream.filesize)}",
                                  callback_data=str(i))]
            for i, stream in enumerate(exact_formats, start=1)
        ]
        

        # Store available formats in user_data
        user_data[chat_id] = {'formats': exact_formats, 'audio': target_audio}

        # Create an inline keyboard with clickable buttons for each format
        reply_markup = InlineKeyboardMarkup(available_formats , row_width=2)
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
    selected_video_format = formats[selected_format_index - 1]

    # Retrieve audio file

    audio_format = user_data.get(chat_id, {}).get('audio')[0]

    # Create a separate thread to download the video
    download_thread = Thread(target=download_and_send, args=(update, context, selected_video_format,audio_format, progress_message))
    download_thread.start()

def download_and_send(update, context, selected_format,audio_format, progress_message):
    try:
        chat_id = update.effective_chat.id

        # Simulate downloading action
        context.bot.send_chat_action(chat_id=chat_id, action='typing')
        print(selected_format)
        print(audio_format)
        # Download the selected video format
        video_path = selected_format.download(filename="video_output_file.mp4")
        audio_path = audio_format.download(filename="audio_output_file.mp4")
        output_path = merge_video_audio(video_path,audio_path,"output.mp4")


        # Simulate converting action
        context.bot.send_chat_action(chat_id=chat_id, action='typing')

        # Simulate uploading action
        context.bot.send_chat_action(chat_id=chat_id, action='upload_video')

        context.bot.edit_message_text(chat_id=chat_id, text=f"Uploading...", message_id=progress_message.message_id)

        # Send the video file as a document to the user
        context.bot.send_document(chat_id=chat_id, document=open(output_path, 'rb'))

        # Remove temporary files
        os.remove(video_path)
        os.remove(audio_path)
        os.remove(output_path)


        # Remove the progress message
        context.bot.delete_message(chat_id=chat_id, message_id=progress_message.message_id)

    except Exception as e:
        # Log the error with traceback
        # Send the error message to the user
        context.bot.send_message(chat_id=chat_id, text=f'Error: Please try again ' + str(e))



def merge_video_audio(input_video, input_audio, output_file):

    command = [
        'ffmpeg',
        '-i', input_video,
        '-i', input_audio,
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-strict', 'experimental',
        output_file
    ]

    try:

        subprocess.run(command, check=True)
        print(f'Merging successful. Output file: {output_file}')
        return output_file
    except subprocess.CalledProcessError as e:
        print(f'Error during merging: {e}')


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
