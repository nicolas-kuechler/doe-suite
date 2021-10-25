
# TODO: rework with https://www.twilio.com/blog/how-to-build-a-slackbot-in-socket-mode-with-python

import re

from time import sleep
from slackclient import SlackClient

class AnsibleMasterBot():
    RTM_READ_DELAY = 1

    KNOWN_CMDS = {
        "echo": echo
    }

    def __init__(self, token):
        self.client = SlackClient(token)
        self.name = "Ansible Master Bot"
        

    class BotCommand():
        def __init__(self, cmd, channel):
            parts = cmd.strip().split()
            self.cmd = parts[0]
            self.args = parts[1:]
            self.channel = channel

    #
    # Commands
    #
    def echo(*args):
        return args

    #
    # Helper functions
    #
    def filter_bot_commands(self, slack_events):
        """
        Parse a list of Slack events and identify and yield bot commands.
        """
        for event in slack_events:
            if event["type"] == "message": 
                matches = re.search(f"^<@{self.id}>(.*)", event["text"])
                if matches:
                    yield BotCommand(matches.group(0), event["channel"])

    def handle_cmd(self, cmd):
        """
        Execute known commands
        """

        if cmd.cmd not in known_cmds:
            response = f"Unknown command. Try: {', '.join(known_cmds.keys())}"
        else:
            response = known_cmds[cmd.cmd](*cmd.args)

        # Sends the response back to the channel
        self.client.api_call(
            "chat.postMessage",
            channel=cmd.channel,
            text=response
        )

    def run(self):
        if self.client.rtm_connect(with_team_state=False):
            print("{self.name} connected and running!")

            self.id = slack_client.api_call("auth.test")["user_id"]
            while True:
                for cmd in self.filter_bot_commands(self.client.rtm_read()):
                    self.handle_cmd(cmd)
                    sleep(self.RTM_READ_DELAY)
        else:
            print("{self.name} failed to connect.")


if __name__ == "__main__":
    slack_client = SlackClient(os.environ.get("SLACK_OAUTH_ACCESS_TOKEN"))

