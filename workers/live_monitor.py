
def monitor_creator(platform, channel_id):
    supported = ["youtube", "twitch", "kick"]

    if platform not in supported:
        raise ValueError("Unsupported platform")

    return {
        "platform": platform,
        "channel_id": channel_id,
        "monitoring": "not_started"
    }
