#!/usr/bin/python
# Copyright 2013 Google Inc. All Rights Reserved.

"""Basic implementation of a remote control emulator for the GFHD100.

Soft_rc runs on the GFHD100 TV Box and registers itself as remote
control to the bthid kernel driver and allows the user to send
keypress codes into it.


The RC exhibits the following behaviors:
---
When a key is pushed down, the RC sends the BT keycode for this
key. This is a key-down event and only send once. If the key remains
pressed down, no additional events are send. Any repetitive key
presses seen in the logs (and via the TV Box's LED blinking
feverishly) are generated by the HID system.

When a key is released on the remote, the RC sends a release
keycode. When the HID receives this code it will stop any repetitive
key events. There are only two unique release keycodes - one for all
the digits (0..9) and the DEL key, and another one for all the other
keys. soft_rc.py automatically selects the correct release code based
on what keycode was send prior.

When two or more keys are pressed at the same time, no keycode is sent
at all (internally the RC allows several keys to be pressed to trigger
onboard features like pairing reset and TV model setup). If a key is
pressed down and then a second key is pressed down afterwards, the
latter key press causes the release keycode for the former key to be
send. If one of the two keys is released, the keycode for the
remaining key is send (as if it was just pressed down). E.g.:
Key-A pressed --> Key-A keycode send
Key-B pressed --> Release keycode send for key-A
Key-A released -->  Key-B keycode send
What this means in essence is that a key-pressed event is *always*
followed by a key-release event.

There are special keycodes used to send status information. Currently,
there is only one: Battery-Level, which gives the current charge level
in %.


Command Line Options
---
[-i,--input <scriptfname>] : script-mode vs. interactive Mode (default)
In interactive mode soft_rc.py reads commands from stdin. If not
redirected, it will wait for user input to be typed in. Several
keywords can be entered on the same line, separated by spaces.  By
using a named pipe and having soft_rc.py read from it, one can feed RC
commands from another (test) script.
In script mode, a text file is provided that contains RC keycode
strings to be executed. For timing keypresses, use the SLEEP special
key.

[-r,--raw] : Raw-mode vs. Autorelease (default)
As explained above, a keypress needs to be followed by a key
release. When in autorelease mode, soft_rc.py will automatically send
a release keycode about 0.1secs after the keypress was sent. That
should be sufficient for most users. If you need control over when
release codes are send, you can enable raw-mode. When in that mode you
are responsible for sending the release code yourself.

[-s,--simumode] : Simulation-mode
In simulation mode, everything works as before except that soft_rc.py
doesn't actually connect to bthid and write keycodes to it. This is
helpful to test out things on a different computer or if you don't
want to actually have the keycodes be executed.

[-k,--keys] : Print the supported key names

[-d,--dlevel] : Sets debugs log level (0:ERR, 1:WARN, 2:INFO, 3:VERB)


Supported RC Keywords (case insensitive)
---
DIGIT_1, DIGIT_2, .. , DIGIT_9, DIGIT_0, DEL,
TV_BOX_POWER, TV_POWER, INPUT,
STOP, RECORD, REWIND, PLAY, FAST_FORWARD, SKIP_BACKWARD, PAUSE, SKIP_FORWARD
MENU, BACK, GUIDE, UP, LEFT, OK, RIGHT, DOWN
EXIT, INFO, VOL_UP, SEARCH, CH_UP, VOL_DOWN, MUTE, CH_DOWN, PREV


Special Keywords (mainly for interactive mode)
---
HELP
Prints the supported key strings.

END
Exits the program.

REL
Sends a Release key (automatically determines the correct release key
code based on the previous key pressed). Only needed in raw
mode. Sending several REL keys don't hurt and are ignored by the HID
subsystem.

SLEEPx.y
Sleeps for x.y secs (useful in script mode and/or when in raw mode).

BATT_LEVELx
Sends battery level <x> (in %).

RAWMODEx
Set raw-mode off (x=0) or on (all else).

DEBUGx
Change debug level to 'x' (useful in interactive mode).
"""

__author__ = "ckuiper@google.com (Chris Kuiper)"


import fcntl
import os
import sys
import time
import options


# pylint: disable=g-wrong-space
VER_MAJOR = 0
VER_MINOR = 1

UNKNOWN_KEY = 0xdeadbeef
BTHID_DEV = "/dev/bthid"

