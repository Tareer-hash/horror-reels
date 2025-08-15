import os
import random
import time
import json
from datetime import datetime
from openai import OpenAI
from gtts import gTTS
import moviepy.editor as mpy
import google.auth
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Load config
from config import OPENAI_API_KEY, YOUTUBE_CREDS

# Configuration
BG_VIDEOS = "assets/gaming_videos"
BG_MUSIC = "assets/horror_music"
MAX_DURATION = 60  # 60 seconds for Shorts
DAILY_UPLOADS = 10

# Initialize APIs
client = OpenAI(api_key=OPENAI_API_KEY)

def generate_script():
    prompt = """Roman Urdu mein exact 55 second ki horror story likho. Structure:
    1. Darawani shuruat (10 sec)
    2. Suspense (35 sec) 
    3. MUST END WITH: "Part 2 ke liye follow karo!" (10 sec)"""
    
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        max_tokens=300
    )
    return response.choices[0].message.content

def create_reel(script, part_num):
    # Random assets
    bg = random.choice(os.listdir(BG_VIDEOS))
    music = random.choice(os.listdir(BG_MUSIC))
    
    # Voiceover
    tts = gTTS(script, lang='ur')
    tts.save("voice.mp3")
    
    # Video processing
    video = mpy.VideoFileClip(f"{BG_VIDEOS}/{bg}").subclip(0, MAX_DURATION)
    audio = mpy.AudioFileClip("voice.mp3").subclip(0, MAX_DURATION)
    music = mpy.AudioFileClip(f"{BG_MUSIC}/{music}").volumex(0.3)
    
    # Export
    final = video.set_audio(mpy.CompositeAudioClip([audio, music]))
    output_file = f"reel_{part_num}.mp4"
    final.write_videofile(output_file, fps=24, threads=4)
    
    # Cleanup
    os.remove("voice.mp3")
    return output_file

def upload_to_yt(video_path, part_num):
    # Create credentials from JSON
    creds_info = json.loads(YOUTUBE_CREDS)
    credentials = google.auth.credentials.Credentials.from_authorized_user_info(creds_info)
    
    youtube = build('youtube', 'v3', credentials=credentials)
    
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": f"Horror Part {part_num} | Roman Urdu",
                "description": open("hashtags.txt", "r").read(),
                "categoryId": "24"
            },
            "status": {"privacyStatus": "public"}
        },
        media_body=MediaFileUpload(video_path)
    )
    return request.execute()['id']

def main():
    for i in range(1, DAILY_UPLOADS+1):
        try:
            print(f"Processing reel {i}/{DAILY_UPLOADS}")
            script = generate_script()
            video_file = create_reel(script, i)
            vid_id = upload_to_yt(video_file, i)
            print(f"Uploaded Part {i}: {vid_id}")
            os.remove(video_file)
            if i < DAILY_UPLOADS:
                time.sleep(300)  # 5-min gap between uploads
        except Exception as e:
            print(f"Error in Part {i}: {str(e)}")

if __name__ == "__main__":
    main()
