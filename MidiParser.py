from enum import Enum, auto
from miditoolkit.midi import parser as mid_parser
import simpleaudio as sa
import wave
from collections import namedtuple
import numpy as np
import fluidsynth

from Instruments import Instruments

Note = namedtuple('Note', ['note', 'velocity', 'instru', 'start', 'end'])
Pitch = namedtuple('Pitch', ['pitch', 'instru', 'time'])
NoteEvent = namedtuple('NoteEvent', ['note', 'type'])

class Instrument:
    def __init__(self, program, bank) -> None:
        self.program = program
        self.bank = bank
        self.pitchBend = 2

class NoteEventType(Enum):
    PLAY = auto(),
    STOP = auto()

# holds events for when to stop/play notes
class MidiEvent:
    def __init__(self, time: int) -> None:
        self.notes: list[NoteEvent] = []
        self.pitches: list[Pitch] = []
        self.time = time

    def addNote(self, note, type: NoteEventType):
        self.notes.append(NoteEvent(note, type))

    def addPitch(self, pitch):
        self.pitches.append(pitch)

class MidiParser:
    def __init__(self, midiFile: str, soundfont: str, sampleRate: int = 44100, transpose: int = 0, tmpSound: str = "tmp.wav") -> None:
        self.ps = mid_parser.MidiFile(midiFile)
        self.fl = fluidsynth.Synth()
        self.volume = 1

        self.sound = []
        self.tickTimeMap = self.ps.get_tick_to_time_mapping()
        self.transpose = transpose
        self.tmpSound = tmpSound
        self.ticksPerQuarter = self.ps.ticks_per_beat
        self.sampleRate = sampleRate

        # load instruments
        self.sfid = self.fl.sfload(soundfont)

        # parse midi
        self.parseNotes()

        self.initNotes()
        self.renderNotes()
        #self.debugPlay()

    def parseNotes(self) -> None:
        self.notes = []
        self.pitches = []
        self.instruments: list[Instrument] = []
        self.endTick = None
        self.condenseTracks = len(self.ps.instruments) > len(Instruments)

        # walk through the midi instrument tracks
        for rawInstru in self.ps.instruments:
            print("loading instrument %s, program %d" % (rawInstru.name, rawInstru.program))

            # check if we already have the instrument (only if we can't fit all tracks)
            instru = -1
            if self.condenseTracks:
                for x in range(len(self.instruments)):
                    if (self.instruments[x].bank == 128 and rawInstru.is_drum) or (self.instruments[x].bank == 0 and not rawInstru.is_drum):
                        if self.instruments[x].program == rawInstru.program:
                            instru = x
                            break

            # create track
            if instru == -1:
                instru = len(self.instruments)
                if rawInstru.is_drum:
                    self.instruments.append(Instrument(program=rawInstru.program, bank=128))
                else:
                    self.instruments.append(Instrument(program=rawInstru.program, bank=0))

            # notes
            for n in rawInstru.notes:
                self.notes.append(Note(note=n.pitch+self.transpose, velocity=n.velocity, instru=instru, start=n.start, end=n.end))
                if not self.endTick or self.endTick < n.end:
                    self.endTick = n.end

            # pitches
            for p in rawInstru.pitch_bends:
                self.pitches.append(Pitch(pitch=p.pitch, time=p.time, instru=instru))
                if not self.endTick or self.endTick < p.time:
                    self.endTick = p.time

            # pitch wheel settings ( TODO: probably a much better way to do this )
            for i, control in enumerate(rawInstru.control_changes):
                if control.number == 100 and control.value == 0:
                    self.instruments[instru].pitchBend = rawInstru.control_changes[i+1].value

        print("condensed %d tracks into %d tracks!" % (len(self.ps.instruments), len(self.instruments)))

    # get time at tick
    def toSeconds(self, tick) -> float:
        return self.tickTimeMap[tick]

    def _findEvent(self, tick) -> int:
        # search current events
        for i, evnt in enumerate(self.events):
            if evnt.time == tick:
                return i

        # no event found, insert
        self.events.append(MidiEvent(tick))
        return len(self.events)-1

    def _addNote(self, note: Note, tick: int, type: NoteEventType):
        evnt = self._findEvent(tick)
        self.events[evnt].addNote(note, type)

    def _addPitch(self, pitch: Pitch, tick: int):
        evnt = self._findEvent(tick)
        self.events[evnt].addPitch(pitch)

    def initNotes(self) -> None:
        self.events: list[MidiEvent] = []

        for i, note in enumerate(self.notes, 1):
            print("\rBuilding %d of %d notes" % (i, len(self.notes)), end='')

            # add start & stop event
            self._addNote(note, note.start, NoteEventType.PLAY)
            self._addNote(note, note.end, NoteEventType.STOP)
        print()

        for i, pitch in enumerate(self.pitches, 1):
            print("\rBuilding %d of %d pitches" % (i, len(self.pitches)), end='')

            self._addPitch(pitch, pitch.time)
        print()

        # sort events
        self.events.sort(key=lambda e: e.time)

    def renderNotes(self) -> None:
        for i in range(len(self.instruments)):
            self.fl.program_select(i, self.sfid, self.instruments[i].bank, self.instruments[i].program)

        # pause till first note
        self.sound = np.append(self.sound, self.fl.get_samples(int(self.sampleRate * self.toSeconds(self.events[0].time))))
        for e, evnt in enumerate(self.events, 1):
            print("\rRendering audio chunk %d of %d" % (e, len(self.events)), end='')

            # render pitch
            for pitch in evnt.pitches:
                fluidsynth.fluid_synth_pitch_bend(self.fl.synth, pitch.instru, self.instruments[pitch.instru].pitchBend)
                self.fl.pitch_bend(pitch.instru, pitch.pitch)

            # render note
            for note in evnt.notes:
                if note.type == NoteEventType.PLAY:
                    self.fl.noteon(note.note.instru, note.note.note, note.note.velocity)
                elif note.type == NoteEventType.STOP:
                    self.fl.noteoff(note.note.instru, note.note.note)

            # get time to render
            timeToNext = 2
            if e < len(self.events):
                timeToNext = self.toSeconds(self.events[e].time) - self.toSeconds(evnt.time)
            self.sound = np.append(self.sound, self.fl.get_samples(int(self.sampleRate * timeToNext)))
        print()

        self.fl.delete()

        self.sound = self.sound / np.max(self.sound)

        # converts self.sound into an unsigned 32bit int array, then multiplies by volume
        self.sound = (self.sound * (2 ** 31 - 1) * self.volume).astype(np.int32)

        # please python write examples for this, the docs for Wave_write are awful
        w = wave.Wave_write(self.tmpSound)
        w.setnchannels(2)
        w.setsampwidth(4)
        w.setframerate(self.sampleRate)
        #w.setnframes(int(self.endTick/2))
        w.writeframesraw(self.sound)
        w.close()

    # for testing
    def debugPlay(self) -> None:
        print("Playing song...")
        player = sa.play_buffer(self.sound, 2, 4, self.sampleRate)
        player.wait_done()