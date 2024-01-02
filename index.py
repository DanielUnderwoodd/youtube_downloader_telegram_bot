import os
import subprocess
import logging
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler,CallbackContext
from telegram import Update,InlineKeyboardMarkup, InlineKeyboardButton
from pytube import YouTube
from threading import Thread
import threading
import asyncio



# Load environment variables from .env
load_dotenv()
# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Access the variables
telegram_bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
event = threading.Event()


# Dictionary to store user data
user_data = {}
async def start(update: Update, context):
    await  update.message.reply_text("Hello! I'm your YouTube video downloader bot.")

async def download_video(update: Update, context):
    
    process_message = await update.message.reply_text(text="Processing your request...",reply_to_message_id=update.message.message_id)
    # Show a processing message while the request is being processed
    chat_id = update.effective_chat.id

    event_loop = asyncio.get_event_loop()

    loop_id = id(event_loop)


# Do something with the event loop
    print("Current event loop downlaod video:", loop_id )

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
        reply_markup = InlineKeyboardMarkup(available_formats )


        message=   await context.bot.edit_message_text(chat_id=chat_id, text="Select a format:",message_id=process_message.message_id, reply_markup=reply_markup)

        # Store the message ID for later deletion
        user_data[chat_id]['message_id'] = message.message_id

    except Exception as e:
           await update.message.reply_text(text=f'Error: {str(e)}')
           logger.error(f"Error processing video download: {str(e)}")


async def button_click(update: Update, context):
    query = update.callback_query
    chat_id = query.message.chat_id
    selected_format_index = int(query.data)
    # Remove the buttons
    

    # Display a progress bar while downloading the video
    progress_message =  await context.bot.edit_message_text(chat_id=chat_id, text="Downloading...", message_id=user_data[chat_id]['message_id'])

    # Retrieve the selected format from user_data
    formats = user_data.get(chat_id, {}).get('formats')
    selected_video_format = formats[selected_format_index - 1]

    # Retrieve audio file

    audio_format = user_data.get(chat_id, {}).get('audio')[0]

    # Create a separate thread to download the video
    event_loop = asyncio.get_event_loop()

    loop_id = id(event_loop)
 

# Do something with the event loop
    print("Current event button click:", loop_id )
    await context.bot.send_chat_action(chat_id=chat_id, action='typing')
    download_thread = Thread(target= download_thread_wrapper, args=(update, context, selected_video_format,audio_format, progress_message,event_loop)
    )
    download_thread.start()


def download_thread_wrapper(update, context, selected_format,audio_format, progress_message,event_loop):

    # Simulate downloading action
    if(selected_format.abr == "128kbps"):
        audio_path = selected_format.download(filename="audio_output_file.mp4")
        output_path = convert_mp4_to_mp3(audio_path,"output.mp3")
    else:
        video_path = selected_format.download(filename="video_output_file.mp4")
        audio_path = audio_format.download(filename="audio_output_file.mp4")
        output_path = merge_video_audio(video_path,audio_path,"output.mp4")
    # Download the selected video format

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.run_until_complete(download_and_send(update,context,video_path,audio_path,output_path,progress_message,event_loop))


async def download_and_send(update: Update, context: CallbackContext, video_path,audio_path,output_path, progress_message,event_loop):
    try:
        chat_id = update.effective_chat.id
        
        loop = asyncio.get_event_loop()
        loop_id = id(loop)


# Do something with the event loop
        print("Current event loop:", loop_id )
        
        # Simulate converting action
        await context.bot.send_chat_action(chat_id=chat_id, action='typing')

        # Simulate uploading action
        await context.bot.send_chat_action(chat_id=chat_id, action='upload_video')

        await context.bot.edit_message_text(chat_id=chat_id, text=f"Uploading...", message_id=progress_message.message_id)
        asyncio.set_event_loop(event_loop)
        await context.bot.send_document(chat_id=chat_id, document=open(output_path, 'rb'))
        # Send the video file as a document to the user

        

        # Remove temporary files
        os.remove(video_path)
        os.remove(audio_path)
        os.remove(output_path)


        # Remove the progress message
        # await context.bot.delete_message(chat_id=chat_id, message_id=progress_message.message_id)

    except Exception as e:
        # Log the error with traceback
        # Send the error message to the user
        await context.bot.send_message(chat_id=chat_id, text=f'Error: Please try again ' + str(e))



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

def convert_mp4_to_mp3(input_file, output_file):
    try:
        # Run ffmpeg command
        subprocess.run(['ffmpeg', '-i', input_file, '-vn', '-acodec', 'libmp3lame', output_file])

        print(f"Conversion successful: {output_file}")
        return output_file

    except Exception as e:
        print(f"Error during conversion: {str(e)}")


def format_size(size):
    # Convert file size to human-readable format
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            break
        size /= 1024.0
    return f"{size:.2f} {unit}"

def main():

    app = ApplicationBuilder().token(telegram_bot_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))
    app.add_handler(CallbackQueryHandler(button_click))

    # Log a message when the server is running
    logger.info("Server is running.")
    app.run_polling()


if __name__ == "__main__":
    main()
