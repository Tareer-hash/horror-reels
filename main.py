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

print("Checking environment variables...")
print(f"OpenAI key exists: {bool(OPENAI_API_KEY)}")
print(f"YouTube creds exist: {bool(YOUTUBE_CREDS)}")

if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY environment variable")
if not YOUTUBE_CREDS:
    raise RuntimeError("Missing YOUTUBE_CREDS environment variable")

# Path configuration
BG_VIDEOS = "assets/gaming_videos"
BG_MUSIC = "assets/horror_music"
MAX_DURATION = 60  # 60 seconds for Shorts
DAILY_UPLOADS = 2  # Reduced for testing

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

def generate_script():
    print("Generating script with OpenAI...")
    prompt = """Roman Urdu mein exact 55 second ki horror story likho. Structure:
    1. Darawani shuruat (10 sec)
    2. Suspense (35 sec) 
    3. MUST END WITH: "Part 2 ke liye follow karo!" (10 sec)"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
            max_tokens=300
        )
        script = response.choices[0].message.content
        print(f"Script generated: {script[:100]}...")  # Show first 100 chars
        return script
    except Exception as e:
        print(f"Error generating script: {str(e)}")
        return None

def create_reel(script, part_num):
    print(f"Creating reel {part_num}...")
    
    # Check if assets exist
    if not os.path.exists(BG_VIDEOS) or not os.listdir(BG_VIDEOS):
        print(f"Error: No video files found in {BG_VIDEOS}")
        return None
        
    if not os.path.exists(BG_MUSIC) or not os.listdir(BG_MUSIC):
        print(f"Error: No music files found in {BG_MUSIC}")
        return None
    
    # Random assets
    try:
        bg = random.choice([f for f in os.listdir(BG_VIDEOS) if f.endswith('.mp4')])
        music = random.choice([f for f in os.listdir(BG_MUSIC) if f.endswith('.mp3')])
        print(f"Using video: {bg}, music: {music}")
    except IndexError:
        print("Error: No valid video or music files found")
        return None
    
    # Voiceover
    try:
        print("Generating voiceover...")
        tts = gTTS(script, lang='ur')
        tts.save("voice.mp3")
    except Exception as e:
        print(f"gTTS failed: {str(e)}")
        return None
    
    try:
        # Video processing
        print("Processing video...")
        video = mpy.VideoFileClip(f"{BG_VIDEOS}/{bg}").subclip(0, MAX_DURATION)
        audio = mpy.AudioFileClip("voice.mp3").subclip(0, MAX_DURATION)
        music_clip = mpy.AudioFileClip(f"{BG_MUSIC}/{music}").volumex(0.3)
        
        # Export
        final = video.set_audio(mpy.CompositeAudioClip([audio, music_clip]))
        output_file = f"reel_{part_num}.mp4"
        print(f"Writing video file: {output_file}")
        final.write_videofile(output_file, fps=24, threads=4, verbose=False, logger=None)
    except Exception as e:
        print(f"Video creation failed: {str(e)}")
        return None
    finally:
        # Cleanup
        if os.path.exists("voice.mp3"):
            os.remove("voice.mp3")
    
    return output_file

def upload_to_yt(video_path, part_num):
    print(f"Attempting to upload {video_path} to YouTube...")
    
    # Create credentials from JSON
    try:
        creds_info = json.loads(YOUTUBE_CREDS)
        credentials = google.auth.credentials.Credentials.from_authorized_user_info(creds_info)
        
        youtube = build('youtube', 'v3', credentials=credentials)
        
        # Read hashtags
        try:
            with open("hashtags.txt", "r") as f:
                hashtags = f.read()
        except:
            hashtags = "#Horror #Story #Shorts"
        
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": f"Horror Part {part_num} | Roman Urdu",
                    "description": hashtags,
                    "categoryId": "24"
                },
                "status": {"privacyStatus": "public"}
            },
            media_body=MediaFileUpload(video_path)
        )
        response = request.execute()
        print(f"Upload successful! Video ID: {response['id']}")
        return response['id']
    except Exception as e:
        print(f"YouTube upload failed: {str(e)}")
        return None

def main():
    print("Starting main process...")
    
    for i in range(1, DAILY_UPLOADS+1):
        try:
            print(f"\n--- Processing reel {i}/{DAILY_UPLOADS} ---")
            
            # Generate script
            script = generate_script()
            if not script:
                print("Skipping due to script generation failure")
                continue
                
            # Create video
            video_file = create_reel(script, i)
            if not video_file:
                print("Skipping due to video creation failure")
                continue
                
            # Upload to YouTube
            vid_id = upload_to_yt(video_file, i)
            if vid_id:
                print(f"Successfully uploaded Part {i}: {vid_id}")
            else:
                print(f"Upload failed for Part {i}")
                
            # Cleanup
            if os.path.exists(video_file):
                os.remove(video_file)
                
            # Wait between uploads
            if i < DAILY_UPLOADS:
                print("Waiting 5 minutes before next upload...")
                time.sleep(300)  # 5-min gap between uploads
                
        except Exception as e:
            print(f"Critical error in Part {i}: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
    print("Process completed!")
