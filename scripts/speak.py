import gtts
import os
from playsound import playsound
import requests
from config import Config
cfg = Config()


# TODO: Nicer names for these ids
voices = ["ErXwobaYiN019PkySvjV", "EXAVITQu4vr4xnSDxMaL"]

tts_headers = {
    "Content-Type": "application/json",
    "xi-api-key": cfg.elevenlabs_api_key
}


def eleven_labs_speech(text, voice_index=0):
    """Speak text using elevenlabs.io's API"""
    tts_url = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}".format(
        voice_id=voices[voice_index])
    formatted_message = {"text": text}
    response = requests.post(
        tts_url, headers=tts_headers, json=formatted_message)

    if response.status_code == 200:
        with open("speech.mpeg", "wb") as f:
            f.write(response.content)
        playsound("speech.mpeg")
        os.remove("speech.mpeg")
        return True
    else:
        print("Request failed with status code:", response.status_code)
        print("Response content:", response.content)
        return False


def brian_speech(text):
    """Speak text using Brian with the streamelements API"""
    tts_url = f"https://api.streamelements.com/kappa/v2/speech?voice=Brian&text={text}"
    response = requests.get(tts_url)

    if response.status_code == 200:
        with open("speech.mp3", "wb") as f:
            f.write(response.content)
        playsound("speech.mp3")
        os.remove("speech.mp3")
        return True
    else:
        print("Request failed with status code:", response.status_code)
        print("Response content:", response.content)
        return False


def gtts_speech(text):
    tts = gtts.gTTS(text)
    tts.save("speech.mp3")
    playsound("speech.mp3")
    os.remove("speech.mp3")


def macos_tts_speech(text):
    os.system(f'say "{text}"')


def say_text(text, voice_index=0):
    if not cfg.elevenlabs_api_key:
        if cfg.use_mac_os_tts == 'True':
            macos_tts_speech(text)
        elif cfg.use_brian_tts == 'True':
            success = brian_speech(text)
            if not success:
                gtts_speech(text)
        else:
            gtts_speech(text)
    else:
        success = eleven_labs_speech(text, voice_index)
        if not success:
            gtts_speech(text)
