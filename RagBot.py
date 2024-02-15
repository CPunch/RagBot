#!python3

import sys
from MidiParser import MidiParser
from VideoRenderer import VideoRenderer

if __name__ == '__main__':
    outFile = "out.mp4"
    if len(sys.argv) < 3:
        print("usage: %s [MIDI] [SOUNDFONT] (out.mp4)" % sys.argv[0])
        exit(1)
    elif len(sys.argv) == 4:
        outFile = sys.argv[3]

    mp = MidiParser(sys.argv[1], sys.argv[2], transpose=0)
    vid = VideoRenderer(mp, 1280, 720, filename=outFile)