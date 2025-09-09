import requests
from slack_sdk import WebClient
from twilio.rest import Client as TwilioClient
import yaml

CONFIG_PATH = "config.yaml"

def load_config():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)

def notify_slack(message: str):
    config = load_config()
    client = WebClient(token=config["notifications"]["slack_token"])
    client.chat_postMessage(channel=config["notifications"]["slack_channel"], text=message)
    print("📩 Slack notification sent!")

def notify_whatsapp(message: str):
    config = load_config()
    client = TwilioClient(config["notifications"]["twilio_sid"], config["notifications"]["twilio_token"])
    client.messages.create(
        from_=f"whatsapp:{config['notifications']['twilio_number']}",
        body=message,
        to=f"whatsapp:{config['notifications']['client_number']}"
    )
    print("📩 WhatsApp notification sent!")