MAGIC_KEY_HELP    = "HELP"
MAGIC_KEY_END     = "END"
MAGIC_KEY_REL     = "REL"
MAGIC_KEY_SLEEP   = "SLEEP"
MAGIC_KEY_BATLV   = "BATT_LEVEL"
MAGIC_KEY_RAWMODE = "RAWMODE"
MAGIC_KEY_DEBUG   = "DEBUG"

LOG_ERR  = 0
LOG_WARN = 1
LOG_INFO = 2
LOG_VERB = 3
LOG_ALL  = 99

SLEEP_BEFORE_RELEASE_TIME = 0.1  # secs

optspec = """
soft_rc.py [options]
--
i,input=    Provides an input script of key presses
r,raw       Raw-mode, disabling auto key-release
s,simumode  Enables simulation mode, i.e., no key codes are send
k,keys      Print the supported key names
d,dlevel=   Sets debugs log level (0:ERR, 1:WARN, 2:INFO, 3:VERB) [1]
"""

keymap = {
    "BATT_LEVEL":    0x001302,
    "DIGIT_1":       0x1e4102,
    "DIGIT_2":       0x1f4102,
    "DIGIT_3":       0x204102,
    "DIGIT_4":       0x214102,
    "DIGIT_5":       0x224102,
    "DIGIT_6":       0x234102,
    "DIGIT_7":       0x244102,
    "DIGIT_8":       0x254102,
    "DIGIT_9":       0x264102,
    "DIGIT_0":       0x274102,
    "DEL":           0x2a4102,
    "RELEASE2":      0x004102,
    "TV_BOX_POWER":  0x00304003,
    "TV_POWER":      0x00821203,
    "INPUT":         0x00824003,
    "STOP":          0x00B74003,
    "RECORD":        0x00B24003,
    "REWIND":        0x00B44003,
    "PLAY":          0x00B04003,
    "FAST_FORWARD":  0x00B34003,
    "SKIP_BACKWARD": 0x00B64003,
    "PAUSE":         0x00B14003,
    "SKIP_FORWARD":  0x00B54003,
    "MENU":          0x00404003,
    "BACK":          0x02244003,
    "GUIDE":         0x008D4003,
    "UP":            0x00424003,
    "LEFT":          0x00444003,
    "OK":            0x00414003,
    "RIGHT":         0x00454003,
    "DOWN":          0x00434003,
    "EXIT":          0x02044003,
    "INFO":          0x00044003,
    "VOL_UP":        0x00E94003,
    "SEARCH":        0x00F74003,
    "CH_UP":         0x009C4003,
    "VOL_DOWN":      0x00EA4003,
    "MUTE":          0x00E24003,
    "CH_DOWN":       0x009D4003,
    "PREV":          0x00834003,
    "RELEASE3":      0x00004003
}


def GetBthidControlStruct():
  """Build BTHID_CONTROL data structure.

  Returns:
    BTHID_CONTROL structure as a byte-buffer

  typedef struct _BTHID_CONTROL
  {
      int size
      unsigned char data[800]
      unsigned char bd_addr[BD_ADDR_LEN]
  } BTHID_CONTROL
  """
  size = "\xB3\x00\x00\x00"  # 179
  descr = (
      "\x05\x01\x09\x06\xA1\x01\x85\x41\x75\x08\x95\x01\x26\xFF\x00\x05"
      "\x07\x19\x00\x2A\xFF\x00\x81\x00\xC0\x05\x0C\x09\x01\xA1\x01\x85"
      "\x40\x19\x00\x2A\xFF\x03\x75\x10\x95\x01\x15\x00\x26\xFF\x03\x81"
      "\x00\xC0\x05\x01\x09\x80\xA1\x01\x85\x12\x19\x81\x29\x93\x15\x81"
      "\x25\x93\x75\x08\x95\x01\x81\x40\xC0\x05\x0C\x09\x01\xA1\x01\x85"
      "\x13\x09\x20\x15\x00\x25\x64\x75\x08\x95\x01\x81\x42\xC0\x85\x21"
      "\x09\x21\x75\x08\x95\x01\x15\x00\x26\xFF\x00\x81\x02\x85\x22\x05"
      "\x01\x09\x22\xA1\x02\x09\x3B\x95\x01\x75\x10\x15\x00\x26\x4F\x01"
      "\x81\x02\x06\xF0\xFF\x09\x22\x75\x10\x96\x4F\x01\x15\x00\x26\xFF"
      "\x00\x82\x01\x02\xC0\x85\xF2\x09\x02\x75\x08\x95\x01\x15\x00\x26"
      "\xFF\x00\x91\x02\x85\xF3\x09\x03\x75\x08\x95\x10\x15\x00\x26\xFF"
      "\x00\x81\x02")
  data = descr + (800 - len(descr)) * "\x00"
  bd_addr = "\xba\xd0\xFA\xCE\xb0\x0C"
  total = size + data + bd_addr
  return buffer(total, 0, len(total))


