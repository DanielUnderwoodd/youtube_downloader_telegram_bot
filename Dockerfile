FROM --platform=linux/amd64 python:3.11

# Set the working directory in the container
WORKDIR /usr/src/app

# Install FFmpeg
RUN apt-get update && apt-get install -y ffmpeg


# Copy the current directory contents into the container
COPY . .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY innertube.py /usr/local/lib/python3.11/site-packages/pytube


# Define the command to run your application
CMD ["python", "index.py"]
