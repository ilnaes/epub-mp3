import io
import ebooklib
import re
from ebooklib import epub
from bs4 import BeautifulSoup
import argparse

# from gtts import gTTS
from google.oauth2 import service_account
from google.cloud import texttospeech
from pydub import AudioSegment
from tqdm import tqdm

# max chunks to send each time
MAX_CHAR = 5000

blacklist = [
    "[document]",
    "noscript",
    "header",
    "html",
    "meta",
    "head",
    "input",
    "script",
]


def read(chap):
    output = ""
    soup = BeautifulSoup(chap, "html.parser")
    text = soup.find_all(text=True)

    for item in text:
        if item.parent.name not in blacklist:
            if item.parent.name == "li":
                # pause between items in list
                output += "{}, ".format(item.strip())
            else:
                output += "{} ".format(item.strip())
    return output


def get_text(file):
    book = epub.read_epub(file)

    links = []
    chapters = []

    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        links.append((item.get_name(), item.get_content()))

    for ch in book.toc:
        if type(ch) == tuple:
            print(f"{len(chapters)}: {ch[0].title}")
            chapters.append(ch[0].href)

            for sec in ch[1]:
                print(f"{len(chapters)}: {sec.title}")
                chapters.append(sec.href)
        else:
            print(f"{len(chapters)}: {ch.title}")
            chapters.append(ch.href)

    # get indices of start of chapters according to TOC
    i = 0
    ch_links = []

    for j, href in enumerate(links):
        if href[0] == chapters[i]:
            ch_links.append(j)
            i += 1

            if i == len(chapters):
                break

    sel = int(input("Input chapter: "))

    chapter = []
    if sel == len(chapters) - 1:
        chapter = links[ch_links[sel] :]
    else:
        chapter = links[ch_links[sel] : ch_links[sel + 1]]

    text = ""
    for sec in chapter:
        text += read(sec[1])

    text = text.replace("\n", " ")
    text = " ".join(text.split())

    return text, sel


def get_mp3(text, creds) -> bytes:
    # Instantiates a client
    client = texttospeech.TextToSpeechClient(credentials=creds)

    # Set the text input to be synthesized
    synthesis_input = texttospeech.SynthesisInput(text=text)

    # Build the voice request, select the language code ("en-US") and the ssml
    # voice gender ("neutral")
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )

    # Select the type of audio file you want returned
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    # Perform the text-to-speech request on the text input with the selected
    # voice parameters and audio file type
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    return response.audio_content


def parse_args():
    parser = argparse.ArgumentParser(
        description="Use Google Text-to-Speech to record epub chapters"
    )

    parser.add_argument(
        "-k",
        "--key",
        type=str,
        help="path to google credentials json (if not using environment variable)",
    )

    parser.add_argument("file", type=str, help="path to epub")
    args = parser.parse_args()

    return args.key, args.file


def main():
    creds, file = parse_args()

    if creds is not None:
        creds = service_account.Credentials.from_service_account_file(creds)

    text, sel = get_text(file)

    print(f"Char length: {len(text)}")
    sentences = re.split(r"(?<=\.) ", text)

    output = AudioSegment.empty()
    current = ""

    for s in tqdm(sentences):
        if len(current) + len(s) + 1 > MAX_CHAR:
            output += AudioSegment.from_mp3(io.BytesIO(get_mp3(current, creds)))
            current = ""

        current += " " + s

    if current:
        output += AudioSegment.from_mp3(io.BytesIO(get_mp3(current, creds)))

    output.export(f"ch{sel}.mp3", format="mp3")
    # obj = gTTS(text=text[:2000], lang="en", slow=False)
    # obj.save("chapter" + str(x) + ".mp3")


if __name__ == "__main__":
    main()
