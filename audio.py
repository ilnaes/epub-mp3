# %%
import io
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from gtts import gTTS
from google.cloud import texttospeech
import re
from pydub import AudioSegment

# %%
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
    for t in text:
        if t.parent.name not in blacklist:
            if t.parent.name == "li":
                output += "{}, ".format(t.strip())
            else:
                output += "{} ".format(t.strip())
    return output


def get_text():
    # %%
    book = epub.read_epub("book.epub")

    links = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        links.append((item.get_name(), item.get_content()))

    # %%
    chapters = []

    for l in book.toc:
        if type(l) == tuple:
            print(f"{len(chapters)}: {l[0].title}")
            chapters.append(l[0].href)

            for sec in l[1]:
                print(f"{len(chapters)}: {sec.title}")
                chapters.append(sec.href)
        else:
            print(f"{len(chapters)}: {l.title}")
            chapters.append(l.href)

    # get indices of start of chapters according to TOC
    i = 0
    ch_links = []

    for j, href in enumerate(links):
        if href[0] == chapters[i]:
            ch_links.append(j)
            i += 1

            if i == len(chapters):
                break

    # %%
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

    return text

    # %%
    # obj = gTTS(text=text[:2000], lang="en", slow=False)
    # obj.save("chapter" + str(x) + ".mp3")


def get_mp3(text, output):
    # Instantiates a client
    client = texttospeech.TextToSpeechClient()

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


def main():
    # text = get_text()
    # sentences = re.split(r"(?<=\.) ", text)

    output = AudioSegment.empty()
    output += AudioSegment.from_mp3(io.BytesIO(get_mp3("hello.", "test.mp3")))
    output += AudioSegment.from_mp3(io.BytesIO(get_mp3("world.", "test.mp3")))

    output.export("test.mp3", format="mp3")


# %%
if __name__ == "__main__":
    main()
