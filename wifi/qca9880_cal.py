#!/usr/bin/python -S

"""Check and fix mis-calibrated QCA9880 modules on gfrg200/gfrg210.

   Some modules were delivered to customers mis-calibrated. This script will
   check if the module is affected, and if so, generate a patch that will be
   used after driver reload.
"""
import glob
import os
import os.path
import struct
import experiment
import utils

CAL_EXPERIMENT = 'WifiCalibrationPatch'
PLATFORM_FILE = '/etc/platform'
CALIBRATION_DIR = '/tmp/ath10k_cal'
CAL_PATCH_FILE = 'cal_data_patch.bin'
ATH10K_CAL_DATA = '/sys/kernel/debug/ieee80211/phy[0-9]*/ath10k/cal_data'
OUI_OFFSET = 6
OUI_LEN = 3
VERSION_OFFSET = 45
VERSION_LEN = 3
SUSPECT_OUIS = ((0x28, 0x24, 0xff), (0x48, 0xa9, 0xd2), (0x60, 0x02, 0xb4),
                (0xbc, 0x30, 0x7d), (0xbc, 0x30, 0x7e))
MODULE_PATH = '/sys/class/net/{}/device/driver/module'

# Each tuple starts with an offset, followed by a list of values to be
# patched beginning at that offset.
CAL_PATCH = ((0x050a, (0x5c, 0x68, 0xbd, 0xcd)),
             (0x0510, (0x5c, 0x68, 0xbd, 0xcd)),
             (0x0516, (0x5c, 0x68, 0xbd, 0xcd)),
             (0x051c, (0x5c, 0x68, 0xbd, 0xcd)),
             (0x0531, (0x2a, 0x28, 0x26)),
             (0x0535, (0x2a, 0x28, 0x26)),
             (0x056b, (0xce, 0x8a, 0x66, 0x02, 0x68, 0x26, 0x80, 0x66)),
             (0x05b4, (0x8a, 0x46, 0x02, 0x68, 0x24, 0x80, 0x46)),
             (0x05c0, (0x8a, 0x46, 0x02, 0x68, 0x24, 0x80, 0x46)),
             (0x05fc, (0x8c, 0x68, 0x02, 0x88, 0x26, 0x80)),
             (0x0608, (0x8c, 0x68, 0x02, 0x88, 0x26, 0x80)))

FCC_PATCH = ((0x0625, (0x50, 0x58, 0x5c, 0x8c, 0xbd, 0xc1, 0xcd,
                       0x4c, 0x50, 0x58, 0x5c, 0x8c, 0xbd, 0xc1,
                       0xcd, 0x4e, 0x56, 0x5e, 0x66, 0x8e)),
             (0x06b4, (0x69, 0x6b, 0x6b, 0x62, 0x62, 0x6b, 0x6c,
                       0x2d, 0x69, 0x6b, 0x6b, 0x62, 0x62, 0x6b,
                       0x6d, 0x2d, 0x62, 0x6f, 0x68, 0x64, 0x64,
                       0x68, 0x68, 0x2d, 0x5c, 0x60, 0x60, 0x66)))

experiment.register(CAL_EXPERIMENT)


def _log(msg):
  utils.log('ath10k calibration: {}'.format(msg))


def _is_ath10k(interface):
  """Check if interface is driven by the ath10k driver.

  Args:
    interface: The interface to be checked. eg wlan1

  Returns:
    True if ath10k, otherwise False.
  """
  try:
    return os.readlink(MODULE_PATH.format(interface)).find('ath10k')
  except OSError:
    return False


def _oui_string(oui):
  """Convert OUI from bytes to a string.

  Args:
    oui: OUI in byte format.

  Returns:
    OUI is string format separated by ':'. Eg. 88:dc:96.
  """
  return ':'.join('{:02x}'.format(ord(b)) for b in oui)


def _version_string(version):
  """Convert version from bytes to a string.

  Args:
    version: version in byte format.

  Returns:
    Three byte version string in hex format: 0x00 0x00 0x00
  """

  return ' '.join('0x{:02x}'.format(ord(b)) for b in version)


