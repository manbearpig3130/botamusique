# coding=utf-8
import logging
import secrets
import datetime
import json
import re
import pymumble_py3 as pymumble
import requests

from constants import tr_cli as tr
from constants import commands
import interface
import util
import variables as var
from pyradios import RadioBrowser
from database import SettingsDatabase, MusicDatabase, Condition
import media.playlist
from media.item import item_id_generators, dict_to_item, dicts_to_items, ValidationFailedError
from media.cache import get_cached_wrapper_from_scrap, get_cached_wrapper_by_id, get_cached_wrappers_by_tags, \
    get_cached_wrapper, get_cached_wrappers, get_cached_wrapper_from_dict, get_cached_wrappers_from_dicts
from media.url_from_playlist import get_playlist_info

# Manbearpig's imports
import openai, os, wget, base64, subprocess, threading, time, glob
from google.cloud import texttospeech
from google.api_core.exceptions import InvalidArgument
from io import BytesIO
from PIL import Image
from pydub import AudioSegment
import random
import pprint

log = logging.getLogger("bot")

def register_all_commands(bot):
    bot.register_command(commands('add_from_shortlist'), cmd_shortlist)
    bot.register_command(commands('add_tag'), cmd_add_tag)
    bot.register_command(commands('change_user_password'), cmd_user_password, no_partial_match=True)
    bot.register_command(commands('clear'), cmd_clear)
    bot.register_command(commands('current_music'), cmd_current_music)
    bot.register_command(commands('delete_from_library'), cmd_delete_from_library)
    bot.register_command(commands('ducking'), cmd_ducking)
    bot.register_command(commands('ducking_threshold'), cmd_ducking_threshold)
    bot.register_command(commands('ducking_volume'), cmd_ducking_volume)
    bot.register_command(commands('find_tagged'), cmd_find_tagged)
    bot.register_command(commands('help'), cmd_help, no_partial_match=False, access_outside_channel=True)
    bot.register_command(commands('joinme'), cmd_joinme, access_outside_channel=True)
    bot.register_command(commands('last'), cmd_last)
    bot.register_command(commands('list_file'), cmd_list_file)
    bot.register_command(commands('mode'), cmd_mode)
    bot.register_command(commands('pause'), cmd_pause)
    bot.register_command(commands('play'), cmd_play)
    bot.register_command(commands('play_file'), cmd_play_file)
    bot.register_command(commands('play_file_match'), cmd_play_file_match)
    bot.register_command(commands('play_playlist'), cmd_play_playlist)
    bot.register_command(commands('play_radio'), cmd_play_radio)
    bot.register_command(commands('play_tag'), cmd_play_tags)
    bot.register_command(commands('play_url'), cmd_play_url)
    bot.register_command(commands('queue'), cmd_queue)
    bot.register_command(commands('random'), cmd_random)
    bot.register_command(commands('rb_play'), cmd_rb_play)
    bot.register_command(commands('rb_query'), cmd_rb_query)
    bot.register_command(commands('remove'), cmd_remove)
    bot.register_command(commands('remove_tag'), cmd_remove_tag)
    bot.register_command(commands('repeat'), cmd_repeat)
    bot.register_command(commands('requests_webinterface_access'), cmd_web_access)
    bot.register_command(commands('rescan'), cmd_refresh_cache, no_partial_match=True)
    bot.register_command(commands('search'), cmd_search_library)
    bot.register_command(commands('skip'), cmd_skip)
    bot.register_command(commands('stop'), cmd_stop)
    bot.register_command(commands('stop_and_getout'), cmd_stop_and_getout)
    bot.register_command(commands('version'), cmd_version, no_partial_match=True)
    bot.register_command(commands('volume'), cmd_volume)
    bot.register_command(commands('yt_play'), cmd_yt_play)
    bot.register_command(commands('yt_search'), cmd_yt_search)

    # admin command
    bot.register_command(commands('add_webinterface_user'), cmd_web_user_add, admin=True)
    bot.register_command(commands('drop_database'), cmd_drop_database, no_partial_match=True, admin=True)
    bot.register_command(commands('kill'), cmd_kill, admin=True)
    bot.register_command(commands('list_webinterface_user'), cmd_web_user_list, admin=True)
    bot.register_command(commands('remove_webinterface_user'), cmd_web_user_remove, admin=True)
    bot.register_command(commands('update'), cmd_update, no_partial_match=True, admin=True)
    bot.register_command(commands('url_ban'), cmd_url_ban, no_partial_match=True, admin=True)
    bot.register_command(commands('url_ban_list'), cmd_url_ban_list, no_partial_match=True, admin=True)
    bot.register_command(commands('url_unban'), cmd_url_unban, no_partial_match=True, admin=True)
    bot.register_command(commands('url_unwhitelist'), cmd_url_unwhitelist, no_partial_match=True, admin=True)
    bot.register_command(commands('url_whitelist'), cmd_url_whitelist, no_partial_match=True, admin=True)
    bot.register_command(commands('url_whitelist_list'), cmd_url_whitelist_list, no_partial_match=True, admin=True)
    bot.register_command(commands('user_ban'), cmd_user_ban, no_partial_match=True, admin=True)
    bot.register_command(commands('user_unban'), cmd_user_unban, no_partial_match=True, admin=True)

    ## Custom commands
    bot.register_command(commands('blockheight'), cmd_get_blockheight)
    bot.register_command(commands('gpt'), cmd_gpt)
    bot.register_command(commands('gptp'), cmd_gptp)
    bot.register_command(commands('gpt_reset'), cmd_gpt_reset)
    bot.register_command(commands('gpts'), cmd_gpts)
    bot.register_command(commands('dalle_gen'), cmd_dalle_gen)
    bot.register_command(commands('listen'), cmd_listen)
    bot.register_command(commands('listening'), cmd_listening)
    bot.register_command(commands('roll'), cmd_roll)
    bot.register_command(commands('gpt_model'), cmd_set_gpt_model)
    bot.register_command(commands('jailbreak'), cmd_jailbreak)
    bot.register_command(commands('load'), cmd_load)
    bot.register_command(commands('debug'), cmd_print_debug)

    # Just for debug use
    bot.register_command('rtrms', cmd_real_time_rms, True)
    # bot.register_command('loop', cmd_loop_state, True)
    # bot.register_command('item', cmd_item, True)

def send_multi_lines(bot, lines, text, linebreak="<br />"):
    global log

    msg = ""
    br = ""
    for newline in lines:
        msg += br
        br = linebreak
        if bot.mumble.get_max_message_length() \
                and (len(msg) + len(newline)) > (bot.mumble.get_max_message_length() - 4):  # 4 == len("<br>")
            bot.send_msg(msg, text)
            msg = ""
        msg += newline

    bot.send_msg(msg, text)

def send_multi_lines_in_channel(bot, lines, linebreak="<br />"):
    global log

    msg = ""
    br = ""
    for newline in lines:
        msg += br
        br = linebreak
        if bot.mumble.get_max_message_length() \
                and (len(msg) + len(newline)) > (bot.mumble.get_max_message_length() - 4):  # 4 == len("<br>")
            bot.send_channel_msg(msg)
            msg = ""
        msg += newline
    bot.send_channel_msg(msg)


## Splits long messages into multiple messages if they exceed the maximum allowed length
def send_split_message_in_channel(bot, message):
    max_message_length = bot.mumble.get_max_message_length()

    def split_message_at_spaces(message, max_length):
        words = message.split(' ')
        message_parts = []
        current_part = ''
        for word in words:
            if len(current_part) + len(word) + 1 > max_length:
                message_parts.append(current_part.strip())
                current_part = ''
            current_part += ' ' + word
        message_parts.append(current_part.strip())
        return message_parts

    if max_message_length:
        # Split the message into smaller parts if it exceeds the maximum allowed length
        message_parts = split_message_at_spaces(message, max_message_length)
    else:
        # If there's no maximum length set, send the message as is
        message_parts = [message]

    for msg_part in message_parts:
        bot.send_channel_msg(msg_part)

def send_item_added_message(bot, wrapper, index, text):
    if index == var.playlist.current_index + 1:
        bot.send_msg(tr('file_added', item=wrapper.format_song_string()) +
                     tr('position_in_the_queue', position=tr('next_to_play')), text)
    elif index == len(var.playlist) - 1:
        bot.send_msg(tr('file_added', item=wrapper.format_song_string()) +
                     tr('position_in_the_queue', position=tr('last_song_on_the_queue')), text)
    else:
        bot.send_msg(tr('file_added', item=wrapper.format_song_string()) +
                     tr('position_in_the_queue', position=f"{index + 1}/{len(var.playlist)}."), text)


## Generate an image from text with Dalle-2
def dalle_gen(inprompt):
    global log

    openai.api_key = var.config.get("bot", "openai_api_key")
    image_resp = openai.Image.create(prompt=inprompt, n=1, size="256x256")
    url = image_resp['data'][0]['url']
    filename = str(datetime.datetime.now().strftime('%d%b%y-%H%M%S-%f')[:-3]) + ".png"
    path = var.config.get("bot", "dalle_folder")
    wget.download(url, path + filename)
    log.info(f"Downloaded {filename} from DALL-E: {url}")
    return url, path + filename


