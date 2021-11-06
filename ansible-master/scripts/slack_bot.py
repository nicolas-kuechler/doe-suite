
import argparse
import logging
import os
import re

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_APP_TOKEN = os.environ["SLACK_APP_TOKEN"]

CMD_REGEX = "<@[A-Z0-9]+> ([a-z]+) (.*)"

app = App(token=SLACK_BOT_TOKEN)

class BotCommand():
    def __init__(self, body):
        event = body["event"]

        self.channel_id = event["channel"]
        self.sender = event["user"]
        text = event["text"]
        matches = re.search(CMD_REGEX, text)

        if not matches:
            logging.debug(f"Invalid command (not matching the regex): {text}")
            raise Exception

        groups = matches.groups()
        self.cmd = groups[0]
        self.args = groups[1]

#
# Commands
#
def echo(args):
    return str(args), None, None

def does(args_str):
    # Import here to avoid circular imports
    from does_master import does_master_exec
    return does_master_exec(args_str)

KNOWN_CMDS = {
    "echo": echo,
    "does": does,
}

#
# Helpers
#
def post_files(channel_id, files, text):
    """
    Post files in the specified channel
    """

    for i, file_name in enumerate(files):
        app.client.files_upload(
            channels=channel_id,
            initial_comment=text[i],
            file=file_name,
        )


#
# Bot Handler
#

def bot_handle(cmd, say):
    """
    Execute known commands
    """

    blocks = None
    if cmd.cmd not in KNOWN_CMDS:
        logging.debug(f"Received unknown command: {cmd.cmd}")
        text = f"Unknown command. Try: {', '.join(KNOWN_CMDS.keys())}"
    else:
        logging.debug(f"Executing command: {cmd.cmd}")
        text, blocks, files_to_upload = KNOWN_CMDS[cmd.cmd](cmd.args)

    if files_to_upload:
        post_files(cmd.channel_id, files_to_upload, text)
    else:
        say(blocks=blocks, text=text)

#
# Advanced message formats
#
def str_to_markdown(s):
    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": s
        }
    }

#
# Decorators
#
@app.event("app_mention")
def mention_handler(body, say):
    try:
        cmd = BotCommand(body)
    except:
        say(f"Invalid command: it has to match the regex '{CMD_REGEX}'")
        return

    bot_handle(cmd, say)


if __name__ == "__main__":
    logging.RootLogger(level=logging.DEBUG)

    parser = argparse.ArgumentParser(description="Slack bot for the DoE-Suite")

    parser.add_argument("--commit", help="Commit for which the bot should post results", type=str)
    parser.add_argument("--channel", help="Channel to post in", type=str)

    args = parser.parse_args()
    commit = args.commit
    channel = args.channel

    if not commit:
        handler = SocketModeHandler(app, SLACK_APP_TOKEN)
        handler.start()
    elif channel:
        # Import here to avoid circular imports
        from does_master import does_fetch_results

        texts, _, files_to_upload = does_fetch_results([commit])
        app.client.files_upload(
            channels=channel,
            initial_comment=texts[0],
            file=files_to_upload[0],
        )
    else:
        print("Invalid arguments: commit and channel must be set both or none.")
        parser.print_help()
