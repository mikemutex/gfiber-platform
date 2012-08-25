#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.

"""Image installer for GFHD100."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import collections
import os
import re
import subprocess
import sys
import tarfile
from Crypto.Hash import SHA512
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
import options


optspec = """
ginstall -p <partition>
ginstall -p <partition> -t <tarfile> [options...]
ginstall -p <partition> -k <kernel> -r <rootfs> [options...]
--
t,tar=        tar archive containing kernel and rootfs
k,kernel=     kernel image filename to install
r,rootfs=     rootfs UBI image filename to install
skiploader    skip installing bootloader (dev-only)
loader=       bootloader file to install
loadersig=    bootloader signature filename
drm=          drm blob filename to install
p,partition=  partition to install to (primary, secondary, or other)
q,quiet       suppress unnecessary output
"""


# unit tests can override these with fake versions
BUFSIZE = 256 * 1024
FLASH_ERASE = '/usr/sbin/flash_erase'
HNVRAM = '/usr/bin/hnvram'
MTDBLOCK = '/dev/mtdblock{0}'
PROC_MTD = '/proc/mtd'
SYS_UBI0 = '/sys/class/ubi/ubi0/mtd_num'
UBIFORMAT = '/usr/sbin/ubiformat'
UBIPREFIX = '/usr/sbin/ubi'
ROOTFSUBI_NO = '5'
GZIP_HEADER = '\x1f\x8b\x08'  # encoded as string to ignore endianness


# Verbosity of output
quiet = False

# Partitions supported
gfhd100_partitions = {'primary': 0, 'secondary': 1}


class Fatal(Exception):
  """An exception that we print as just an error, with no backtrace."""
  pass


def Verify(f, s, k):
  key = RSA.importKey(k.read())
  h = SHA512.new(f.read())
  v = PKCS1_v1_5.new(key)
  return v.verify(h, s.read())


def Log(s, *args):
  sys.stdout.flush()
  if args:
    sys.stderr.write(s % args)
  else:
    sys.stderr.write(s)


def VerbosePrint(s, *args):
  if not quiet:
    Log(s, *args)


def SetBootPartition(partition):
  extra = 'ubi.mtd=rootfs{0} root=mtdblock:rootfs rootfstype=squashfs'.format(
      partition)
  cmd = [HNVRAM,
         '-w', 'MTD_TYPE_FOR_KERNEL=RAW',
         '-w', 'ACTIVATED_KERNEL_NAME=kernel{0}'.format(partition),
         '-w', 'EXTRA_KERNEL_OPT={0}'.format(extra)]
  devnull = open('/dev/null', 'w')
  return subprocess.call(cmd, stdout=devnull)


def GetBootedPartition():
  """Get the role of partition where the running system is booted from.

  Returns:
    "primary" or "secondary" boot partition, or None if not booted from flash.
  """
  try:
    f = open(SYS_UBI0)
    line = f.readline().strip()
  except IOError:
    return None
  booted_mtd = 'mtd' + str(int(line))
  for (pname, pnum) in gfhd100_partitions.items():
    rootfs = 'rootfs' + str(pnum)
    mtd = GetMtdDevForPartition(rootfs)
    if booted_mtd == mtd:
      return pname
  return None


def GetOtherPartition(partition):
  """Get the role of the other partition.

  Args:
    partition: current parition role.

  Returns:
    The name of the other partition.
    If partion=primary, will return 'secondary'.
  """
  for (pname, _) in gfhd100_partitions.items():
    if pname != partition:
      return pname
  return None


def GetMtdNum(arg):
  """Return the integer number of an mtd device, given its name or number."""
  try:
    return int(arg)
  except ValueError:
    pass
  m = re.match(r'(/dev/){0,1}mtd(\d+)', arg)
  if m:
    return int(m.group(2))
  return False


def GetEraseSize(mtd):
  """Find the erase block size of an mtd device.

  Args:
    mtd: integer number of the MTD device, or its name. Ex: 3, or "mtd3"

  Returns:
    The erase size as an integer, 0 if not found.
  """
  mtd = 'mtd' + str(GetMtdNum(mtd))
  splt = re.compile('[ :]+')
  f = open(PROC_MTD)
  for line in f:
    fields = splt.split(line.strip())
    if len(fields) >= 3 and fields[0] == mtd:
      return int(fields[2], 16)
  return 0


def GetMtdDevForPartition(name):
  """Find the mtd# for a named partition.

  In /proc/mtd we have:

  dev:    size   erasesize  name
  mtd0: 00200000 00010000 "cfe"
  mtd1: 00200000 00010000 "reserve0"
  mtd2: 10000000 00100000 "kernel0"
  mtd3: 10000000 00100000 "kernel1"

  Args:
    name: the partition to find. For example, "kernel0"

  Returns:
    The mtd device, for example "mtd2"
  """
  splt = re.compile('[ :]+')
  quotedname = '"' + name + '"'
  f = open(PROC_MTD)
  for line in f:
    fields = splt.split(line.strip())
    if len(fields) >= 4 and fields[3] == quotedname:
      return fields[0]
  return None


def IsDeviceB0():
  """Returns true if the device is a BCM7425B0 platform."""
  return open('/proc/cpuinfo').read().find('BCM7425B0') >= 0


def IsDevice4GB():
  """Returns true if the device is using old-style 4GB NAND layout."""
  partition = GetMtdNum(GetMtdDevForPartition('rootfs0'))
  return GetFileSize(partition) == 0x40000000  # ie. size of v1 root partition


def RoundTo(orig, mult):
  """Round orig up to a multiple of mult."""
  return ((orig + mult - 1) // mult) * mult


def EraseMtd(mtd):
  """Erase an mtd partition.

  Args:
    mtd: integer number of the MTD device, or its name. Ex: 3, or "mtd3"

  Returns:
    true if successful.
  """
  devmtd = '/dev/mtd' + str(GetMtdNum(mtd))
  cmd = [FLASH_ERASE, '--quiet', devmtd, '0', '0']
  devnull = open('/dev/null', 'w')
  return subprocess.call(cmd, stdout=devnull)


def WriteToFile(srcfile, dstfile):
  """Copy all bytes from srcfile to dstfile."""
  buf = srcfile.read(BUFSIZE)
  totsize = 0
  while buf:
    totsize += len(buf)
    dstfile.write(buf)
    buf = srcfile.read(BUFSIZE)
    VerbosePrint('.')
  return totsize


def IsIdentical(srcfile, dstfile):
  """Compare srcfile and dstfile. Return true if contents are identical."""
  sbuf = srcfile.read(BUFSIZE)
  dbuf = dstfile.read(len(sbuf))
  if not sbuf:
    raise IOError('IsIdentical: srcfile is empty?')
  if not dbuf:
    raise IOError('IsIdentical: dstfile is empty?')
  while sbuf and dbuf:
    if sbuf != dbuf:
      return False
    sbuf = srcfile.read(BUFSIZE)
    dbuf = dstfile.read(len(sbuf))
    VerbosePrint('.')
  return True


def GetFileSize(f):
  """Return size of a file like object."""
  current = f.tell()
  f.seek(0, os.SEEK_END)
  size = f.tell()
  f.seek(current, os.SEEK_SET)
  return size


def InstallToMtd(f, mtd):
  """Write an image to an mtd device."""
  if EraseMtd(mtd):
    raise IOError('Flash erase failed.')
  mtdblockname = MTDBLOCK.format(GetMtdNum(mtd))
  start = f.tell()
  with open(mtdblockname, 'r+b') as mtdfile:
    written = WriteToFile(f, mtdfile)
    f.seek(start, os.SEEK_SET)
    mtdfile.seek(0, os.SEEK_SET)
    if not IsIdentical(f, mtdfile):
      raise IOError('Flash verify failed')
    return written


def InstallUbiFileToUbi(f, mtd):
  """Write an image with ubi header to a ubi device.

  Args:
    f: a file-like object holding the image to be installed.
    mtd: the mtd partition to install to.

  Raises:
    IOError: when ubi format fails

  Returns:
    number of bytes written.
  """
  fsize = GetFileSize(f)
  writesize = RoundTo(fsize, GetEraseSize(mtd))
  devmtd = '/dev/mtd' + str(GetMtdNum(mtd))
  cmd = [UBIFORMAT, devmtd, '-f', '-', '-y', '-q', '-S', str(writesize)]
  ub = subprocess.Popen(cmd, stdin=subprocess.PIPE)
  siz = WriteToFile(f, ub.stdin)
  ub.stdin.close()  # send EOF to UBIFORMAT
  rc = ub.wait()
  if rc != 0 or siz != fsize:
    raise IOError('ubi format failed')
  return siz


def UbiCmd(name, args):
  """Wrapper for ubi calls."""
  cmd = collections.deque(args)
  cmd.appendleft(UBIPREFIX + name)
  rc = subprocess.call(cmd)
  if rc != 0:
    raise IOError('ubi ' + name + ' failed')


def InstallRawFileToUbi(f, mtd, ubino):
  """Write an image without ubi header to a ubi device.

  Args:
    f: a file-like object holding the image to be installed.
    mtd: the mtd partition to install to.
    ubino: the ubi device number to attached ubi partition.

  Raises:
    IOError: when ubi format fails

  Returns:
    number of bytes written.
  """
  devmtd = '/dev/mtd' + str(GetMtdNum(mtd))
  if os.path.exists('/dev/ubi' + ubino):
    UbiCmd('detach', ['-d', ubino])
  UbiCmd('format', [devmtd, '-y', '-q'])
  UbiCmd('attach', ['-m', str(GetMtdNum(mtd)), '-d', ubino])
  UbiCmd('mkvol', ['/dev/ubi' + ubino, '-N', 'rootfs-prep', '-m'])
  mtd = GetMtdDevForPartition('rootfs-prep')
  siz = InstallToMtd(f, mtd)
  UbiCmd('rename', ['/dev/ubi' + ubino, 'rootfs-prep', 'rootfs'])
  UbiCmd('detach', ['-d', ubino])
  return siz


class FileImage(object):
  """A system image packaged as separate kernel, rootfs and loader files."""

  def __init__(self, kernelfile, rootfs, loader, loadersig):
    self.kernelfile = kernelfile
    self.rootfs = rootfs
    if self.rootfs:
      self.rootfstype = rootfs[7:]
    else:
      self.rootfstype = None
    self.loader = loader
    self.loadersig = loadersig

  def GetVersion(self):
    return None

  def GetLoader(self):
    if self.loader:
      try:
        return open(self.loader, 'rb')
      except IOError, e:
        raise Fatal(e)
    else:
      return None

  def GetKernel(self):
    if self.kernelfile:
      try:
        return open(self.kernelfile, 'rb')
      except IOError, e:
        raise Fatal(e)
    else:
      return None

  def IsRootFsUbi(self):
    if self.rootfstype[-4:] == '_ubi':
      return True
    return False

  def GetRootFs(self):
    if self.rootfs:
      try:
        return open(self.rootfs, 'rb')
      except IOError, e:
        raise Fatal(e)
    else:
      return None

  def GetLoaderSig(self):
    if self.loadersig:
      try:
        return open(self.loadersig, 'rb')
      except IOError, e:
        raise Fatal(e)
    else:
      return None


class TarImage(object):
  """A system image packaged as a tar file."""

  def __init__(self, tarfilename):
    self.tarfilename = tarfilename
    self.tar_f = tarfile.open(name=tarfilename)
    fnames = self.tar_f.getnames()
    for fname in fnames:
      if fname[:7] == 'rootfs.':
        self.rootfstype = fname[7:]
        break

  def GetVersion(self):
    # no point catching this error: if there's no version file, the
    # whole install image is definitely invalid.
    return self.tar_f.extractfile('version').read(4096).strip()

  def GetKernel(self):
    try:
      return self.tar_f.extractfile('vmlinuz')
    except KeyError:
      try:
        return self.tar_f.extractfile('vmlinux')
      except KeyError:
        return None

  def IsRootFsUbi(self):
    if self.rootfstype[-4:] == '_ubi':
      return True
    return False

  def GetRootFs(self):
    try:
      return self.tar_f.extractfile('rootfs.' + self.rootfstype)
    except KeyError:
      return None

  def GetLoader(self):
    if IsDeviceB0():
      Log('old B0 device: ignoring loader.bin in tarball\n')
      return None
    try:
      return self.tar_f.extractfile('loader.bin')
    except KeyError:
      return None

  def GetLoaderSig(self):
    try:
      return self.tar_f.extractfile('loader.sig')
    except KeyError:
      return None


def main():
  global quiet  #gpylint: disable-msg=W0603
  o = options.Options(optspec)
  opt, flags, extra = o.parse(sys.argv[1:])  #gpylint: disable-msg=W0612

  if not (opt.drm or opt.kernel or opt.rootfs or opt.loader or opt.tar or
          opt.partition):
    o.fatal('Expected at least one of -p, -k, -r, -t, --loader, or --drm')

  quiet = opt.quiet
  if opt.drm:
    Log('DO NOT INTERRUPT OR POWER CYCLE, or you will lose drm capability.\n')
    try:
      drm = open(opt.drm, 'rb')
    except IOError, e:
      raise Fatal(e)
    mtd = GetMtdDevForPartition('drmregion0')
    VerbosePrint('Writing drm to %r', mtd)
    InstallToMtd(drm, mtd)
    VerbosePrint('\n')

    drm.seek(0)
    mtd = GetMtdDevForPartition('drmregion1')
    VerbosePrint('Writing drm to %r', mtd)
    InstallToMtd(drm, mtd)
    VerbosePrint('\n')

  if (opt.kernel or opt.rootfs or opt.tar) and not opt.partition:
    # default to the safe option if not given
    opt.partition = 'other'

  if opt.partition:
    if opt.partition == 'other':
      boot = GetBootedPartition()
      if boot is None:
        # Policy decision: if we're booted from NFS, install to secondary
        partition = 'secondary'
      else:
        partition = GetOtherPartition(boot)
    else:
      partition = opt.partition
    pnum = gfhd100_partitions[partition]
  else:
    partition = None
    pnum = None

  if opt.tar or opt.kernel or opt.rootfs:
    if not partition:
      o.fatal('A --partition option must be provided with -k, -r, or -t')
    if partition not in gfhd100_partitions:
      o.fatal('--partition must be one of: ' + str(gfhd100_partitions.keys()))

  if opt.tar or opt.kernel or opt.rootfs or opt.loader:
    if opt.tar:
      img = TarImage(opt.tar)
      if opt.kernel or opt.rootfs or opt.loader or opt.loadersig:
        o.fatal('--tar option is incompatible with -k, -r, '
                '--loader and --loadersig')
    else:
      img = FileImage(opt.kernel, opt.rootfs, opt.loader, opt.loadersig)

    try:
      key = open('/etc/gfiber_public.der')
    except IOError, e:
      raise Fatal(e)

    # old software versions are incompatible with 1 GB NAND partition format
    # (whether or not you're physically using SLC NAND or not) so don't try
    # to install on those devices.  But allow old versions on other
    # platforms, for easier upgrade/downgrade testing.
    ver = img.GetVersion()
    if (ver and ver.startswith('bruno-') and ver < 'bruno-octopus-3' and
        not IsDevice4GB()):
      raise Fatal("%r is too old for new-style partitions: aborting.\n" % ver)

    rootfs = img.GetRootFs()
    if rootfs:
      # log rootfs type in case wrong rootfs is installed
      if img.IsRootFsUbi():
        Log('Installing ubi-formatted rootfs.\n')
      else:
        Log('Installing raw rootfs image to ubi partition.\n')
      mtd = GetMtdDevForPartition('rootfs' + str(pnum))
      VerbosePrint('Writing rootfs to %r', mtd)
      if img.IsRootFsUbi():
        InstallUbiFileToUbi(rootfs, mtd)
      else:
        InstallRawFileToUbi(rootfs, mtd, ROOTFSUBI_NO)
      VerbosePrint('\n')

    kern = img.GetKernel()
    if kern:
      mtd = GetMtdDevForPartition('kernel' + str(pnum))
      if IsDeviceB0():
        buf = kern.read(4100)
        if buf[0:3] != GZIP_HEADER and buf[4096:4099] == GZIP_HEADER:
          VerbosePrint('old B0 device: removing kernel signing.\n')
          kern.seek(4096)
        elif buf[0:3] == GZIP_HEADER:
          VerbosePrint('old B0 device: no kernel signing, not removing.\n')
          kern.seek(0)
        else:
          raise Fatal('old B0 device: unrecognized kernel format')
      VerbosePrint('Writing kernel to {0}'.format(mtd))
      InstallToMtd(kern, mtd)
      VerbosePrint('\n')

    loader = img.GetLoader()
    if loader:
      loader_start = loader.tell()
      if opt.skiploader:
        VerbosePrint('Skipping loader installation.\n')
      else:
        loadersig = img.GetLoaderSig()
        if not loadersig:
          raise Fatal('Loader signature file is missing; try --loadersig')
        if not Verify(loader, loadersig, key):
          raise Fatal('Loader signing check failed.')
        mtd = GetMtdDevForPartition('cfe')
        is_loader_current = False
        mtdblockname = MTDBLOCK.format(GetMtdNum(mtd))
        with open(mtdblockname, 'r+b') as mtdfile:
          VerbosePrint('Checking if the loader is up to date.')
          loader.seek(loader_start)
          is_loader_current = IsIdentical(loader, mtdfile)
        VerbosePrint('\n')
        if is_loader_current:
          VerbosePrint('The loader is the latest.\n')
        else:
          loader.seek(loader_start, os.SEEK_SET)
          Log('DO NOT INTERRUPT OR POWER CYCLE, or you will brick the unit.\n')
          VerbosePrint('Writing loader to %r', mtd)
          InstallToMtd(loader, mtd)
          VerbosePrint('\n')

  if partition:
    VerbosePrint('Setting boot partition to kernel%d\n', pnum)
    SetBootPartition(pnum)

  return 0


if __name__ == '__main__':
  try:
    sys.exit(main())
  except Fatal, e:
    Log('%s\n', e)
    sys.exit(1)