def _is_module_miscalibrated():
  """Check the QCA8990 module to see if it is improperly calibrated.

  There are two manufacturers of the modules, Senao and Wistron of which only
  Wistron modules are suspect. Wistron provided a list of suspect OUIs
  which are listed in SUSPECT_OUIS.

  The version field must also be checked, starting at offset VERSION_OFFSET.
  If this fields is all zeros, then it is an implicit indication of V01,
  otherwise it contains a version string.

  V01 -- (version field contains 0's) These modules need both calibration and
         FCC power limits patched.
  V02 -- Only FCC power limits need to be patched
  V03 -- No patching required.

  Returns:
    A tuple containing one or both of: fcc, cal. Or None.
    'fcc' -- FCC patching required.
    'cal' -- Calibration data patching required.
    None  -- No patching required.
  """

  try:
    cal_data_path = _ath10k_cal_data_path()
    if cal_data_path is None:
      return None

    with open(cal_data_path, mode='rb') as f:
      f.seek(OUI_OFFSET)
      oui = f.read(OUI_LEN)
      f.seek(VERSION_OFFSET)
      version = struct.unpack('3s', f.read(VERSION_LEN))[0]

  except IOError as e:
    _log('unable to open cal_data {}: {}'.format(cal_data_path, e.strerror))
    return None

  if oui not in (bytearray(s) for s in SUSPECT_OUIS):
    if not _cal_dir_exists():
      _log('OUI {} is properly calibrated.'.format(_oui_string(oui)))
    return None

  # V01 is retroactively represented not by a string, but by 3 0 value bytes.
  if version == '\x00\x00\x00':
    if not _cal_dir_exists():
      _log('version field is V01. CAL + FCC calibration required.')
    return ('fcc', 'cal')

  if version == 'V02':
    if not _cal_dir_exists():
      _log('version field is V02. Only FCC calibration required.')
    return ('fcc',)

  if version == 'V03':
    if not _cal_dir_exists():
      _log('version field is V03. No patching required.')
    return None

  if not _cal_dir_exists():
    _log('version field unknown: {}'.format(version))
  return None


def _cal_dir_exists():
  return os.path.exists(CALIBRATION_DIR)


def _patch_exists():
  return os.path.exists(os.path.join(CALIBRATION_DIR, CAL_PATCH_FILE))


def _create_cal_dir():
  """Create calibration directory.

  Calibration directory contains the calibration patch file.
  If the directory is empty it signals that calibration checks have already
  completed.

  Returns:
    True if directory exists or is created, false if any error.
  """
  try:
    if not os.path.isdir(CALIBRATION_DIR):
      os.makedirs(CALIBRATION_DIR)
      return True
  except OSError as e:
    _log('unable to create calibration dir {}: {}.'.
         format(CALIBRATION_DIR, e.strerror))
    return False

  return True


def _ath10k_cal_data_path():
  """Find the current path to cal data.

  This path encodes the phy number, which is usually phy1, but if the
  driver load order changed or if this runs after a reload, the phy
  number will change.

  Returns:
    Path to cal_data in debugfs.
  """

  return glob.glob(ATH10K_CAL_DATA)[0]


def _apply_patch(msg, cal_data, patch):
  _log(msg)
  for offset, values in patch:
    cal_data[offset:offset + len(values)] = values


def _generate_calibration_patch(calibration_state):
  """Create calibration patch and write to storage.

  Args:
    calibration_state: data from ath10k to be patched.

  Returns:
    True for success or False for failure.
  """
  try:
    with open(_ath10k_cal_data_path(), mode='rb') as f:
      cal_data = bytearray(f.read())
  except IOError as e:
    _log('cal patch: unable to open for read {}: {}.'.
         format(_ath10k_cal_data_path(), e.strerror))
    return False

  # Actual calibration starts here.
  if 'cal' in calibration_state:
    _apply_patch('Applying CAL patch...', cal_data, CAL_PATCH)

  if 'fcc' in calibration_state:
    _apply_patch('Applying FCC patch...', cal_data, FCC_PATCH)

  try:
    patched_file = os.path.join(CALIBRATION_DIR, CAL_PATCH_FILE)
    open(patched_file, 'wb').write(cal_data)
  except IOError as e:
    _log('unable to open for writing {}: {}.'.format(patched_file, e.strerror))
    return False

  return True


def _reload_driver():
  """Reload the ath10k driver so it picks up modified calibration file."""
  ret = utils.subprocess_quiet(('rmmod', 'ath10k_pci'))
  if ret != 0:
    _log('rmmod ath10k_pci failed: {}.'.format(ret))
    return

  ret = utils.subprocess_quiet(('modprobe', 'ath10k_pci'))
  if ret != 0:
    _log('modprobe ath10k_pci failed: {}.'.format(ret))
    return

  _log('reload ath10k driver complete')


def qca8990_calibration():
  """Main QCA8990 calibration check."""

  if not _is_ath10k('wlan1'):
    if not _cal_dir_exists():
      _log('This system does not use ath10k')
    _create_cal_dir()
    return

  if not experiment.enabled(CAL_EXPERIMENT):
    if  _patch_exists():
      os.remove(os.path.join(CALIBRATION_DIR, CAL_PATCH_FILE))
      _reload_driver()
      _log('experiment {} removed. Removed patch and reloaded driver.'.
           format(CAL_EXPERIMENT))
      return
    if not _cal_dir_exists():
      _log('experiment {} not active. Skipping calibration check.'
           .format(CAL_EXPERIMENT))
      _create_cal_dir()
    return

  # Experiment is enabled.

  calibration_state = _is_module_miscalibrated()
  if calibration_state is not None and not _patch_exists():
    _create_cal_dir()
    if _generate_calibration_patch(calibration_state):
      _log('generated new patch.')
      _reload_driver()
    return

  if calibration_state is None:
    if not _cal_dir_exists():
      _log('This system does not need calibration.')
    _create_cal_dir()
    return


if __name__ == '__main__':
  qca8990_calibration()
