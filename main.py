import os
import random
import time
import json
from datetime import datetime
from openai import OpenAI
from gtts import gTTS
import moviepy.editor as mpy
from moviepy.audio.fx import all as afx
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
EXACT_DURATION = 60  # Exactly 60 seconds for Shorts
DAILY_UPLOADS = 1  # Reduced to just 1 for testing

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Pre-defined scripts (you can replace these with your own)
PREDEFINED_SCRIPTS = [
    "Raat ke andhere mein ek ajeeb si aawaz aati thi. Har koi dar ke mare soya rehta tha. Ek din ek ladke ne socha ki woh jaakar dekhega ke aawaz kahan se aa rahi hai. Jab woh pahucha to usne dekha ek purani haveli mein roshni thi. Woh andar gaya to dekha ek budhiya baithi thi. Usne pucha, 'Kaun ho tum?' Budhiya ne muskurate hue kaha, 'Main tumhari daadi hoon.' Ladka dar gaya kyuki uski daadi to kayi saal pehle mar chuki thi. Budhiya ne kaha, 'Beta, main tumse ek kaam kehti hoon. Yeh haveli chhod kar chale jao.' Ladka bhaag gaya aur kabhi wapas nahi aaya. Part 2 ke liye follow karo!",
    "Ek chhota sa gaon tha jahan har saal ek ladki ki mysterious maut hoti thi. Log kehte the ki woh ek dayan ka shikaar hai. Ek din ek naya parivaar us gaon mein aakar basa. Unki ek beti thi jo bohot curious thi. Usne socha ki woh is rahasya ko solve karegi. Raat ko woh jungle mein gai jahan ladkiyon ki maut hoti thi. Wahan usne dekha ek lambi si parchhayi uski taraf badh rahi thi. Parchhayi ne kaha, 'Main tumhe bachana chahta hoon. Yeh jagah khatarnak hai.' Woh parchhayi ek bhoot tha jo khud ek shikaar thi. Usne bataya ki dayan har saal ek nayi ladki ko maut ke ghat utarti hai. Ab tumhari bari hai. Part 2 ke liye follow karo!",
    "Shahar ki ek puri imarat mein rehne wale log ek hafte ke andar gayab ho gaye. Police ne koi clue nahi paya. Ek journalist ne is mystery ko investigate karne ka faisla kiya. Wo imarat mein ghusa aur wahan usne dekha ki deewaron se khoon tapak raha hai. Usne ek basement ka darwaza dekha jo pehle kabhi nahi tha. Neeche utar kar usne dekha ki saare log ek bade se jaal mein phanse hue hain. Ek ajeeb si aakriti unki jaan le rahi thi. Wo aakriti journalist ki taraf mudi aur uski aankhein laal ho gayi. Wo bol, 'Tum agle ho.' Journalist ne apni camera chalayi aur bhaag kar police ko bulaaya. Part 2 ke liye follow karo!"
]

def generate_script():
    print("Using predefined script...")
    # Return a random predefined script
    return random.choice(PREDEFINED_SCRIPTS)

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
        # Get voice duration
        voice_clip = mpy.AudioFileClip("voice.mp3")
        voice_duration = voice_clip.duration
        print(f"Voice duration: {voice_duration} seconds")
        
        # Extend or trim voice to exactly 60 seconds
        if voice_duration < EXACT_DURATION:
            # If voice is shorter, extend it with silence
            silence_duration = EXACT_DURATION - voice_duration
            silence = mpy.AudioClip(lambda t: 0, duration=silence_duration)
            extended_voice = mpy.concatenate_audioclips([voice_clip, silence])
            final_voice = extended_voice.set_duration(EXACT_DURATION)
            print(f"Extended voice with {silence_duration} seconds of silence")
        else:
            # If voice is longer, trim it
            final_voice = voice_clip.subclip(0, EXACT_DURATION)
            print(f"Trimmed voice from {voice_duration} to {EXACT_DURATION} seconds")
        
        # Video processing - ensure exactly 60 seconds
        video = mpy.VideoFileClip(f"{BG_VIDEOS}/{bg}").subclip(0, EXACT_DURATION)
        
        # Music processing - ensure exactly 60 seconds
        music_clip = mpy.AudioFileClip(f"{BG_MUSIC}/{music}").volumex(0.3)
        if music_clip.duration < EXACT_DURATION:
            # Loop music if it's shorter than 60 seconds
            num_loops = int(EXACT_DURATION / music_clip.duration) + 1
            music_segments = [music_clip] * num_loops
            music_clip = mpy.concatenate_audioclips(music_segments)
        music_clip = music_clip.subclip(0, EXACT_DURATION)
        
        # Combine audio tracks
        final_audio = mpy.CompositeAudioClip([final_voice, music_clip])
        
        # Set audio to video
        final_video = video.set_audio(final_audio)
        
        # Export
        output_file = f"reel_{part_num}.mp4"
        print(f"Writing 60-second video file: {output_file}")
        final_video.write_videofile(
            output_file, 
            fps=24, 
            threads=4, 
            verbose=False, 
            logger=None,
            codec='libx264',
            audio_codec='aac'
        )
        
        # Close clips to free resources
        voice_clip.close()
        video.close()
        music_clip.close()
        
    except Exception as e:
        print(f"Video creation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # Cleanup
        if os.path.exists("voice.mp3"):
            os.remove("voice.mp3")
    
    return output_file

def upload_to_yt(video_path, part_num):
    print(f"Attempting to upload {video_path} to YouTube...")
    
    # Check if video file exists
    if not os.path.exists(video_path):
        print(f"Error: Video file {video_path} does not exist")
        return None
    
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
            hashtags = "#Horror #Story #Shorts #RomanUrdu #Scary"
        
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": f"Horror Part {part_num} | Roman Urdu",
                    "description": hashtags,
                    "categoryId": "24",
                    "tags": ["horror", "story", "shorts", "roman urdu", "scary"]
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
        import traceback
        traceback.print_exc()
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
                
        except Exception as e:
            print(f"Critical error in Part {i}: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
    print("Process completed!")