## Text goes in, GPT response comes out
def ask_gpt(bot, input, user):
    #global currentMessages
    global log

    openai.api_key = var.config.get("bot", "openai_api_key")
    var.config.get("server", "host")
    bot.currentMessages.append({"role": "user", "content": user + ": " + input})
    response = openai.ChatCompletion.create(
        model=bot.gpt_model,
        temperature=float(var.config.get("bot", "gpt_temperature")),
        max_tokens=600,
        messages=bot.currentMessages
    )
    chatResponse = response['choices'][0]['message']['content']
    bot.currentMessages.append({"role": "assistant", "content": chatResponse})
    log.info(f"GPT Response: {chatResponse}")
    #pprint.pprint(bot.currentMessages)
    return chatResponse


## Welcome messages from GPT. This is a separate function because it needs to be called from the on_user_join event
def gpt_welcome(bot, input, user):
    #global welcomeMessages

    openai.api_key = var.config.get("bot", "openai_api_key")
    bot.welcomeMessages.append({"role": "system", "content": input})
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        temperature=float(var.config.get("bot", "gpt_temperature")),
        max_tokens=400,
        messages=bot.welcomeMessages
    )
    ## Keep the list at 5 messages to avoid racking up too many tokens just for welcome messages
    if len(bot.welcomeMessages) >= 5:
        for message in bot.welcomeMessages:
            if "has joined the server." in message['content']:
                bot.welcomeMessages.remove(message)
            bot.welcomeMessages.pop(1)
                
    chatResponse = response['choices'][0]['message']['content']
    bot.welcomeMessages.append({"role": "assistant", "content": chatResponse})
    return chatResponse


## Input text gets sent to google text to speech and the mp3 file is returned
def voice(txt):
    global log

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = var.config.get("bot", "google_application_credentials")
    voiceFolder = var.config.get("bot", "voice_folder")
    client = texttospeech.TextToSpeechClient()
    voice = texttospeech.VoiceSelectionParams(language_code="en-GB", name="en-GB-Neural2-B")
    audio_config=texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    synth_input = texttospeech.SynthesisInput(ssml=txt)
    try:
        ## Synthesize the text to speech
        response = client.synthesize_speech(input=synth_input, voice=voice, audio_config=audio_config)
    except InvalidArgument as e:
        log.info(f"Input wasn't valid SSML. Using regular txt instead. {e}")
        synth_input = texttospeech.SynthesisInput(text=txt)
        voice = texttospeech.VoiceSelectionParams(language_code="en-GB", name="en-GB-Wavenet-B")
        response = client.synthesize_speech(input=synth_input, voice=voice, audio_config=audio_config)
    
    ## Save the response as an mp3 file
    filename = str(datetime.datetime.now().strftime('%d%b%y-%H%M%S-%f')[:-3]) + "gpt-voice.mp3"
    with open(voiceFolder + filename, "wb") as out:
        out.write(response.audio_content)
    return filename


## Play the voiceResponse .mp3 file with ffmpeg
def speak(bot, voiceResponse):
    voiceFolder = var.config.get("bot", "voice_folder")
    command = ["ffmpeg", "-i", voiceFolder + voiceResponse, "-acodec", "pcm_s16le", "-f", "s16le", "-ac", "2", "-af", "aresample=48000", "-ar", "48000",  "-"]
    sound = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=1024)
    while True:
        data = sound.stdout.read(1024)
        if not data:
            break
        bot.mumble.sound_output.add_sound(data)


## When a user joins, send a welcome message and update the users_message
def on_user_join(user, bot):
    global log

    log.info(f"{user['name']} has joined the server. Preparing GPT Welcome message...")
    pretext = f"(SSML) The user {user['name']} has joined the server. VERY briefly welcome them to the server with a joke about their name."
    welcomeResponse = gpt_welcome(bot, pretext, user['name'])
    log.info(f"GPT: {welcomeResponse}")
    voiceResponse = voice(welcomeResponse)
    speak(bot, voiceResponse)
    set_users_message(bot)
    bot.send_channel_msg(welcomeResponse)
    user.send_text_message(f"Type !help to get a list of commands")


## Convert raw PCM audio to MP3
def convert_raw_to_mp3(raw_file_path, mp3_file_path, sample_rate=48000, channels=2):
    # Import raw PCM audio
    audio = AudioSegment.from_file(raw_file_path, format="raw", frame_rate=sample_rate, channels=channels, sample_width=2)
    # Export the audio as an MP3 file
    audio.export(mp3_file_path, format="mp3")


## Run on_user_join in a separate thread so that it doesn't block the main thread
def on_user_join_threaded(user, bot):
    t = threading.Thread(target=on_user_join, name="UserJoinThread", args=(user, bot))
    t.start()


## When a user leaves the server, update users_message and remove them from the current_speaker_list
def on_user_leave(user, event, bot):
    global log

    set_users_message(bot)
    log.info(f"{user['name']} has left the server.")
    if bot.listening:
        if user['name'] in bot.current_speaker_list:
            bot.current_speaker_list.remove(user['name'])
            bot.send_channel_msg(f"{user['name']} has left the server. No longer listening to {user['name']}.")


## Run on_user_leave in a separate thread so that it doesn't block the main thread
def on_user_leave_threaded(user, event, bot):
    t2 = threading.Thread(target=on_user_leave, name="UserLeaveThread", args=(user, event, bot))
    t2.start()

#Transcribe mp3 file with openai:
def transcribe_mp3(mp3_file_path):
    openai.api_key = var.config.get("bot", "openai_api_key")
    mp3_file = open(mp3_file_path, "rb")
    transcription = openai.Audio.transcribe("whisper-1", mp3_file)
    return transcription.text

## When a user who BotWatch is listening to speaks, this function is called to record their audio
def listen_handler(user, soundchunk, bot):
    global log

    if user['name'] in bot.current_speaker_list:
        bot.last_recieved_timestamps[user['name']] = time.time()
        path = f"{var.config.get('bot', 'tmp_folder')}{user['name']}.raw"
        with open(path, "ab") as f:
            f.write(soundchunk.pcm)
        print(".", end="", flush=True)


## Run the listen_handler function in a separate thread
def listen_handler_threaded(user, soundchunk, bot):
    t3 = threading.Thread(target=listen_handler, name="listenHandlerThread", args=(user, soundchunk, bot))
    t3.start()


## Sets the users message to the current list of users on the server, so BotWallis knows who is present
def set_users_message(bot):
    #global currentMessages

    names = []
    for usr in bot.mumble.users:
        names.append(bot.mumble.users[usr]['name'])
    namesMessage = "Currently present members on the Mumble server are: {}"
    namesMessage = namesMessage.format(', '.join(f"'{x}'" for x in names))

    # Replace the old names message with the new one if it exists, otherwise add it:
    updated = False
    for i, my_dict in enumerate(bot.currentMessages):
        for key, value in my_dict.items():
            if "Currently present members on the Mumble server are: " in value:
                bot.currentMessages[i][key] = namesMessage
                updated = True
    if updated == False:
        bot.currentMessages.append({"role": "system", "content": namesMessage})
    log.info(namesMessage)

## Initialize the GPT stuff. This is called when the bot starts up and when the bot is reset:
def gpt_init(bot, save=False):
    global log

    # If being reset, write currentMessages to a .json file:
    if save == True and len(bot.currentMessages) > 6 and bot.loadedConversation == False:
        timestamp = str(datetime.datetime.now().strftime('%d%b%y-%H%M%S-%f')[:-3])
        chatlogPath = var.config.get("bot", "chatlog_folder")
        filepath = f"{chatlogPath}{timestamp}-chat.json"
        with open(filepath, 'w') as f:
            json.dump(bot.currentMessages, f, indent=4)
        log.info(f"Saved last conversation to {filepath}")
    
    # Reset conversation history - clear currentMessages and add default messages:
    var.config.read('configuration.ini')
    bot.loadedConversation = False
    bot.defaultMessages.clear()
    bot.defaultMessages = [
    {"role": "system", "content": f"{var.config.get('bot', 'gpt_system_message')}"}
    ]
    if bot.jailbreak:
        bot.jailbreakPrompt = bot.jailbreakPrompt
        bot.defaultMessages.append({"role": "system", "content": f"{bot.jailbreakPrompt}"})
    bot.currentMessages.clear()
    for msg in bot.defaultMessages:
        bot.currentMessages.append(msg)
        bot.welcomeMessages.append(msg)

    ## Reset GPT model
    bot.gpt_model = var.config.get("bot", "gpt_model")

    ## Stop listening to users who BotWallis is currently listening to:
    bot.current_speaker_list.clear()
    
    # Get list of users on the Mumble server and add it to currentMessages:
    set_users_message(bot)

    # log some info:
    log.info("Max message size: " + str(bot.mumble.get_max_message_length()))
    log.info("AI Initialized")