def PrintKeys():
  """Print supported key names."""
  print "\nSupported Key names (case-insensitive):"
  print "======================================="
  print "Special keys:\n------------"
  print "  'HELP': Print supported key names (useful in interactive mode)"
  print "  'END': Exit this program"
  print "  'REL': Send release key (key-up) for the last key pressed down"
  print "         E.g.: 'INFO REL' -> INFO key-down, then INFO key-up"
  print "  'SLEEPx.y': Sleep for x.y secs"
  print("         E.g.: GUIDE SLEEP0.5 REL -> GUIDE key-down, "
        "then sleep 0.5sec, then GUIDE key-up")
  print "  'BATT_LEVELx': Send battery level <x> [%]"
  print "                 E.g.: BATT_LEVEL55 -> Send Battery-level 55%"
  print "  'RAWMODEx': set raw-mode off (x=0) or on (all else)"
  print "  'DEBUGx': change debug level to x (useful in interactive mode)"
  print "\nRemote Control key names:\n-------------------------"
  print "%s\n" % sorted(keymap.keys())


class RcServer(object):
  """Implements the Remote Control server."""

  def Log(self, level, text):
    if level == LOG_ALL or level <= self.debug_level:
      print text

  def __init__(self, autorelease, simu_mode, inScript, debug_level):
    self.autorelease = autorelease
    self.simu_mode = simu_mode
    self.dev_fd = None
    self.in_script_fd = None
    self.debug_level = debug_level
    self.prev_key_code = None

    self.Log(LOG_ALL, "autorelease=%d, debug_level=%d, simu_mode=%d"
             % (self.autorelease, self.debug_level, self.simu_mode))

    if not inScript:
      self.Log(LOG_INFO, "Running in interactive mode")
    else:
      self.Log(LOG_INFO, "Opening input script %r" % inScript)
      try:
        self.in_script_fd = open(inScript, "r")
      except IOError:
        print "Cannot open input script %r" % inScript
        raise

    if self.simu_mode:
      self.Log(LOG_INFO, "Simulation mode, skipping opening bthid device.")
    else:
      self.Log(LOG_INFO, "Opening bthid device %r" % BTHID_DEV)
      try:
        self.dev_fd = os.open(BTHID_DEV, os.O_RDWR)
      except (IOError, OSError):
        print "Cannot open device %r" % BTHID_DEV
        raise
      else:
        # Register to bthid
        try:
          fcntl.ioctl(self.dev_fd, 1, GetBthidControlStruct())
        except (IOError, OSError):
          print "Cannot ioctl to device %r" % BTHID_DEV
          raise

  def GetKeyUp(self, keycode):
    return keycode & 0x0000ffff

  def WriteKeyCode(self, keycode):
    if self.simu_mode:
      self.Log(LOG_INFO, "Send (simulated) keycode = %x" % keycode)
    else:
      self.Log(LOG_INFO, "Send keycode = %x" % keycode)
      count = keycode & 0xff
      warr = bytearray()
      for i in range(count):
        warr.append((keycode >> (8*(i+1))) & 0xff)
      wbuf = buffer(warr, 0, count)
      try:
        os.write(self.dev_fd, wbuf)
      except (IOError, OSError):
        print "Cannot write keycode %x to device %r" % (keycode, BTHID_DEV)
        raise

  def Run(self):
    finished = False
    while not finished:
      #
      # Read a new command line from file or stdin
      #
      if self.in_script_fd:
        line = self.in_script_fd.readline().rstrip("\r\n")
        if line:
          print line
        else:
          print "EOF -> send %r" % MAGIC_KEY_END
          line = MAGIC_KEY_END
      else:
        try:
          line = sys.stdin.readline().rstrip("\r\n")
        except KeyboardInterrupt:
          break
      #
      # Parse the command line
      #
      for token in line.upper().split():
        self.Log(LOG_VERB, "token %r" % token)

        # 'HELP'
        if token == MAGIC_KEY_HELP:
          PrintKeys()
          continue

        # 'END'
        if token == MAGIC_KEY_END:
          # clean up if possible
          if self.prev_key_code:
            keycode = self.GetKeyUp(self.prev_key_code)
            self.Log(LOG_VERB, "Enter:'REL' -> 0x%x" % keycode)
            self.WriteKeyCode(keycode)
          finished = True
          break

        # 'SLEEPx.y'
        elif token.find(MAGIC_KEY_SLEEP, 0, len(MAGIC_KEY_SLEEP)) == 0:
          tstr = token[len(MAGIC_KEY_SLEEP):]
          try:
            t = float(tstr)
          except ValueError:
            t = SLEEP_BEFORE_RELEASE_TIME
            self.Log(LOG_WARN, "SLEEP: %r is not a float, "
                     "use default %d secs instead" % (tstr, t))
          self.Log(LOG_INFO, "Sleeping %f secs" % t)
          time.sleep(t)
          continue

        # 'REL'
        elif token == MAGIC_KEY_REL:
          if self.prev_key_code:
            keycode = self.GetKeyUp(self.prev_key_code)
          else:
            self.Log(LOG_WARN, "%r not valid, no previous key-down exists!" %
                     MAGIC_KEY_REL)
            continue

        # 'BATT_LEVEL'
        elif token.find(MAGIC_KEY_BATLV, 0, len(MAGIC_KEY_BATLV)) == 0:
          levelstr = token[len(MAGIC_KEY_BATLV):]
          token = MAGIC_KEY_BATLV
          if levelstr.isdigit():
            level = int(levelstr)
            if level > 100:
              level = 100
            self.Log(LOG_INFO, "Send battery-level = %d" % level)
            keycode = keymap.get(token) | (level << 16)

        # 'RAWMODEx'
        elif token.find(MAGIC_KEY_RAWMODE, 0, len(MAGIC_KEY_RAWMODE)) == 0:
          rawmodestr = token[len(MAGIC_KEY_RAWMODE):len(MAGIC_KEY_RAWMODE)+1]
          if rawmodestr == "0":
            self.Log(LOG_ALL, "Disable raw-mode (autorelease = on)")
            self.autorelease = True
          else:
            self.Log(LOG_ALL, "Enable raw-mode (autorelease = off)")
            self.autorelease = False
          continue

        # 'DEBUG'
        elif token.find(MAGIC_KEY_DEBUG, 0, len(MAGIC_KEY_DEBUG)) == 0:
          dlevelstr = token[len(MAGIC_KEY_DEBUG):]
          if dlevelstr.isdigit():
            dlevel = int(dlevelstr)
            if dlevel <= LOG_VERB and dlevel >= LOG_ERR:
              self.debug_level = dlevel
              self.Log(LOG_ALL, "Changed debug level to %d" % self.debug_level)
              continue
          # error case
          self.Log(LOG_ERR, "Unknown debug level %r, must be [%d..%d]."
                   % (dlevelstr, LOG_ERR, LOG_VERB))
          continue

        # regular key
        else:
          keycode = keymap.get(token, UNKNOWN_KEY)
          if keycode == UNKNOWN_KEY:
            self.Log(LOG_WARN, "Unknown keystr %r, ignore." % token)
            continue

        # Send into the driver
        self.Log(LOG_VERB, "Enter: %r -> 0x%x" % (token, keycode))
        self.WriteKeyCode(keycode)

        # if not in raw-mode sleep a little and send key-up
        if self.autorelease and (keycode & 0xffff0000):
          time.sleep(SLEEP_BEFORE_RELEASE_TIME)
          keycode = self.GetKeyUp(keycode)
          self.Log(LOG_VERB, "Enter:'REL' -> 0x%x" % keycode)
          self.WriteKeyCode(keycode)

        self.prev_key_code = keycode


def main(argv):
  print "Version %d.%d" % (VER_MAJOR, VER_MINOR)

  o = options.Options(optspec)
  opt, _, _ = o.parse(argv[1:])

  if opt.keys:
    PrintKeys()
    exit(0)

  autorelease = False if opt.raw else True
  simumode = True if opt.simumode else False
  try:
    debug_level = int(str(opt.dlevel))
  except ValueError:
    debug_level = LOG_WARN

  try:
    RcServer(autorelease, simumode, opt.input, debug_level).Run()
  except (IOError, OSError) as e:
    sys.stdout.flush()
    sys.stderr.write("Error: %s\n\n" % e)
    exit(1)

  exit(0)

if __name__ == "__main__":
  main(sys.argv)
