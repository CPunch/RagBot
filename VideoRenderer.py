from moviepy.editor import *
from PIL import Image, ImageDraw
import numpy as np

from MidiParser import MidiParser, Note
from Instruments import Instruments

class VideoRenderer:
    def __init__(self, mp: MidiParser, width: int, height: int, filename: str = "out.mp4") -> None:
        self.mp = mp

        # find highest & lowest note
        self.highest = None
        self.lowest = None
        for n in self.mp.notes:
            if not self.highest or self.highest < n.note:
                self.highest = n.note

            if not self.lowest or self.lowest > n.note:
                self.lowest = n.note

        self.width = width
        self.height = height
        self.offset = self.lowest-1
        self.noteSize = height / ((self.highest - self.lowest)+1)
        self.keyboardWidth = 100
        self.duration = mp.toSeconds(mp.endTick)+2
        self.timePerWidth = 4 # whole screen will scroll by x seconds

        # sort notes by start tick so they're drawn properly
        self.notes: list[Note] = self.mp.notes
        self.notes.sort(key=lambda n: n.start)

        audio = AudioFileClip(mp.tmpSound)
        nAudio = CompositeAudioClip([audio])
        nAudio.duration = self.duration

        # creating animation
        animation = VideoClip(self._makeFrame, duration = self.duration)
        animation.audio = nAudio

        # displaying animation with auto play and looping
        animation.write_videofile(filename=filename, fps=60, threads=16)

    # returns true if the note is currently playing
    def drawNote(self, n: Note, t: float, draw: ImageDraw) -> bool:
        start = self.mp.toSeconds(n.start) - t
        end = self.mp.toSeconds(n.end) - t

        # note won't be rendered
        if end < 0 or start > self.timePerWidth or end == start:
            return

        x = (start / self.timePerWidth) * self.width + self.keyboardWidth
        x2 = (end / self.timePerWidth) * self.width + self.keyboardWidth
        y = self.height - ((n.note - self.offset) * self.noteSize)

        # grab the fill color for note
        isPlaying = False
        colr = None
        if x < self.keyboardWidth: # currently playing
            colr = Instruments[n.instru][1]
            isPlaying = True
        else:
            colr = Instruments[n.instru][0]

        # draw note
        draw.rectangle((x, y, x2, y+self.noteSize), fill=colr)
        return isPlaying

    def _makeFrame(self, t):
        frame = Image.new("RGB", [self.width, self.height], (30, 30, 30))
        draw = ImageDraw.Draw(frame)
        currentNotes = []

        # draw notes
        for n in self.notes:
            if self.drawNote(n, t, draw):
                currentNotes.append(n.note)

        # draw keyboard
        for i in range(self.lowest, self.highest+1):
            y = self.height - ((i - self.offset) * self.noteSize)

            # select key color
            fillColor = (0, 0, 0)
            if i % 12 in [1, 3, 6, 8, 10]: # black key
                if i in currentNotes:
                    fillColor = (25, 25, 25)
                else:
                    fillColor = (50, 50, 50)
            else:
                if i in currentNotes:
                    fillColor = (175, 175, 175)
                else:
                    fillColor = (255, 255, 255)

            draw.rectangle((0, y, self.keyboardWidth, y+self.noteSize), fill=fillColor)

        return np.array(frame)