## Magic to allow images to be sent in the chat:
def prepare_thumbnail(im):
    im.thumbnail((100, 100), Image.ANTIALIAS)
    buffer = BytesIO()
    im = im.convert('RGB')
    im.save(buffer, format="JPEG")
    return base64.b64encode(buffer.getvalue()).decode('utf-8')

## Function to return a user's ID by their name:
def get_user_by_name(bot, name):
    for user in bot.mumble.users:
        if bot.mumble.users[user]['name'] == name:
            return user


def ask_gpt_thread(bot, input, user, result_container):
    result_container.append(ask_gpt(bot, input, user))

def voice_response_thread(bot, input, result_container):
    result_container.append(voice(input))

## When BotWallis is listening, and a user stops talking, this function is called:
def handle_user_inactivity(user, bot):
    global log
    
    print(f"{user} has stopped sending sound")
    log.info(f"Converting {user}.raw to mp3")
    convert_raw_to_mp3(f"{var.config.get('bot', 'tmp_folder')}{user}.raw", f"{var.config.get('bot', 'tmp_folder')}{user}.mp3")
    os.remove(f"{var.config.get('bot', 'tmp_folder')}{user}.raw")
    log.info(f"Transcribing {user}.mp3")
    u = get_user_by_name(bot, user)
    try:
        transcription = transcribe_mp3(f"{var.config.get('bot', 'tmp_folder')}{user}.mp3")
    except openai.error.InvalidRequestError as e:
        bot.mumble.users[u].send_text_message(f"Error: {e}")
        log.info(f"Error: {e}")
        return

    log.info(f"{transcription}")
    if transcription == "":
        log.info(f"Transcription was empty. Skipping.")
        bot.mumble.users[u].send_text_message(f"Transcription was empty. Skipping.")
        return
    
    bot.mumble.users[u].send_text_message(f"Transcription: {transcription}")
    pretext = "(SSML) "
    print("Getting GPT response.", end="")
    result_container = []
    gthread = threading.Thread(target=ask_gpt_thread, name="askGptThread", args=(bot, pretext + transcription, user, result_container))
    gthread.start()
    while gthread.is_alive():
        print(".", end="", flush=True)
        time.sleep(0.25)
    gptResponse = result_container[0]
    send_split_message_in_channel(bot, gptResponse)

    vthread = threading.Thread(target=voice_response_thread, name="voiceResponseThread", args=(bot, gptResponse, result_container))
    vthread.start()
    print("\nGetting voice response.", end="")
    while vthread.is_alive():
        print(".", end="", flush=True)
        time.sleep(0.25)
    voiceResponse = result_container[1]
    speak(bot, voiceResponse)


## Tracks the last time a user sent sound, and if they haven't sent sound for a while, calls handle_user_inactivity():
def check_inactivity_thread(bot):
    global log
    timeout = 0.5

    while not bot.stop_event.is_set():
        current_time = time.time()
        inactive_users = [username for username, timestamp in bot.last_recieved_timestamps.items() if current_time - timestamp > timeout]
        for user in inactive_users:
            log.info(f"No sound recieved for {timeout} seconds from {user}.")
            handle_user_inactivity(user, bot)
            del bot.last_recieved_timestamps[user]
        time.sleep(0.1)


## Function to toggle listening thread:
def toggle_listening(bot):
    global log

    bot.listening = not bot.listening
    if bot.listening == True:
        bot.mumble.set_receive_sound(1)
        bot.stop_event = threading.Event()
        bot.inactivity_thread = threading.Thread(target=check_inactivity_thread, args=(bot,), name="inactivityThread")
        bot.inactivity_thread.start()
        log.info("BotWallis is now listening.")
    else:
        bot.mumble.set_receive_sound(0)
        bot.stop_event.set()
        bot.inactivity_thread.join()
        log.info("BotWallis is no longer listening.")


## get, set or list GPT models:
def set_gpt_model(bot, model):
    global log

    if model == "":
        return f"Current GPT model: {bot.gpt_model}"
    openai.api_key = var.config.get("bot", "openai_api_key")
    modelsDict = openai.Model.list()
    models = []
    for m in modelsDict['data']:
        models.append(m['id'])
    
    if model in models:
        bot.gpt_model = model
        log.info(f"Set GPT model to {model}")
        return f"Set GPT model to {model}"
    elif model == "list":
        return f"Available models: {models}"
    else:
        return f"Model {model} not found. Type '!gpt_model list' to see available models."

def load_conversation(bot, filename, setusers=True):
    global log

    path = var.config.get("bot", "chatlog_folder")
    if not os.path.isabs(filename):
        filename = os.path.join(path, filename)
    
    ## load json from file:
    with open((filename), 'r') as f:
        data = json.load(f)
    bot.currentMessages.clear()
    for message in data:
        #pprint.pprint(message)
        bot.currentMessages.append(message)
    log.info(f"Loaded conversation from {filename}")
    bot.loadedConversation = True
    if setusers:
        set_users_message(bot)
    #pprint.pprint(bot.currentMessages)


# ------------------------------------ Variables ------------------------------------
ITEMS_PER_PAGE = 50
song_shortlist = []
# ------------------------------------ Commands ------------------------------------

## Toggle listening for specified user, or user who called the command if input is blank
def cmd_listen(bot, user, text, command, parameter):
    global log

    if parameter == '':
        if user not in bot.current_speaker_list:
            bot.current_speaker_list.append(user)
            l = True
        else:
            bot.current_speaker_list.remove(user)
            l = False
        bot.send_channel_msg(tr('listen', user=user, l=l))
    elif get_user_by_name(bot, parameter):
        if parameter not in bot.current_speaker_list:
            bot.current_speaker_list.append(parameter)
            l = True
        else:
            bot.current_speaker_list.remove(parameter)
            l = False
        bot.send_channel_msg(tr('listen', user=parameter, l=l))
    else:
        bot.send_channel_msg(f"Can't find user {parameter}")
        

## Set the GPT model to use. If no model is specified, return the current model. If "list" is specified, return a list of available models.
def cmd_set_gpt_model(bot, user, text, command, parameter):
    global log

    m = set_gpt_model(bot, parameter)
    if "Available models: " in m:
        bot.send_msg(m, text)
    else:
        bot.send_channel_msg(m)


## Toggle listening thread on/off
def cmd_listening(bot, user, text, command, parameter):
    global log
    toggle_listening(bot)

## Load a previous conversation
def cmd_load(bot, user, text, command, parameter):
    global log

    def get_last_x_files(x, startfrom=0):
        files = glob.glob(os.path.join(var.config.get("bot", "chatlog_folder"), "*"))
        files.sort(key=os.path.getmtime, reverse=True)
        start_index = startfrom
        end_index = start_index + x
        recent_files = files[start_index:end_index]
        numbered_files = [(i + 1 + startfrom, file) for i, file in enumerate(recent_files)]
        return numbered_files
    
    def is_pattern(s):
        pattern = r'^s\d+$'
        return bool(re.match(pattern, s))

    def is_int(s):
        try:
            int(s)
            return True
        except ValueError:
            return False

    if parameter == "":
        msg = _format_chatlogs(get_last_x_files(10))
        bot.send_msg(f"{msg}", text)
    if is_pattern(parameter):
        n = int(parameter[1:])
        msg = _format_chatlogs(get_last_x_files(10, n))
        bot.send_msg(f"{msg}", text)
    elif ".json" in parameter:
        load_conversation(bot, parameter)
        bot.send_msg(f"Loaded conversation from {parameter}", text)
    elif is_int(parameter):
        numbered_files = get_last_x_files(int(parameter))
        try:
            load_conversation(bot, numbered_files[int(parameter) - 1][1])
            bot.send_msg(f"Loaded conversation from {numbered_files[int(parameter) - 1][1]}", text)
        except IndexError:
            bot.send_msg(f"Invalid index {parameter}", text)

## Ask BotWallis to join the channel which the calling user is in. Optional token provided as argument if required
def cmd_joinme(bot, user, text, command, parameter):
    global log
    bot.mumble.users.myself.move_in(
        bot.mumble.users[text.actor]['channel_id'], token=parameter)

def cmd_print_debug(bot, user, text, command, parameter):
    global log
    pprint.pprint(bot.currentMessages)


def cmd_jailbreak(bot, user, text, command, parameter):
    global log

    if parameter == "list" or parameter == "print":
        bot.send_msg(f"{bot.jailbreakPrompt}", text)
        return

    elif parameter.startswith("set "):
        bot.jailbreakPrompt = parameter[4:]
        bot.send_msg(f"Set jailbreak prompt", text)
    elif parameter == "reset":
        gpt_init(bot)
        bot.jailbreakPrompt = var.config.get('bot', 'jailbreak_message')
        bot.send_msg(f"Reset jailbreak prompt. Resetting...", text)
        return
    else:
        bot.jailbreak = not bot.jailbreak
        if bot.jailbreak:
            bot.send_channel_msg(f"Applied jailbreak prompt. Resetting...")
        else:
            bot.send_channel_msg(f"Removed jailbreak prompt. Resetting...")
    gpt_init(bot)
    bot.send_msg(tr('gpt_reset', model=bot.gpt_model), text)

