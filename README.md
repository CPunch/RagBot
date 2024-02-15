# RagBot

RagBot is a simple python script for turning MIDI and SoundFont files into a synthesia-like video.

https://github.com/CPunch/RagBot/assets/28796526/305c2def-db0f-40ad-9d58-c4264bd9ff9b

## Installation

After cloning the repository, you can install the required packages with pip:

```bash
pip install -r requirements.txt
```
> I recommend doing this in a [virtual environment](https://docs.python.org/3/library/venv.html)

## Usage

To use RagBot, you need a MIDI file and a SoundFont file. Simply pass the paths to these files as arguments to the script:

```bash
python RagBot.py path/to/midi/file.mid path/to/soundfont/file.sf2
```