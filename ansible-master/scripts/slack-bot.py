
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
    return str(args)

KNOWN_CMDS = {
    "echo": echo
}

#
# Bot Handler
#

def bot_handle(cmd, say):
    """
    Execute known commands
    """

    if cmd.cmd not in KNOWN_CMDS:
        logging.debug(f"Received unknown command: {cmd.cmd}")
        response = f"Unknown command. Try: {', '.join(KNOWN_CMDS.keys())}"
    else:
        logging.debug(f"Executing command: {cmd.cmd}")
        response = KNOWN_CMDS[cmd.cmd](cmd.args)

    say(response)

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

    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