## Roll a die. This way we don't consume a kettle's worth of electricity when asking GPT to do it every time.
def cmd_roll(bot, user, text, command, parameter):
    global log

    def borked(bot, user):
        bot.send_channel_msg(f"{user} appears to be retarded. Rolling a d6.")
        result = random.randint(1, 6)
        bot.send_channel_msg(tr('roll', user=user, max=6, result=result))

    if len(parameter.split(" ")) == 2:
        num1 = parameter.split(" ")[0]
        num2 = parameter.split(" ")[1]
        try:
            result = random.randint(int(num1), int(num2))
            bot.send_channel_msg(tr('roll', user=user, max=num2, result=result))
        except:
            borked(bot, user)
    elif len(parameter.split(" ")) == 1 and parameter != "":
        num1 = parameter.split(" ")[0]
        try:
            result = random.randint(1, int(num1))
            bot.send_channel_msg(tr('roll', user=user, max=num1, result=result))
        except:
            borked(bot, user)
    elif parameter == "":
        result = random.randint(1, 6)
        bot.send_channel_msg(tr('roll', user=user, max=6, result=result))
    else:
        borked(bot, user)


## Get Bitcoin blockchain info
def cmd_get_blockheight(bot, user, text, command, parameter):
    global log
    r = requests.get('http://127.0.0.1:8332/rest/chaininfo.json')
    blockdata = r.json()
    msg = _format_chaininfo(blockdata)
    bot.send_msg(tr('blockheight', block=msg), text)


## Generate an image with DALL-E 2.0 from input text
def cmd_dalle_gen(bot, user, text, command, parameter):
    global log
    url, filename = dalle_gen(parameter)
    im = Image.open(filename)
    thumbnail = prepare_thumbnail(im)
    for user in bot.mumble.users:
        bot.mumble.users[user].send_text_message(tr('dalle_gen', response=url, prompt="Generated image"))
    bot.send_channel_msg('<br /><img width="200" src="data:image/png;base64,' + str(thumbnail) + '"/>')


## Ask GPT to generate a response in text
def cmd_gpt(bot, user, text, command, parameter):
    global log
    r = ask_gpt(bot, parameter, user)
    send_split_message_in_channel(bot, r)


## Ask GPT to generate a response in text, responding via private message
def cmd_gptp(bot, user, text, command, parameter):
    global log
    r = ask_gpt(bot, parameter, user)
    bot.send_msg(tr('gptp', response=r), text)


## Ask GPT to generate a response and speak it out with google text-to-speech engine
def cmd_gpts(bot, user, text, command, parameter):
    global log
    pretext = "(SSML) "
    gptResponse = ask_gpt(bot, pretext + parameter, user)
    send_split_message_in_channel(bot, gptResponse)
    voiceResponse = voice(gptResponse)
    speak(bot, voiceResponse)
    

## Reset the GPT conversation history and GPT model. Stops listening
def cmd_gpt_reset(bot, user, text, command, parameter):
    global log
    gpt_init(bot, save=True)
    bot.send_msg(tr('gpt_reset', model=bot.gpt_model), text)


def cmd_user_ban(bot, user, text, command, parameter):
    global log

    if parameter:
        var.db.set("user_ban", parameter, None)
        bot.send_msg(tr("user_ban_success", user=parameter), text)
    else:
        ban_list = "<ul>"
        for i in var.db.items("url_ban"):
            ban_list += "<li>" + i[0] + "</li>"
        ban_list += "</ul>"
        bot.send_msg(tr("user_ban_list", list=ban_list), text)


def cmd_user_unban(bot, user, text, command, parameter):
    global log

    if parameter and var.db.has_option("user_ban", parameter):
        var.db.remove_option("user_ban", parameter)
        bot.send_msg(tr("user_unban_success", user=parameter), text)


def cmd_url_ban(bot, user, text, command, parameter):
    global log

    url = util.get_url_from_input(parameter)
    if url:
        _id = item_id_generators['url'](url=url)
        var.cache.free_and_delete(_id)
        var.playlist.remove_by_id(_id)
    else:
        if var.playlist.current_item() and var.playlist.current_item().type == 'url':
            item = var.playlist.current_item().item()
            url = item.url
            var.cache.free_and_delete(item.id)
            var.playlist.remove_by_id(item.id)
        else:
            bot.send_msg(tr('bad_parameter', command=command), text)
            return

    # Remove from the whitelist first
    if var.db.has_option('url_whitelist', url):
        var.db.remove_option("url_whitelist", url)
        bot.send_msg(tr("url_unwhitelist_success", url=url), text)

    if not var.db.has_option('url_ban', url):
        var.db.set("url_ban", url, None)
    bot.send_msg(tr("url_ban_success", url=url), text)


def cmd_url_ban_list(bot, user, text, command, parameter):
    ban_list = "<ul>"
    for i in var.db.items("url_ban"):
        ban_list += "<li>" + i[0] + "</li>"
    ban_list += "</ul>"

    bot.send_msg(tr("url_ban_list", list=ban_list), text)


def cmd_url_unban(bot, user, text, command, parameter):
    url = util.get_url_from_input(parameter)
    if url:
        var.db.remove_option("url_ban", url)
        bot.send_msg(tr("url_unban_success", url=url), text)
    else:
        bot.send_msg(tr('bad_parameter', command=command), text)


def cmd_url_whitelist(bot, user, text, command, parameter):
    url = util.get_url_from_input(parameter)
    if url:
        # Unban first
        if var.db.has_option('url_ban', url):
            var.db.remove_option("url_ban", url)
            bot.send_msg(tr("url_unban_success"), text)

        # Then add to whitelist
        if not var.db.has_option('url_whitelist', url):
            var.db.set("url_whitelist", url, None)
        bot.send_msg(tr("url_whitelist_success", url=url), text)
    else:
        bot.send_msg(tr('bad_parameter', command=command), text)


def cmd_url_whitelist_list(bot, user, text, command, parameter):
    ban_list = "<ul>"
    for i in var.db.items("url_whitelist"):
        ban_list += "<li>" + i[0] + "</li>"
    ban_list += "</ul>"

    bot.send_msg(tr("url_whitelist_list", list=ban_list), text)


def cmd_url_unwhitelist(bot, user, text, command, parameter):
    url = util.get_url_from_input(parameter)
    if url:
        var.db.remove_option("url_whitelist", url)
        bot.send_msg(tr("url_unwhitelist_success"), text)
    else:
        bot.send_msg(tr('bad_parameter', command=command), text)


def cmd_play(bot, user, text, command, parameter):
    global log

    params = parameter.split()
    index = -1
    start_at = 0
    if len(params) > 0:
        if params[0].isdigit() and 1 <= int(params[0]) <= len(var.playlist):
            index = int(params[0])
        else:
            bot.send_msg(tr('invalid_index', index=parameter), text)
            return

        if len(params) > 1:
            try:
                start_at = util.parse_time(params[1])
            except ValueError:
                bot.send_msg(tr('bad_parameter', command=command), text)
                return

    if len(var.playlist) > 0:
        if index != -1:
            bot.play(int(index) - 1, start_at)

        elif bot.is_pause:
            bot.resume()
        else:
            bot.send_msg(var.playlist.current_item().format_current_playing(), text)
    else:
        bot.is_pause = False
        bot.send_msg(tr('queue_empty'), text)


def cmd_pause(bot, user, text, command, parameter):
    global log

    bot.pause()
    bot.send_channel_msg(tr('paused'))


def cmd_play_file(bot, user, text, command, parameter, do_not_refresh_cache=False):
    global log, song_shortlist

    # assume parameter is a path
    music_wrappers = get_cached_wrappers_from_dicts(var.music_db.query_music(Condition().and_equal('path', parameter)), user)
    if music_wrappers:
        var.playlist.append(music_wrappers[0])
        log.info("cmd: add to playlist: " + music_wrappers[0].format_debug_string())
        send_item_added_message(bot, music_wrappers[0], len(var.playlist) - 1, text)
        return

    # assume parameter is a folder
    music_wrappers = get_cached_wrappers_from_dicts(var.music_db.query_music(Condition()
                                                                             .and_equal('type', 'file')
                                                                             .and_like('path', parameter + '%')), user)
    if music_wrappers:
        msgs = [tr('multiple_file_added')]

        for music_wrapper in music_wrappers:
            log.info("cmd: add to playlist: " + music_wrapper.format_debug_string())
            msgs.append("<b>{:s}</b> ({:s})".format(music_wrapper.item().title, music_wrapper.item().path))

        var.playlist.extend(music_wrappers)

        send_multi_lines_in_channel(bot, msgs)
        return

    # try to do a partial match
    matches = var.music_db.query_music(Condition()
                                       .and_equal('type', 'file')
                                       .and_like('path', '%' + parameter + '%', case_sensitive=False))
    if len(matches) == 1:
        music_wrapper = get_cached_wrapper_from_dict(matches[0], user)
        print("wrapper")
        print(type(music_wrapper))
        print(music_wrapper)
        var.playlist.append(music_wrapper)
        log.info("cmd: add to playlist: " + music_wrapper.format_debug_string())
        send_item_added_message(bot, music_wrapper, len(var.playlist) - 1, text)
        return
    elif len(matches) > 1:
        song_shortlist = matches
        msgs = [tr('multiple_matches')]
        for index, match in enumerate(matches):
            msgs.append("<b>{:d}</b> - <b>{:s}</b> ({:s})".format(
                index + 1, match['title'], match['path']))
        msgs.append(tr("shortlist_instruction"))
        send_multi_lines(bot, msgs, text)
        return

    if do_not_refresh_cache:
        bot.send_msg(tr("no_file"), text)
    else:
        var.cache.build_dir_cache()
        cmd_play_file(bot, user, text, command, parameter, do_not_refresh_cache=True)


