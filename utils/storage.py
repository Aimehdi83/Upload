import json
import os

CHANNEL_FILE = "runtime/channels.json"

def get_channels():
    if not os.path.exists(CHANNEL_FILE):
        return []
    with open(CHANNEL_FILE, "r") as f:
        return json.load(f)

def add_channel(channel_id):
    channels = get_channels()
    if channel_id not in channels:
        channels.append(channel_id)
        with open(CHANNEL_FILE, "w") as f:
            json.dump(channels, f)

def remove_channel(channel_id):
    channels = get_channels()
    if channel_id in channels:
        channels.remove(channel_id)
        with open(CHANNEL_FILE, "w") as f:
            json.dump(channels, f)
