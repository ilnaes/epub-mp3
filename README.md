# Epub Transcript

This short script allows you to create an mp3 of a chapter of an epub using Google's Text to Speech service.  You will need to set up authentication.  See [https://cloud.google.com/text-to-speech/docs/libraries](https://cloud.google.com/text-to-speech/docs/libraries) for information on how to set up.

N.B. As of this writing (8/2021) only the first million characters are free ([https://cloud.google.com/text-to-speech#section-11](https://cloud.google.com/text-to-speech#section-11).  You may have to pay after that.  Keep that in mind!

# Usage:

```sh
python epub_trans.py [-k KEY] file
```

A menu will then pop up allowing you to select a chapter.