def cmd_play_file_match(bot, user, text, command, parameter, do_not_refresh_cache=False):
    global log

    if parameter:
        file_dicts = var.music_db.query_music(Condition().and_equal('type', 'file'))
        msgs = [tr('multiple_file_added') + "<ul>"]
        try:
            count = 0
            music_wrappers = []
            for file_dict in file_dicts:
                file = file_dict['title']
                match = re.search(parameter, file)
                if match and match[0]:
                    count += 1
                    music_wrapper = get_cached_wrapper(dict_to_item(file_dict), user)
                    music_wrappers.append(music_wrapper)
                    log.info("cmd: add to playlist: " + music_wrapper.format_debug_string())
                    msgs.append("<li><b>{}</b> ({})</li>".format(music_wrapper.item().title,
                                                                 file[:match.span()[0]]
                                                                 + "<b style='color:pink'>"
                                                                 + file[match.span()[0]: match.span()[1]]
                                                                 + "</b>"
                                                                 + file[match.span()[1]:]
                                                                 ))

            if count != 0:
                msgs.append("</ul>")
                var.playlist.extend(music_wrappers)
                send_multi_lines_in_channel(bot, msgs, "")
            else:
                if do_not_refresh_cache:
                    bot.send_msg(tr("no_file"), text)
                else:
                    var.cache.build_dir_cache()
                    cmd_play_file_match(bot, user, text, command, parameter, do_not_refresh_cache=True)

        except re.error as e:
            msg = tr('wrong_pattern', error=str(e))
            bot.send_msg(msg, text)
    else:
        bot.send_msg(tr('bad_parameter', command=command), text)


def cmd_play_url(bot, user, text, command, parameter):
    global log

    url = util.get_url_from_input(parameter)
    if url:
        music_wrapper = get_cached_wrapper_from_scrap(type='url', url=url, user=user)
        var.playlist.append(music_wrapper)

        log.info("cmd: add to playlist: " + music_wrapper.format_debug_string())
        send_item_added_message(bot, music_wrapper, len(var.playlist) - 1, text)

        if len(var.playlist) == 2:
            # If I am the second item on the playlist. (I am the next one!)
            bot.async_download_next()
    else:
        bot.send_msg(tr('bad_parameter', command=command), text)


def cmd_play_playlist(bot, user, text, command, parameter):
    global log

    offset = 0  # if you want to start the playlist at a specific index
    try:
        offset = int(parameter.split(" ")[-1])
    except ValueError:
        pass

    url = util.get_url_from_input(parameter)
    log.debug(f"cmd: fetching media info from playlist url {url}")
    items = get_playlist_info(url=url, start_index=offset, user=user)
    if len(items) > 0:
        items = var.playlist.extend(list(map(lambda item: get_cached_wrapper_from_scrap(**item), items)))
        for music in items:
            log.info("cmd: add to playlist: " + music.format_debug_string())
    else:
        bot.send_msg(tr("playlist_fetching_failed"), text)


def cmd_play_radio(bot, user, text, command, parameter):
    global log

    if not parameter:
        all_radio = var.config.items('radio')
        msg = tr('preconfigurated_radio')
        for i in all_radio:
            comment = ""
            if len(i[1].split(maxsplit=1)) == 2:
                comment = " - " + i[1].split(maxsplit=1)[1]
            msg += "<br />" + i[0] + comment
        bot.send_msg(msg, text)
    else:
        if var.config.has_option('radio', parameter):
            parameter = var.config.get('radio', parameter)
            parameter = parameter.split()[0]
        url = util.get_url_from_input(parameter)
        if url:
            music_wrapper = get_cached_wrapper_from_scrap(type='radio', url=url, user=user)

            var.playlist.append(music_wrapper)
            log.info("cmd: add to playlist: " + music_wrapper.format_debug_string())
            send_item_added_message(bot, music_wrapper, len(var.playlist) - 1, text)
        else:
            bot.send_msg(tr('bad_url'), text)


def cmd_rb_query(bot, user, text, command, parameter):
    global log

    log.info('cmd: Querying radio stations')
    if not parameter:
        log.debug('rbquery without parameter')
        msg = tr('rb_query_empty')
        bot.send_msg(msg, text)
    else:
        log.debug('cmd: Found query parameter: ' + parameter)
        rb = RadioBrowser()
        rb_stations = rb.search(name=parameter, name_exact=False)
        msg = tr('rb_query_result')
        msg += '\n<table><tr><th>!rbplay ID</th><th>Station Name</th><th>Genre</th><th>Codec/Bitrate</th><th>Country</th></tr>'
        if not rb_stations:
            log.debug(f"cmd: No matches found for rbquery {parameter}")
            bot.send_msg(f"Radio-Browser found no matches for {parameter}", text)
        else:
            for s in rb_stations:
                station_id = s['stationuuid']
                station_name = s['name']
                country = s['countrycode']
                codec = s['codec']
                bitrate = s['bitrate']
                genre = s['tags']
                msg += f"<tr><td>{station_id}</td><td>{station_name}</td><td>{genre}</td><td>{codec}/{bitrate}</td><td>{country}</td></tr>"
            msg += '</table>'
            # Full message as html table
            if len(msg) <= 5000:
                bot.send_msg(msg, text)
            # Shorten message if message too long (stage I)
            else:
                log.debug('Result too long stage I')
                msg = tr('rb_query_result') + ' (shortened L1)'
                msg += '\n<table><tr><th>!rbplay ID</th><th>Station Name</th></tr>'
                for s in rb_stations:
                    station_id = s['stationuuid']
                    station_name = s['name']
                    msg += f'<tr><td>{station_id}</td><td>{station_name}</td>'
                msg += '</table>'
                if len(msg) <= 5000:
                    bot.send_msg(msg, text)
                # Shorten message if message too long (stage II)
                else:
                    log.debug('Result too long stage II')
                    msg = tr('rb_query_result') + ' (shortened L2)'
                    msg += '!rbplay ID - Station Name'
                    for s in rb_stations:
                        station_id = s['stationuuid']
                        station_name = s['name'][:12]
                        msg += f'{station_id} - {station_name}'
                    if len(msg) <= 5000:
                        bot.send_msg(msg, text)
                    # Message still too long
                    else:
                        bot.send_msg('Query result too long to post (> 5000 characters), please try another query.', text)


def cmd_rb_play(bot, user, text, command, parameter):
    global log

    log.debug('cmd: Play a station by ID')
    if not parameter:
        log.debug('rbplay without parameter')
        msg = tr('rb_play_empty')
        bot.send_msg(msg, text)
    else:
        log.debug('cmd: Retreiving url for station ID ' + parameter)
        rb = RadioBrowser()
        rstation = rb.station_by_uuid(parameter)
        stationname = rstation[0]['name']
        country = rstation[0]['countrycode']
        codec = rstation[0]['codec']
        bitrate = rstation[0]['bitrate']
        genre = rstation[0]['tags']
        homepage = rstation[0]['homepage']
        url = rstation[0]['url']
        msg = 'Radio station added to playlist:'

        msg += '<table><tr><th>ID</th><th>Station Name</th><th>Genre</th><th>Codec/Bitrate</th><th>Country</th><th>Homepage</th></tr>' + \
               f"<tr><td>{parameter}</td><td>{stationname}</td><td>{genre}</td><td>{codec}/{bitrate}</td><td>{country}</td><td>{homepage}</td></tr></table>"
        log.debug(f'cmd: Added station to playlist {stationname}')
        bot.send_msg(msg, text)
        if url != "-1":
            log.info('cmd: Found url: ' + url)
            music_wrapper = get_cached_wrapper_from_scrap(type='radio', url=url, name=stationname, user=user)
            var.playlist.append(music_wrapper)
            log.info("cmd: add to playlist: " + music_wrapper.format_debug_string())
            bot.async_download_next()
        else:
            log.info('cmd: No playable url found.')
            msg += "No playable url found for this station, please try another station."
            bot.send_msg(msg, text)


