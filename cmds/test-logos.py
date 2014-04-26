#!/usr/bin/python

"""Tests for the logos program."""

import random
import select
import signal
import socket
import subprocess
import time
from wvtest.wvtest import *


def macAddressShapedString():
  chars = '0123456789abcdef::::::'
  return ''.join(random.choice(chars) for x in range(17))

@wvtest
def testLogos():
  # We use a SOCK_DGRAM here rather than a normal pipe, because datagram
  # sockets are guaranteed never to merge consecutive writes into a single
  # packet.  That way we can validate the correct merging of write() calls
  # into exactly one per line.
  sock1, sock2 = socket.socketpair(socket.AF_UNIX, socket.SOCK_DGRAM)
  pipefd1, pipefd2 = os.pipe()
  pipe1 = os.fdopen(pipefd1, 'r')  # for auto-close semantics
  pipe2 = os.fdopen(pipefd2, 'w')  # for auto-close semantics
  os.environ['LOGOS_DEBUG'] = '1'
  argv = ['./host-logos', 'fac', '50000']
  p = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=sock1.fileno())
  sock1.close()
  pipe2.close()
  fd1 = p.stdin.fileno()
  fd2 = sock2.fileno()

  def _Read():
    r, w, x = select.select([fd2, pipe1], [], [], 30)
    if pipe1 in r:
      WVFAIL('subprocess died unexpectedly')
      raise Exception('subprocess died unexpectedly with code %d' % p.wait())
    elif not r:
      raise Exception('read timed out')
    return os.read(fd2, 4096)

  # basics
  os.write(fd1, 'a\nErROR: b\nw: c')
  WVPASSEQ('<7>fac: a\n', _Read())
  WVPASSEQ('<3>fac: ErROR: b\n', _Read())
  r, w, x = select.select([fd2], [], [], 0)
  WVFAIL(r)
  os.write(fd1, '\n\n')
  WVPASSEQ('<4>fac: w: c\n', _Read())
  WVPASSEQ('<7>fac: \n', _Read())

  # tabs and CR
  os.write(fd1, 'a\tb\r\nabba\tbbb\naa\t\tb\tc\n')
  WVPASSEQ('<7>fac: a       b\n', _Read())
  WVPASSEQ('<7>fac: abba    bbb\n', _Read())
  WVPASSEQ('<7>fac: aa              b       c\n', _Read())
  os.write(fd1, ''.join(chr(i) for i in range(33)) + '\n')
  WVPASSEQ(r'<7>fac: ' +
           r'\x00\x01\x02\x03\x04\x05\x06\x07\x08    '
           + '\n', _Read())
  WVPASSEQ(r'<7>fac: ' +
           r'\x0b\x0c\x0e\x0f' +
           r'\x10\x11\x12\x13\x14\x15\x16\x17' +
           r'\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f ' +
           '\n', _Read())

  # very long lines should be broken, but not missing any characters
  sent = ('x ' * 2000)
  for c in sent:
    os.write(fd1, c)
  os.write(fd1, '\nbooga!')
  total = ''
  while total != sent:
    print 'len(total)=%d len(sent)=%d' % (len(total), len(sent))
    result = _Read()
    WVPASSLT(len(result), len(sent))
    WVPASS(result.startswith('<7>fac: '))
    WVPASS(result.endswith('\n'))
    total += result[8:-1]
    if not WVPASS(sent.startswith(total)):
      return
  result = _Read()
  print '%r' % result
  WVPASS(result.startswith('<4>fac: W: '))
  r, w, x = select.select([fd2], [], [], 0)
  WVFAIL(r)
  os.write(fd1, '\n')
  WVPASSEQ('<7>fac: booga!\n', _Read())

  # MAC addresses
  os.write(fd1, 'f8:8f:ca:00:00:01\n')
  WVPASSEQ('<7>fac: f8:8f:ca:00:XX:XX\n', _Read())
  os.write(fd1, '8:8f:ca:00:00:01\n')
  WVPASSEQ('<7>fac: 8:8f:ca:00:00:01\n', _Read())
  os.write(fd1, '8:8f:ca:00:00:01:\n')
  WVPASSEQ('<7>fac: 8:8f:ca:00:00:01:\n', _Read())
  os.write(fd1, ':::semicolons:f8:8f:ca:00:00:01:and:after\n')
  WVPASSEQ('<7>fac: :::semicolons:f8:8f:ca:00:XX:XX:and:after\n', _Read())
  os.write(fd1, 'f8-8f-ca-00-00-01\n')
  WVPASSEQ('<7>fac: f8-8f-ca-00-XX-XX\n', _Read())

  # Send in random strings to look for crashes.
  for x in range(10):
    mac = macAddressShapedString()
    print 'Trying %s to check for crashes' % mac
    os.write(fd1, mac + '\n')
    print _Read()

  # Filenames
  os.write(fd1, 'Accessing /var/media/pictures/MyPicture.jpg for decode\n')
  WVPASSEQ('<7>fac: Accessing /var/media/pictures/XXXXXXXXXXXXX for decode\n',
           _Read())
  os.write(fd1, '/var/media/pictures/MyPicture.jpg\n')
  WVPASSEQ('<7>fac: /var/media/pictures/XXXXXXXXXXXXX\n',
           _Read())
  os.write(fd1, 'Accessing /var/media/videos/MyMovie.mpg for decode\n')
  WVPASSEQ('<7>fac: Accessing /var/media/videos/XXXXXXXXXXX for decode\n',
           _Read())
  os.write(fd1, 'Accessing /var/media/tv/MyTvShow.ts for decode\n')
  WVPASSEQ('<7>fac: Accessing /var/media/tv/MyTvShow.ts for decode\n',
           _Read())
  os.write(fd1, 'check "/var/media/videos/MyTvShow.ts"len=1024\n')
  WVPASSEQ('<7>fac: check "/var/media/videos/XXXXXXXXXXX"len=1024\n',
           _Read())

  # rate limiting
  os.write(fd1, (('x'*80) + '\n') * 500)
  result = ''
  while 'burst limit' not in result:
    result = _Read()
    print repr(result)
  print 'got: %r' % result
  WVPASS('rate limiting started')
  while 1:
    # drain the input until it's idle
    r, w, x = select.select([fd1], [], [], 0.1)
    if not r:
      break

  p.send_signal(signal.SIGHUP)  # refill the bucket, ending rate limiting
  os.write(fd1, 'Awake!\n')
  result = ''
  while 'burst limit' not in result:
    result = _Read()
  print 'got: %r' % result
  WVPASS('rate limiting finished')

  result = ''
  while 'Awake!' not in result:
    result = _Read()
  WVPASS('awake!')

  p.stdin.close()
  WVPASSEQ(p.wait(), 0)


if __name__ == '__main__':
  wvtest_main()
