#!/usr/bin/python -S

"""Functions related to persisting command line options."""

import ast
import os

import utils


def save_options(program, band, argv, tmp=False):
  """Saves program options.

  Persistence options are stripped before saving to prevent rewriting identical
  options when they are loaded and run.

  Args:
    program: The program for which to save options.
    band: The band for which to save options.
    argv: The options to save.
    tmp: Whether to save options to /tmp or _CONFIG_DIR.
  """
  to_save = {
      'argv': [arg for arg in argv if arg not in ['-P', '--persist']],
      'env': {},
  }

  # Also save important environment variables.
  if program == 'hostapd' and 'WIFI_PSK' in os.environ:
    to_save['env']['WIFI_PSK'] = utils.validate_and_sanitize_psk(
        os.environ['WIFI_PSK'])
  if program == 'wpa_supplicant' and 'WIFI_CLIENT_PSK' in os.environ:
    to_save['env']['WIFI_CLIENT_PSK'] = utils.validate_and_sanitize_psk(
        os.environ['WIFI_CLIENT_PSK'])

  utils.atomic_write(
      utils.get_filename(program, utils.FILENAME_KIND.options, band, tmp=tmp),
      repr(to_save))


def load_options(program, band, tmp):
  """Loads program options.

  Args:
    program: The program for which to load options.
    band: The band for which to load options.
    tmp: Whether to load options from /tmp (i.e. what is currently running) or
      _CONFIG_DIR (the options from last time --persist was set).

  Returns:
    The stored options (which can be passed to wifi._run), or None if the file
    cannot be opened.
  """
  filename = utils.get_filename(program, utils.FILENAME_KIND.options, band,
                                tmp=tmp)
  try:
    with open(filename, 'r') as options_file:
      saved = ast.literal_eval(options_file.read())
      os.environ.update(saved['env'])
      return saved['argv']
  except IOError:
    return None


def delete_options(program, band):
  """Deletes persisted program options from _CONFIG_DIR.

  Args:
    program: The program for which to delete options.
    band: The band for which to delete options.

  Returns:
    Whether deletion succeeded.
  """
  filename = utils.get_filename(program, utils.FILENAME_KIND.options, band)
  if os.path.exists(filename):
    try:
      os.remove(filename)
      utils.log('Removed persisted options for %s GHz %s', band, program)
    except OSError:
      utils.log('Failed to remove persisted options for %s GHz %s',
                band, program)
      return False
  else:
    utils.log('No persisted options to remove for %s GHz %s', band, program)

  return True