yt_last_result = []
yt_last_page = 0  # TODO: if we keep adding global variables, we need to consider sealing all commands up into classes.


def cmd_yt_search(bot, user, text, command, parameter):
    global log, yt_last_result, yt_last_page, song_shortlist
    item_per_page = 5

    if parameter:
        # if next page
        if parameter.startswith("-n"):
            yt_last_page += 1
            if len(yt_last_result) > yt_last_page * item_per_page:
                song_shortlist = [{'type': 'url',
                                   'url': "https://www.youtube.com/watch?v=" + result[0],
                                   'title': result[1]
                                   } for result in yt_last_result[yt_last_page * item_per_page: item_per_page]]
                msg = _yt_format_result(yt_last_result, yt_last_page * item_per_page, item_per_page)
                bot.send_msg(tr('yt_result', result_table=msg), text)
            else:
                bot.send_msg(tr('yt_no_more'), text)

        # if query
        else:
            results = util.youtube_search(parameter)
            if results:
                yt_last_result = results
                yt_last_page = 0
                song_shortlist = [{'type': 'url', 'url': "https://www.youtube.com/watch?v=" + result[0]}
                                  for result in results[0: item_per_page]]
                msg = _yt_format_result(results, 0, item_per_page)
                bot.send_msg(tr('yt_result', result_table=msg), text)
            else:
                bot.send_msg(tr('yt_query_error'), text)
    else:
        bot.send_msg(tr('bad_parameter', command=command), text)


def _yt_format_result(results, start, count):
    msg = '<table><tr><th width="10%">Index</th><th>Title</th><th width="20%">Uploader</th></tr>'
    for index, item in enumerate(results[start:start + count]):
        msg += '<tr><td>{index:d}</td><td>{title}</td><td>{uploader}</td></tr>'.format(
            index=index + 1, title=item[1], uploader=item[2])
    msg += '</table>'

    return msg

def _format_chaininfo(chainjson):
    msg = '<table><tr><th width="10%">Bitcoin Chaininfo</th><th></th></tr>'
    for i in chainjson.keys():
        msg += f'<tr><td><b>{i}</b></td><td>{chainjson[i]}</td></tr>'
    msg += '</table>'

    return msg


def _format_chatlogs(inputList):
    msg = '<table><tr><th width="10%">#</th><th>Recent Conversations</th><th>Last message</th></tr>'
    for i in inputList:
        with open(i[1]) as f:
            data = json.load(f)
            last_message = data[-1]['content']
        msg += f'<tr><td><b>{i[0]}</b></td><td>{os.path.basename(i[1])}</td><td>{last_message}</td></tr>'
    msg += '</table>'
    return msg

def cmd_yt_play(bot, user, text, command, parameter):
    global log, yt_last_result, yt_last_page

    if parameter:
        results = util.youtube_search(parameter)
        if results:
            yt_last_result = results
            yt_last_page = 0
            url = "https://www.youtube.com/watch?v=" + yt_last_result[0][0]
            cmd_play_url(bot, user, text, command, url)
        else:
            bot.send_msg(tr('yt_query_error'), text)
    else:
        bot.send_msg(tr('bad_parameter', command=command), text)


def cmd_help(bot, user, text, command, parameter):
    global log
    bot.send_msg(tr('help'), text)
    if bot.is_admin(user):
        bot.send_msg(tr('admin_help'), text)


def cmd_stop(bot, user, text, command, parameter):
    global log

    if var.config.getboolean("bot", "clear_when_stop_in_oneshot", fallback=False) \
            and var.playlist.mode == 'one-shot':
        cmd_clear(bot, user, text, command, parameter)
    else:
        bot.stop()
    bot.send_msg(tr('stopped'), text)


def cmd_clear(bot, user, text, command, parameter):
    global log

    bot.clear()
    bot.send_msg(tr('cleared'), text)


def cmd_kill(bot, user, text, command, parameter):
    global log

    bot.pause()
    bot.exit = True


def cmd_update(bot, user, text, command, parameter):
    global log

    if bot.is_admin(user):
        bot.mumble.users[text.actor].send_text_message(
            tr('start_updating'))
        msg = util.update(bot.version)
        bot.mumble.users[text.actor].send_text_message(msg)
    else:
        bot.mumble.users[text.actor].send_text_message(
            tr('not_admin'))


def cmd_stop_and_getout(bot, user, text, command, parameter):
    global log

    bot.stop()
    if var.playlist.mode == "one-shot":
        var.playlist.clear()

    bot.join_channel()


def cmd_volume(bot, user, text, command, parameter):
    global log

    # The volume is a percentage
    if parameter and parameter.isdigit() and 0 <= int(parameter) <= 100:
        bot.volume_helper.set_volume(float(parameter) / 100.0)
        bot.send_msg(tr('change_volume', volume=parameter, user=bot.mumble.users[text.actor]['name']), text)
        var.db.set('bot', 'volume', str(float(parameter) / 100.0))
        log.info(f'cmd: volume set to {float(parameter) / 100.0}')
    else:
        bot.send_msg(tr('current_volume', volume=int(bot.volume_helper.plain_volume_set * 100)), text)


def cmd_ducking(bot, user, text, command, parameter):
    global log

    if parameter == "" or parameter == "on":
        bot.is_ducking = True
        var.db.set('bot', 'ducking', True)
        bot.mumble.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_SOUNDRECEIVED, bot.ducking_sound_received)
        bot.mumble.set_receive_sound(True)
        log.info('cmd: ducking is on')
        msg = "Ducking on."
        bot.send_msg(msg, text)
    elif parameter == "off":
        bot.is_ducking = False
        bot.mumble.set_receive_sound(False)
        var.db.set('bot', 'ducking', False)
        msg = "Ducking off."
        log.info('cmd: ducking is off')
        bot.send_msg(msg, text)


def cmd_ducking_threshold(bot, user, text, command, parameter):
    global log

    if parameter and parameter.isdigit():
        bot.ducking_threshold = int(parameter)
        var.db.set('bot', 'ducking_threshold', str(bot.ducking_threshold))
        msg = f"Ducking threshold set to {bot.ducking_threshold}."
        bot.send_msg(msg, text)
    else:
        msg = f"Current ducking threshold is {bot.ducking_threshold}."
        bot.send_msg(msg, text)


def cmd_ducking_volume(bot, user, text, command, parameter):
    global log

    # The volume is a percentage
    if parameter and parameter.isdigit() and 0 <= int(parameter) <= 100:
        bot.volume_helper.set_ducking_volume(float(parameter) / 100.0)
        bot.send_msg(tr('change_ducking_volume', volume=parameter, user=bot.mumble.users[text.actor]['name']), text)
        var.db.set('bot', 'ducking_volume', float(parameter) / 100.0)
        log.info(f'cmd: volume on ducking set to {parameter}')
    else:
        bot.send_msg(tr('current_ducking_volume', volume=int(bot.volume_helper.plain_ducking_volume_set * 100)), text)


def cmd_current_music(bot, user, text, command, parameter):
    global log

    if len(var.playlist) > 0:
        bot.send_msg(var.playlist.current_item().format_current_playing(), text)
    else:
        bot.send_msg(tr('not_playing'), text)


def cmd_skip(bot, user, text, command, parameter):
    global log

    if not bot.is_pause:
        bot.interrupt()
    else:
        var.playlist.next()
        bot.wait_for_ready = True

    if len(var.playlist) == 0:
        bot.send_msg(tr('queue_empty'), text)


def cmd_last(bot, user, text, command, parameter):
    global log

    if len(var.playlist) > 0:
        bot.interrupt()
        var.playlist.point_to(len(var.playlist) - 1 - 1)
    else:
        bot.send_msg(tr('queue_empty'), text)


def cmd_remove(bot, user, text, command, parameter):
    global log

    # Allow to remove specific music into the queue with a number
    if parameter and parameter.isdigit() and 0 < int(parameter) <= len(var.playlist):

        index = int(parameter) - 1

        if index == var.playlist.current_index:
            removed = var.playlist[index]
            bot.send_msg(tr('removing_item',
                                      item=removed.format_title()), text)
            log.info("cmd: delete from playlist: " + removed.format_debug_string())

            var.playlist.remove(index)

            if index < len(var.playlist):
                if not bot.is_pause:
                    bot.interrupt()
                    var.playlist.current_index -= 1
                    # then the bot will move to next item

            else:  # if item deleted is the last item of the queue
                var.playlist.current_index -= 1
                if not bot.is_pause:
                    bot.interrupt()
        else:
            var.playlist.remove(index)

    else:
        bot.send_msg(tr('bad_parameter', command=command), text)


