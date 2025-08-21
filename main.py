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

# Configuration - ENSURE THESE ARE SET AS ENVIRONMENT VARIABLES
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
YOUTUBE_CREDS = os.getenv("YOUTUBE_CREDS")

if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY environment variable")
if not YOUTUBE_CREDS:
    raise RuntimeError("Missing YOUTUBE_CREDS environment variable")

# Path configuration
BG_VIDEOS = "assets/gaming_videos"
BG_MUSIC = "assets/horror_music"
MAX_DURATION = 60  # 60 seconds for Shorts
DAILY_UPLOADS = 10

# Initialize OpenAI client SAFELY
client = OpenAI(api_key=OPENAI_API_KEY)

def generate_script():
    prompt = """Roman Urdu mein exact 55 second ki horror story likho. Structure:
    1. Darawani shuruat (10 sec)
    2. Suspense (35 sec) 
    3. MUST END WITH: "Part 2 ke liye follow karo!" (10 sec)"""
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",  # Changed from gpt-4-turbo
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        max_tokens=300
    )
    return response.choices[0].message.content

def create_reel(script, part_num):
    # Random assets
    bg = random.choice(os.listdir(BG_VIDEOS))
    music = random.choice(os.listdir(BG_MUSIC))
    
    # Voiceover with error handling
    try:
        tts = gTTS(script, lang='ur')
        tts.save("voice.mp3")
    except Exception as e:
        print(f"gTTS failed: {str(e)}")
        return None
    
    try:
        # Video processing
        video = mpy.VideoFileClip(f"{BG_VIDEOS}/{bg}").subclip(0, MAX_DURATION)
        audio = mpy.AudioFileClip("voice.mp3").subclip(0, MAX_DURATION)
        music = mpy.AudioFileClip(f"{BG_MUSIC}/{music}").volumex(0.3)
        
        # Export
        final = video.set_audio(mpy.CompositeAudioClip([audio, music]))
        output_file = f"reel_{part_num}.mp4"
        final.write_videofile(output_file, fps=24, threads=4)
    except Exception as e:
        print(f"Video creation failed: {str(e)}")
        return None
    finally:
        # Cleanup even if errors occur
        if os.path.exists("voice.mp3"):
            os.remove("voice.mp3")
    
    return output_file

def upload_to_yt(video_path, part_num):
    # Create credentials from JSON
    try:
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
    except Exception as e:
        print(f"YouTube upload failed: {str(e)}")
        return None

def main():
    for i in range(1, DAILY_UPLOADS+1):
        try:
            print(f"Processing reel {i}/{DAILY_UPLOADS}")
            script = generate_script()
            video_file = create_reel(script, i)
            
            if not video_file:
                print(f"Skipping upload for Part {i} (creation failed)")
                continue
                
            vid_id = upload_to_yt(video_file, i)
            
            if vid_id:
                print(f"Uploaded Part {i}: {vid_id}")
            else:
                print(f"Upload failed for Part {i}")
                
            if os.path.exists(video_file):
                os.remove(video_file)
                
            if i < DAILY_UPLOADS:
                time.sleep(300)  # 5-min gap between uploads
        except Exception as e:
            print(f"Critical error in Part {i}: {str(e)}")
            # Add retry logic or break if needed

if __name__ == "__main__":
    main()
