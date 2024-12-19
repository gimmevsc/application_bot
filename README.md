# Telegram Bot

This project is a Telegram bot that allows users to submit application data, which is then sent to multiple sites via APIs. The bot parses user input and sends the data to predefined sites, providing the user with feedback on the submission status.

## Dependencies

- Python 3.10+
- [Poetry](https://python-poetry.org/)

## Running the Bot

1. *Install dependencies (only for the first run)*:

   ```bash
   poetry install
   ```
   
2. *Create a .env file and populate it with the necessary information*:

   ```bash
   cp .env.example .env
   ```

- Copy the server URL to receive updates from Telegram and add it to the `WEBHOOK_URL` in the `.env` file.

3. *Activate the virtual environment*:

   ```bash
   poetry shell
   ```

4. *Run the bot*:

   ```bash
   python main.py
   ```
   
### NOTE

By default, the bot will run in development mode (polling). To run it in WebHook mode, either start the Docker container or set `DEVELOPMENT` to `False` in the `.env` file:

```
DEVELOPMENT=False
``` 