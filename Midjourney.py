from DiscordBot import run_discord_bot
from timeout import Timeout
from PIL import Image
import threading
import requests
import time
import random


class MidjourneyClient:
    def __init__(self, api_key, session_url, agent, GPT_client):
        self.GPT_client = GPT_client
        self.url = "https://discord.com/api/v9/interactions"
        with open(session_url, 'r+') as session_file:
            cookie = session_file.read()
        self.headers = {
            'Accept': '*/*',
            'Authorization': api_key,
            'User-Agent': agent,
            'Cookie': cookie
        }

        ready_event = threading.Event()
        self.generation_event = threading.Event()
        self.closing_event = threading.Event()
        self.discord_bot = threading.Thread(target=run_discord_bot, args=(ready_event, self.generation_event,
                                                                          self.closing_event))
        self.discord_bot.start()
        ready_event.wait()

    def imagine(self, prompt, style=100, weird=0, chaos=0):
        def generate_nonce():
            prefix = "1238891"
            # Generate 12 additional random digits
            remaining_digits = ''.join([str(random.randint(0, 9)) for _ in range(12)])
            # Concatenate the prefix and the random digits
            nonce = prefix + remaining_digits
            return str(nonce)

        sending_prompt = prompt
        for i in range(2):
            payload = {
                    "type": 2,
                    "application_id": "936929561302675456",
                    "guild_id": "1234897373902409738",
                    "channel_id": "1234897373902409741",
                    "session_id": "f2819fa0c1917fe071fb885b21bb5255",
                    "data": {
                        "version": "1237876415471554623",
                        "id": "938956540159881230",
                        "name": "imagine",
                        "type": 1,
                        "options": [
                            {
                                "type": 3,
                                "name": "prompt",
                                "value": f"{sending_prompt} --s {style} --w {weird} --c {chaos}"
                            }
                        ],
                        "application_command": {
                            "id": "938956540159881230",
                            "type": 1,
                            "application_id": "936929561302675456",
                            "version": "1237876415471554623",
                            "name": "imagine",
                            "description": "Create images with Midjourney",
                            "options": [
                                {
                                    "type": 3,
                                    "name": "prompt",
                                    "description": "The prompt to imagine",
                                    "required": True,
                                    "description_localized": "The prompt to imagine",
                                    "name_localized": "prompt"
                                }
                            ],
                            "dm_permission": True,
                            "contexts": [
                                0,
                                1,
                                2
                            ],
                            "integration_types": [
                                0,
                                1
                            ],
                            "global_popularity_rank": 1,
                            "description_localized": "Create images with Midjourney",
                            "name_localized": "imagine"
                        },
                        "attachments": []
                    },
                    "nonce": generate_nonce(),
                    "analytics_location": "slash_ui"
                }
            response = requests.post(self.url, headers=self.headers, json=payload)

            print(response.status_code)
            if response.status_code == 204:
                timeout = Timeout(200, self.generation_event.set)
                timeout.start()
                self.generation_event.wait()
                timeout.stop()
                self.generation_event.clear()

                attempts = 0
                max_attempts = 2
                while attempts < max_attempts:
                    try:
                        return Image.open(f'output/{prompt.replace(" ", "_")[:20]}.jpg')
                    except FileNotFoundError:
                        if attempts == max_attempts:
                            time.sleep(3)
                            break
                        else:
                            attempts += 1
                            continue
            else:
                print("Midjourney- Couldn't get result from server, reaching out again...")
                response = self.GPT_client.chat.completions.create(
                    model='gpt-4',
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": f'"{prompt}" make this prompt pass the soft bans in Midjourney'}
                    ]
                )
                sending_prompt = response.choices[0].message.content
                continue

        raise TimeoutError

    def terminate(self):
        self.closing_event.set()
        print("Discord- Bot is down ")
