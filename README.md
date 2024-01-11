Great! Here's the updated README.md file for your YouTube downloader Telegram bot:

```markdown
# YouTube Downloader Telegram Bot

This Telegram bot is developed in Python and allows users to download YouTube videos directly within the Telegram app.

## Table of Contents

- [Installation](#installation)
  - [Using Requirements File](#using-requirements-file)
  - [Using Docker](#using-docker)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)

## Installation

### Using Requirements File

1. Clone the repository:

   ```bash
   git clone https://github.com/DanielUnderwoodd/youtube_downloader_telegram_bot.git
   cd youtube_downloader_telegram_bot
   ```

2. Install the required dependencies using pip:

   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root and set your Telegram bot token:

   ```
   TELEGRAM_TOKEN=your_telegram_bot_token
   ```

4. Run the bot:

   ```bash
   python main.py
   ```

### Using Docker

1. Clone the repository:

   ```bash
   git clone https://github.com/DanielUnderwoodd/youtube_downloader_telegram_bot.git
   cd youtube_downloader_telegram_bot
   ```

2. Build and run the Docker container:

   ```bash
   docker-compose up -d
   ```

   Optionally, you can specify a custom Docker image name:

   ```bash
   DOCKER_IMAGE=your_image_name docker-compose up -d
   ```

   The Docker container will be built, and the YouTube downloader bot will be started.

## Usage

[Provide information on how to use and interact with your YouTube downloader bot.]

## Contributing

We welcome contributions! To contribute to this YouTube downloader bot, follow these steps:

1. Fork the repository.
2. Create a new branch: `git checkout -b feature-new-feature`.
3. Make your changes and commit them: `git commit -am 'Add new feature'`.
4. Push to the branch: `git push origin feature-new-feature`.
5. Submit a pull request.

For major changes, please open an issue first to discuss the proposed changes.

## License

This YouTube downloader bot is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
```

Feel free to customize it further based on your specific project details and requirements. If you haven't already, make sure to include a `requirements.txt` file with your project dependencies and any necessary configuration files.