def cmd_list_file(bot, user, text, command, parameter):
    global song_shortlist

    files = var.music_db.query_music(Condition()
                                     .and_equal('type', 'file')
                                     .order_by('path'))

    song_shortlist = files

    msgs = [tr("multiple_file_found") + "<ul>"]
    try:
        count = 0
        for index, file in enumerate(files):
            if parameter:
                match = re.search(parameter, file['path'])
                if not match:
                    continue

            count += 1
            if count > ITEMS_PER_PAGE:
                break
            msgs.append("<li><b>{:d}</b> - <b>{:s}</b> ({:s})</li>".format(index + 1, file['title'], file['path']))

        if count != 0:
            msgs.append("</ul>")
            if count > ITEMS_PER_PAGE:
                msgs.append(tr("records_omitted"))
            msgs.append(tr("shortlist_instruction"))
            send_multi_lines(bot, msgs, text, "")
        else:
            bot.send_msg(tr("no_file"), text)

    except re.error as e:
        msg = tr('wrong_pattern', error=str(e))
        bot.send_msg(msg, text)


def cmd_queue(bot, user, text, command, parameter):
    global log

    if len(var.playlist) == 0:
        msg = tr('queue_empty')
        bot.send_msg(msg, text)
    else:
        msgs = [tr('queue_contents')]
        for i, music in enumerate(var.playlist):
            tags = ''
            if len(music.item().tags) > 0:
                tags = "<sup>{}</sup>".format(", ".join(music.item().tags))
            if i == var.playlist.current_index:
                newline = "<b style='color:orange'>{} ({}) {} </b> {}".format(i + 1, music.display_type(),
                                                                              music.format_title(), tags)
            else:
                newline = '<b>{}</b> ({}) {} {}'.format(i + 1, music.display_type(),
                                                        music.format_title(), tags)

            msgs.append(newline)

        send_multi_lines(bot, msgs, text)


def cmd_random(bot, user, text, command, parameter):
    global log

    bot.interrupt()
    var.playlist.randomize()


def cmd_repeat(bot, user, text, command, parameter):
    global log

    repeat = 1
    if parameter and parameter.isdigit():
        repeat = int(parameter)

    music = var.playlist.current_item()
    if music:
        for _ in range(repeat):
            var.playlist.insert(
                var.playlist.current_index + 1,
                music
            )
            log.info("bot: add to playlist: " + music.format_debug_string())

        bot.send_channel_msg(tr("repeat", song=music.format_song_string(), n=str(repeat)))
    else:
        bot.send_msg(tr("queue_empty"), text)


def cmd_mode(bot, user, text, command, parameter):
    global log

    if not parameter:
        bot.send_msg(tr("current_mode", mode=var.playlist.mode), text)
        return
    if parameter not in ["one-shot", "repeat", "random", "autoplay"]:
        bot.send_msg(tr('unknown_mode', mode=parameter), text)
    else:
        var.db.set('playlist', 'playback_mode', parameter)
        var.playlist = media.playlist.get_playlist(parameter, var.playlist)
        log.info(f"command: playback mode changed to {parameter}.")
        bot.send_msg(tr("change_mode", mode=var.playlist.mode,
                                  user=bot.mumble.users[text.actor]['name']), text)
        if parameter == "random":
            bot.interrupt()


def cmd_play_tags(bot, user, text, command, parameter):
    if not parameter:
        bot.send_msg(tr('bad_parameter', command=command), text)
        return

    msgs = [tr('multiple_file_added') + "<ul>"]
    count = 0

    tags = parameter.split(",")
    tags = list(map(lambda t: t.strip(), tags))
    music_wrappers = get_cached_wrappers_by_tags(tags, user)
    for music_wrapper in music_wrappers:
        count += 1
        log.info("cmd: add to playlist: " + music_wrapper.format_debug_string())
        msgs.append("<li><b>{}</b> (<i>{}</i>)</li>".format(music_wrapper.item().title, ", ".join(music_wrapper.item().tags)))

    if count != 0:
        msgs.append("</ul>")
        var.playlist.extend(music_wrappers)
        send_multi_lines_in_channel(bot, msgs, "")
    else:
        bot.send_msg(tr("no_file"), text)


def cmd_add_tag(bot, user, text, command, parameter):
    global log

    params = parameter.split(" ", 1)
    index = 0
    tags = []

    if len(params) == 2 and params[0].isdigit():
        index = params[0]
        tags = list(map(lambda t: t.strip(), params[1].split(",")))
    elif len(params) == 2 and params[0] == "*":
        index = "*"
        tags = list(map(lambda t: t.strip(), params[1].split(",")))
    else:
        index = str(var.playlist.current_index + 1)
        tags = list(map(lambda t: t.strip(), parameter.split(",")))

    if tags[0]:
        if index.isdigit() and 1 <= int(index) <= len(var.playlist):
            var.playlist[int(index) - 1].add_tags(tags)
            log.info(f"cmd: add tags {', '.join(tags)} to song {var.playlist[int(index) - 1].format_debug_string()}")
            bot.send_msg(tr("added_tags",
                                      tags=", ".join(tags),
                                      song=var.playlist[int(index) - 1].format_title()), text)
            return

        elif index == "*":
            for item in var.playlist:
                item.add_tags(tags)
                log.info(f"cmd: add tags {', '.join(tags)} to song {item.format_debug_string()}")
            bot.send_msg(tr("added_tags_to_all", tags=", ".join(tags)), text)
            return

    bot.send_msg(tr('bad_parameter', command=command), text)


def cmd_remove_tag(bot, user, text, command, parameter):
    global log

    params = parameter.split(" ", 1)
    index = 0
    tags = []

    if len(params) == 2 and params[0].isdigit():
        index = params[0]
        tags = list(map(lambda t: t.strip(), params[1].split(",")))
    elif len(params) == 2 and params[0] == "*":
        index = "*"
        tags = list(map(lambda t: t.strip(), params[1].split(",")))
    else:
        index = str(var.playlist.current_index + 1)
        tags = list(map(lambda t: t.strip(), parameter.split(",")))

    if tags[0]:
        if index.isdigit() and 1 <= int(index) <= len(var.playlist):
            if tags[0] != "*":
                var.playlist[int(index) - 1].remove_tags(tags)
                log.info(f"cmd: remove tags {', '.join(tags)} from song {var.playlist[int(index) - 1].format_debug_string()}")
                bot.send_msg(tr("removed_tags",
                                          tags=", ".join(tags),
                                          song=var.playlist[int(index) - 1].format_title()), text)
                return
            else:
                var.playlist[int(index) - 1].clear_tags()
                log.info(f"cmd: clear tags from song {var.playlist[int(index) - 1].format_debug_string()}")
                bot.send_msg(tr("cleared_tags",
                                          song=var.playlist[int(index) - 1].format_title()), text)
                return

        elif index == "*":
            if tags[0] != "*":
                for item in var.playlist:
                    item.remove_tags(tags)
                    log.info(f"cmd: remove tags {', '.join(tags)} from song {item.format_debug_string()}")
                bot.send_msg(tr("removed_tags_from_all", tags=", ".join(tags)), text)
                return
            else:
                for item in var.playlist:
                    item.clear_tags()
                    log.info(f"cmd: clear tags from song {item.format_debug_string()}")
                bot.send_msg(tr("cleared_tags_from_all"), text)
                return

    bot.send_msg(tr('bad_parameter', command=command), text)


def cmd_find_tagged(bot, user, text, command, parameter):
    global song_shortlist

    if not parameter:
        bot.send_msg(tr('bad_parameter', command=command), text)
        return

    msgs = [tr('multiple_file_found') + "<ul>"]
    count = 0

    tags = parameter.split(",")
    tags = list(map(lambda t: t.strip(), tags))

    music_dicts = var.music_db.query_music_by_tags(tags)
    song_shortlist = music_dicts

    for i, music_dict in enumerate(music_dicts):
        item = dict_to_item(music_dict)
        count += 1
        if count > ITEMS_PER_PAGE:
            break
        msgs.append("<li><b>{:d}</b> - <b>{}</b> (<i>{}</i>)</li>".format(i + 1, item.title, ", ".join(item.tags)))

    if count != 0:
        msgs.append("</ul>")
        if count > ITEMS_PER_PAGE:
            msgs.append(tr("records_omitted"))
        msgs.append(tr("shortlist_instruction"))
        send_multi_lines(bot, msgs, text, "")
    else:
        bot.send_msg(tr("no_file"), text)


def cmd_search_library(bot, user, text, command, parameter):
    global song_shortlist
    if not parameter:
        bot.send_msg(tr('bad_parameter', command=command), text)
        return

    msgs = [tr('multiple_file_found') + "<ul>"]
    count = 0

    _keywords = parameter.split(" ")
    keywords = []
    for kw in _keywords:
        if kw:
            keywords.append(kw)

    music_dicts = var.music_db.query_music_by_keywords(keywords)
    if music_dicts:
        items = dicts_to_items(music_dicts)
        song_shortlist = music_dicts

        if len(items) == 1:
            music_wrapper = get_cached_wrapper(items[0], user)
            var.playlist.append(music_wrapper)
            log.info("cmd: add to playlist: " + music_wrapper.format_debug_string())
            send_item_added_message(bot, music_wrapper, len(var.playlist) - 1, text)
        else:
            for item in items:
                count += 1
                if count > ITEMS_PER_PAGE:
                    break
                if len(item.tags) > 0:
                    msgs.append("<li><b>{:d}</b> - [{}] <b>{}</b> (<i>{}</i>)</li>".format(count, item.display_type(), item.title, ", ".join(item.tags)))
                else:
                    msgs.append("<li><b>{:d}</b> - [{}] <b>{}</b> </li>".format(count, item.display_type(), item.title, ", ".join(item.tags)))

            if count != 0:
                msgs.append("</ul>")
                if count > ITEMS_PER_PAGE:
                    msgs.append(tr("records_omitted"))
                msgs.append(tr("shortlist_instruction"))
                send_multi_lines(bot, msgs, text, "")
            else:
                bot.send_msg(tr("no_file"), text)
    else:
        bot.send_msg(tr("no_file"), text)


