import math
from secret import reddit_secret, reddit_id, midjourny_api_key, openai_api_key
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip
from openai import OpenAI
from Midjourney import MidjourneyClient
import praw
import re
import os


class ChatGPTResponseError(Exception):
    pass


class VideoGenerator:
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)' \
                 ' Chrome/120.0.0.0 Safari/537.36'

    stories_prompt = """ You are a TikTok story generator. You get a story from the user and turn it into a series of scenes and narration for TikTok. Here are your instructions:

1. Split the story into a suitable number of scenes for a TikTok narration video.
2. For each scene, include the narrator's storyline to read and a descriptive prompt suitable for Midjourney6.
3. Ensure the narrator lines are told from a third-person storyteller perspective, typical of an average TikTok video. The story should be told as if it really happened, narrating the sequence of events. Only mention the year and place where the story happened, avoiding specific timestamps like "lately."
4. Ensure the image prompts maintain a consistent theme based on the story provided.
5. Avoid using punctuation in the image prompt and do not mention character names; only describe the characters.
6. Make sure to add the image theme based on the story.
7. Avoid using controversial words in the image prompt, making sure it passes NSFW regulations.
8. Use descriptive phrases like "a girl from Texas in 1999" instead of pronouns like "she" or "he". If the story does not mention specific details, you are allowed to invent them.
9. Additionally, estimate the percentage of the total video time each scene will take to ensure the total adds up to 100%.
10. Start the story in an interesting manner, such as "This is a true story about..."

Format the response as a Python list, like this:
[
 ("Scene 1 narrator line", "Scene 1 image prompt", percentage as integer),
 ("Scene 2 narrator line", "Scene 2 image prompt", percentage as integer)
]

For example:
[("This is a true story about a girl in Norway in 1999", "A picturesque Norwegian town in 1999", 5),
("Her life changed forever when her dad suddenly passed away", "A grieving family in a modest Norwegian home", 10),
("Her mother, who already had mental health issues, became increasingly abusive", "A distressed mother showing signs of mental struggle", 10),
("Due to their worsening financial situation, they had to move to a new, run-down neighborhood", "A family moving into a run-down neighborhood", 10),
("In the new house, the girl discovered a small hidden door behind the wallpaper", "A girl uncovering a hidden door behind old wallpaper", 10),
("But behind the door, she found only a wall of bricks", "A small door revealing a wall of bricks behind it", 5),
("Her mother flew into a rage and severely beat her", "An enraged mother attacking her daughter in a fit of anger", 10),
("The girl lost consciousness, and her mother, in a delusional state, tried to sew buttons into her face", "A distressed mother attempting to sew buttons into her daughter's face", 10),
("Neighbors noticed a foul smell coming from the house and called the police", "Concerned neighbors calling the police outside a dilapidated house", 10),
("The police discovered the girl's lifeless body inside", "Police officers discovering a lifeless body inside a dimly lit house", 10),
("Her mother was transferred to a mental hospital, unable to cope with what she had done", "A woman being taken away to a mental hospital", 10)]

Ensure the list is compatible with Python syntax. Do not use special characters and limit the number of prompts to 10. """

    def __init__(self, content_path='content'):
        print("Generator- Setting up the video generator...")
        self.reddit_client = praw.Reddit(
            client_id=reddit_id,
            client_secret=reddit_secret,
            user_agent=VideoGenerator.user_agent
        )
        self.content_path = content_path
        self.GPT_client = OpenAI(api_key=openai_api_key)

        self.midjourney_client = MidjourneyClient(midjourny_api_key, "session.txt", VideoGenerator.user_agent,
                                                  self.GPT_client)
        print("Generator- generator is set\n############################")

    def generate(self, video_amount, subreddit, scenes_amount=10, max_length=None):
        print("Generator- Retrieving stories from reddit...", end='')
        media = self._mine_narratives_(video_amount, max_length, subreddit)
        print("[SUCCESS]")

        print("Generator- Creating Drafts...", end='')
        drafts = self._create_drafts_(media)
        print("[SUCCESS]\n###########################")

        print("Starts video creation...")
        for i, (title, story) in enumerate(drafts, 1):
            print(f"Generator- Synthesizing video number {i} ...")
            title = re.sub(r'[<>:"/\\|?* ]', '_', title)
            data_path = f"{self.content_path}/{title}"
            if not os.path.exists(data_path):
                os.mkdir(data_path)
                with open(data_path + '/script.txt', 'w+', encoding='utf-8') as f:
                    f.write(story)

            images = self._craft_images_(VideoGenerator.stories_prompt + str(scenes_amount), story)

            narration = ""
            for index, (line, image, timing) in enumerate(images, 1):
                try:
                    image.save(data_path + f'/{index}-{timing}.jpeg', 'JPEG')
                    narration += f"{line}. "
                except AttributeError:
                     print("Warning, None Type")

            print("Generator- Generating narration...", end='')
            speech = self._synthesize_voice_(narration)
            speech.write_to_file(data_path + '/voiceover.aac')
            print("[SUCCESS]")

            print("Generator- Stitching the video...", end='')
            self._stitch_videos_(data_path)
            print("[SUCCESS]")
 
            print(f"Video number {i} is completed\n###########################")
            break

    def close_session(self):
        self.midjourney_client.terminate()
        print("The generator session was closed")

    def _mine_narratives_(self, total_media_to_retrieve, max_post_length, subreddits_title):
        if max_post_length is None:
            max_post_length = math.inf
        results = []
        params = {'limit': 7}

        while len(results) < total_media_to_retrieve:
            batch = list(
                self.reddit_client.subreddit(subreddits_title).top(limit=params['limit'], params=params, time_filter='week'))
            if not batch:
                print("Reddit- No posts found")
                break

            params = {'limit': params['limit'], 'after': batch[-1].fullname}
            batch = list(filter(lambda post: len(post.selftext.split(" ")) <= max_post_length, batch))
            results.extend(batch)

        return results

    def _create_drafts_(self, media):
        drafts = []

        for post in media:
            story = post.selftext
            response = self.GPT_client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": "I have a certain script: '{0}'"
                                   "Generate a very short title for a YouTube Short based on the script."
                                   " Make it similar to the examples below style in writing. "
                                   "Examples: - Scary things hidden in normal photos Part#28 -"
                                   " This is the scariest video on the internet".format(story),
                    }
                ],
                model="gpt-4",
            )
            drafts.append((response.choices[0].message.content, story))

        return drafts

    def _craft_images_(self, prompt, script):
        response = self.GPT_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": prompt},
                      {"role": "user", 'content': script}],
            temperature=1,
            max_tokens=1024,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )

        if response.choices[0].message is not None:
            scenes = response.choices[0].message.content
            narrator_lines, image_prompts, timings = eval('zip(*{0})'.format(scenes.replace('\n', '')))
            print("Crafting Images... ")

            related_images = []
            for i, image_prompt in enumerate(image_prompts, 1):
                print(f"Crafting image number {i}...")
                try:
                    image = self.midjourney_client.imagine(image_prompt)
                    related_images.append(image)
                except TimeoutError:
                    related_images.append(related_images[-1])

            return list(zip(narrator_lines, related_images, timings))

        else:
            raise ChatGPTResponseError

    def _synthesize_voice_(self, script):
        response = self.GPT_client.audio.speech.create(
            response_format='aac',
            model="tts-1",
            voice="onyx",
            input=script
        )

        return response

    @staticmethod
    def _stitch_videos_(content_path, captions):
        def sort_key(filename):
            number = int(filename.split('-')[0])
            return number

        image_files = [f for f in os.listdir(content_path) if f.endswith('jpeg')]
        image_files = sorted(image_files, key=sort_key)
        percentages = list(map(lambda name: name.split('-')[1].split('.')[0], image_files))
        image_files = list(map(lambda f: os.path.join(content_path, f), image_files))

        audio_clip_path = os.path.join(content_path, 'voiceover.aac')
        audio_clip = AudioFileClip(audio_clip_path)

        video_clips = []
        for i, image_path in enumerate(image_files):
            # duration = int(percentages[i]) / 100 * audio_clip.duration
            duration = audio_clip.duration / len(image_files)
            img_clip = ImageClip(image_path, duration=duration)
            video_clips.append(img_clip)

        concatenated_clips = concatenate_videoclips(video_clips, method='compose')

        txt_clips = []
        for caption in captions:
            txt_clip = TextClip(caption['text'], fontsize=24, color='white')
            txt_clip = txt_clip.set_position(('center', 'bottom')).set_duration(caption['duration'])
            txt_clip = txt_clip.set_start(caption['start'])
            txt_clips.append(txt_clip)

        final_clip = CompositeVideoClip([concatenated_clips, *txt_clips]).set_audio(audio_clip)
        final_clip = concatenated_clips.set_audio(audio_clip)

        final_output_path = os.path.join(content_path, 'clip.mp4')
        final_clip.write_videofile(final_output_path, codec='libx264', audio_codec='aac', fps=24,
                                   threads=4)

    def _generate_captions_(self):
        pass