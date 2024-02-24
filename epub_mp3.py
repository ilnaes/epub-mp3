import argparse
import io
import re

import ebooklib
from bs4 import BeautifulSoup
from ebooklib import epub
from google.cloud import texttospeech
from google.oauth2 import service_account
from pydub import AudioSegment
from tqdm import tqdm

# max chunks to send each time
MAX_CHAR = 4500

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
                output += f"{item.strip()}, "
            elif item.parent.name[0] == "h":
                # full stop after titles
                output += f"{item.strip()}. "
            else:
                output += f"{item.strip()} "
    return output


def get_input(prompt, valid, other=[]):
    while True:
        try:
            x = input(prompt)

            if x in other:
                return x

            if int(x) < valid[0] or int(x) > valid[1]:
                raise ValueError
            return int(x)

        except ValueError:
            print(f"Input valid chapter {valid[0]}-{valid[1]}!")
            pass


def get_text(file):
    book = epub.read_epub(file)

    #%%
    contents = [x.get_content() for x in book.get_items_of_type(ebooklib.ITEM_DOCUMENT)]
    idx = {
        x.file_name: i
        for i, x in enumerate(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
    }

    #%%
    j = 0
    pos = []  # converts toc to pointers to locations in contents
    prev = ""

    def print_ch(items, n):
        nonlocal j
        nonlocal prev

        for x in items:
            if type(x) == tuple or type(x) == list:
                print_ch(x, n + 1)
            else:
                curr = x.href
                i = curr.find("#")
                if i >= 0:
                    # filter out jump link
                    curr = curr[0:i]
                if curr == prev:
                    continue

                print(f"\033[92m{j}:\033[0m " + ("  " * n) + x.title)
                pos.append(idx[curr])
                j += 1
                prev = curr

    print_ch(book.toc, 0)

    #%%
    start = get_input(f"Input start chapter 0-{j-1}: ", (0, j - 1))
    end = get_input(
        f"Input end chapter {start}-{j-1}: (Can press ENTER to select just the one start chapter) ",
        (start, j - 1),
        [""],
    )

    if end == "":
        end = start

    #%%

    chapters = []

    for i in range(pos[start], pos[end + 1]):
        text = read(contents[i])
        text = text.replace("\n", " ")
        text = " ".join(text.split())
        chapters.append(text)

    return "\n".join(chapters), start


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
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="name of the mp3 output (default will be ch##.mp3 where ## is your selection)",
    )
    parser.add_argument(
        "-d",
        "--dry",
        action="store_true",
        help="does a dry run and prints out your chapter as a string list rather than send to Google",
    )

    parser.add_argument("file", type=str, help="path to epub")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.key is not None:
        creds = service_account.Credentials.from_service_account_file(args.key)

    text, sel = get_text(args.file)

    if args.output is None:
        outfile = input(f"Output file (default ch{sel}.mp3): ") or f"ch{sel}.mp3"

        if outfile[-4:] != ".mp3":
            outfile += ".mp3"

    print(f"Char length: {len(text)}")
    sentences = re.split(r"(?<=\.) ", text)

    if args.dry:
        print(sentences)
        quit()

    output = AudioSegment.empty()
    current = ""

    for s in tqdm(sentences):
        if len(current) + len(s) + 1 > MAX_CHAR:
            output += AudioSegment.from_mp3(io.BytesIO(get_mp3(current, creds)))
            current = ""

        current += " " + s

    if current:
        output += AudioSegment.from_mp3(io.BytesIO(get_mp3(current, creds)))

    output.export(outfile, format="mp3")

    # old gTTS
    # obj = gTTS(text=text[:2000], lang="en", slow=False)
    # obj.save("chapter" + str(x) + ".mp3")


if __name__ == "__main__":
    main()