def cmd_shortlist(bot, user, text, command, parameter):
    global song_shortlist, log
    if parameter.strip() == "*":
        msgs = [tr('multiple_file_added') + "<ul>"]
        music_wrappers = []
        for kwargs in song_shortlist:
            kwargs['user'] = user
            music_wrapper = get_cached_wrapper_from_scrap(**kwargs)
            music_wrappers.append(music_wrapper)
            log.info("cmd: add to playlist: " + music_wrapper.format_debug_string())
            msgs.append("<li>[{}] <b>{}</b></li>".format(music_wrapper.item().type, music_wrapper.item().title))

        var.playlist.extend(music_wrappers)

        msgs.append("</ul>")
        send_multi_lines_in_channel(bot, msgs, "")
        return

    try:
        indexes = [int(i) for i in parameter.split(" ")]
    except ValueError:
        bot.send_msg(tr('bad_parameter', command=command), text)
        return

    if len(indexes) > 1:
        msgs = [tr('multiple_file_added') + "<ul>"]
        music_wrappers = []
        for index in indexes:
            if 1 <= index <= len(song_shortlist):
                kwargs = song_shortlist[index - 1]
                kwargs['user'] = user
                music_wrapper = get_cached_wrapper_from_scrap(**kwargs)
                music_wrappers.append(music_wrapper)
                log.info("cmd: add to playlist: " + music_wrapper.format_debug_string())
                msgs.append("<li>[{}] <b>{}</b></li>".format(music_wrapper.item().type, music_wrapper.item().title))
            else:
                var.playlist.extend(music_wrappers)
                bot.send_msg(tr('bad_parameter', command=command), text)
                return

        var.playlist.extend(music_wrappers)

        msgs.append("</ul>")
        send_multi_lines_in_channel(bot, msgs, "")
        return
    elif len(indexes) == 1:
        index = indexes[0]
        if 1 <= index <= len(song_shortlist):
            kwargs = song_shortlist[index - 1]
            kwargs['user'] = user
            music_wrapper = get_cached_wrapper_from_scrap(**kwargs)
            var.playlist.append(music_wrapper)
            log.info("cmd: add to playlist: " + music_wrapper.format_debug_string())
            send_item_added_message(bot, music_wrapper, len(var.playlist) - 1, text)
            return

    bot.send_msg(tr('bad_parameter', command=command), text)


def cmd_delete_from_library(bot, user, text, command, parameter):
    global song_shortlist, log
    try:
        indexes = [int(i) for i in parameter.split(" ")]
    except ValueError:
        bot.send_msg(tr('bad_parameter', command=command), text)
        return

    if len(indexes) > 1:
        msgs = [tr('multiple_file_added') + "<ul>"]
        count = 0
        for index in indexes:
            if 1 <= index <= len(song_shortlist):
                music_dict = song_shortlist[index - 1]
                if 'id' in music_dict:
                    music_wrapper = get_cached_wrapper_by_id(music_dict['id'], user)
                    log.info("cmd: remove from library: " + music_wrapper.format_debug_string())
                    msgs.append("<li>[{}] <b>{}</b></li>".format(music_wrapper.item().type, music_wrapper.item().title))
                    var.playlist.remove_by_id(music_dict['id'])
                    var.cache.free_and_delete(music_dict['id'])
                    count += 1
            else:
                bot.send_msg(tr('bad_parameter', command=command), text)
                return

        if count == 0:
            bot.send_msg(tr('bad_parameter', command=command), text)
            return

        msgs.append("</ul>")
        send_multi_lines_in_channel(bot, msgs, "")
        return
    elif len(indexes) == 1:
        index = indexes[0]
        if 1 <= index <= len(song_shortlist):
            music_dict = song_shortlist[index - 1]
            if 'id' in music_dict:
                music_wrapper = get_cached_wrapper_by_id(music_dict['id'], user)
                bot.send_msg(tr('file_deleted', item=music_wrapper.format_song_string()), text)
                log.info("cmd: remove from library: " + music_wrapper.format_debug_string())
                var.playlist.remove_by_id(music_dict['id'])
                var.cache.free_and_delete(music_dict['id'])
                return

    bot.send_msg(tr('bad_parameter', command=command), text)


def cmd_drop_database(bot, user, text, command, parameter):
    global log

    if bot.is_admin(user):
        var.db.drop_table()
        var.db = SettingsDatabase(var.settings_db_path)
        var.music_db.drop_table()
        var.music_db = MusicDatabase(var.settings_db_path)
        log.info("command: database dropped.")
        bot.send_msg(tr('database_dropped'), text)
    else:
        bot.mumble.users[text.actor].send_text_message(tr('not_admin'))


def cmd_refresh_cache(bot, user, text, command, parameter):
    global log
    if bot.is_admin(user):
        var.cache.build_dir_cache()
        log.info("command: Local file cache refreshed.")
        bot.send_msg(tr('cache_refreshed'), text)
    else:
        bot.mumble.users[text.actor].send_text_message(tr('not_admin'))


def cmd_web_access(bot, user, text, command, parameter):
    auth_method = var.config.get("webinterface", "auth_method")

    if auth_method == 'token':
        interface.banned_ip = []
        interface.bad_access_count = {}

        user_info = var.db.get("user", user, fallback='{}')
        user_dict = json.loads(user_info)
        if 'token' in user_dict:
            var.db.remove_option("web_token", user_dict['token'])

        token = secrets.token_urlsafe(5)
        user_dict['token'] = token
        user_dict['token_created'] = str(datetime.datetime.now())
        user_dict['last_ip'] = ''
        var.db.set("web_token", token, user)
        var.db.set("user", user, json.dumps(user_dict))

        access_address = var.config.get("webinterface", "access_address") + "/?token=" + token
    else:
        access_address = var.config.get("webinterface", "access_address")

    bot.send_msg(tr('webpage_address', address=access_address), text)


def cmd_user_password(bot, user, text, command, parameter):
    if not parameter:
        bot.send_msg(tr('bad_parameter', command=command), text)
        return

    user_info = var.db.get("user", user, fallback='{}')
    user_dict = json.loads(user_info)
    user_dict['password'], user_dict['salt'] = util.get_salted_password_hash(parameter)

    var.db.set("user", user, json.dumps(user_dict))

    bot.send_msg(tr('user_password_set'), text)


def cmd_web_user_add(bot, user, text, command, parameter):
    if not parameter:
        bot.send_msg(tr('bad_parameter', command=command), text)
        return

    auth_method = var.config.get("webinterface", "auth_method")

    if auth_method == 'password':
        web_users = json.loads(var.db.get("privilege", "web_access", fallback='[]'))
        if parameter not in web_users:
            web_users.append(parameter)
        var.db.set("privilege", "web_access", json.dumps(web_users))
        bot.send_msg(tr('web_user_list', users=", ".join(web_users)), text)
    else:
        bot.send_msg(tr('command_disabled', command=command), text)


def cmd_web_user_remove(bot, user, text, command, parameter):
    if not parameter:
        bot.send_msg(tr('bad_parameter', command=command), text)
        return

    auth_method = var.config.get("webinterface", "auth_method")

    if auth_method == 'password':
        web_users = json.loads(var.db.get("privilege", "web_access", fallback='[]'))
        if parameter in web_users:
            web_users.remove(parameter)
        var.db.set("privilege", "web_access", json.dumps(web_users))
        bot.send_msg(tr('web_user_list', users=", ".join(web_users)), text)
    else:
        bot.send_msg(tr('command_disabled', command=command), text)


def cmd_web_user_list(bot, user, text, command, parameter):
    auth_method = var.config.get("webinterface", "auth_method")

    if auth_method == 'password':
        web_users = json.loads(var.db.get("privilege", "web_access", fallback='[]'))
        bot.send_msg(tr('web_user_list', users=", ".join(web_users)), text)
    else:
        bot.send_msg(tr('command_disabled', command=command), text)


def cmd_version(bot, user, text, command, parameter):
    bot.send_msg(tr('report_version', version=bot.get_version()), text)


# Just for debug use
def cmd_real_time_rms(bot, user, text, command, parameter):
    bot._display_rms = not bot._display_rms


def cmd_loop_state(bot, user, text, command, parameter):
    print(bot._loop_status)


def cmd_item(bot, user, text, command, parameter):
    var.playlist._debug_print()
