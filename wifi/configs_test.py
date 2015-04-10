#!/usr/bin/python -S

"""Tests for configs.py."""

import subprocess

import configs
import experiment
import utils
from wvtest import wvtest


_WPA_SUPPLICANT_CONFIG = """ctrl_interface=/var/run/wpa_supplicant
ap_scan=1
network={
\tssid="some ssid"
\t#psk="some passphrase"
\tpsk=41821f7ca3ea5d85beea7644ed7e0fefebd654177fa06c26fbdfdc3c599a317f
}
"""


@wvtest.wvtest
def generate_wpa_supplicant_config_test():
  if subprocess.call(['which', 'wpa_passphrase']) != 0:
    utils.log(
        'Can\'t test generate_wpa_supplicant_config without wpa_passphrase')
    return

  config = configs.generate_wpa_supplicant_config(
      'some ssid', 'some passphrase')
  wvtest.WVPASSEQ(_WPA_SUPPLICANT_CONFIG, config)


_PHY_INFO = """Wiphy phy0
  max # scan SSIDs: 4
  max scan IEs length: 2257 bytes
  Retry short limit: 7
  Retry long limit: 4
  Coverage class: 0 (up to 0m)
  Device supports RSN-IBSS.
  Device supports AP-side u-APSD.
  Device supports T-DLS.
  Supported Ciphers:
    * WEP40 (00-0f-ac:1)
    * WEP104 (00-0f-ac:5)
    * TKIP (00-0f-ac:2)
    * CCMP (00-0f-ac:4)
    * CMAC (00-0f-ac:6)
  Available Antennas: TX 0x7 RX 0x7
  Configured Antennas: TX 0x7 RX 0x7
  Supported interface modes:
     * IBSS
     * managed
     * AP
     * AP/VLAN
     * WDS
     * monitor
     * P2P-client
     * P2P-GO
  Band 1:
    Capabilities: 0x11ef
      RX LDPC
      HT20/HT40
      SM Power Save disabled
      RX HT20 SGI
      RX HT40 SGI
      TX STBC
      RX STBC 1-stream
      Max AMSDU length: 3839 bytes
      DSSS/CCK HT40
    Maximum RX AMPDU length 65535 bytes (exponent: 0x003)
    Minimum RX AMPDU time spacing: 8 usec (0x06)
    HT TX/RX MCS rate indexes supported: 0-23
    Bitrates (non-HT):
      * 1.0 Mbps
      * 2.0 Mbps (short preamble supported)
      * 5.5 Mbps (short preamble supported)
      * 11.0 Mbps (short preamble supported)
      * 6.0 Mbps
      * 9.0 Mbps
      * 12.0 Mbps
      * 18.0 Mbps
      * 24.0 Mbps
      * 36.0 Mbps
      * 48.0 Mbps
      * 54.0 Mbps
    Frequencies:
      * 2412 MHz [1] (30.0 dBm)
      * 2417 MHz [2] (30.0 dBm)
      * 2422 MHz [3] (30.0 dBm)
      * 2427 MHz [4] (30.0 dBm)
      * 2432 MHz [5] (30.0 dBm)
      * 2437 MHz [6] (30.0 dBm)
      * 2442 MHz [7] (30.0 dBm)
      * 2447 MHz [8] (30.0 dBm)
      * 2452 MHz [9] (30.0 dBm)
      * 2457 MHz [10] (30.0 dBm)
      * 2462 MHz [11] (30.0 dBm)
      * 2467 MHz [12] (disabled)
      * 2472 MHz [13] (disabled)
      * 2484 MHz [14] (disabled)
  Band 2:
    Capabilities: 0x11ef
      RX LDPC
      HT20/HT40
      SM Power Save disabled
      RX HT20 SGI
      RX HT40 SGI
      TX STBC
      RX STBC 1-stream
      Max AMSDU length: 3839 bytes
      DSSS/CCK HT40
    Maximum RX AMPDU length 65535 bytes (exponent: 0x003)
    Minimum RX AMPDU time spacing: 8 usec (0x06)
    HT TX/RX MCS rate indexes supported: 0-23
    Bitrates (non-HT):
      * 6.0 Mbps
      * 9.0 Mbps
      * 12.0 Mbps
      * 18.0 Mbps
      * 24.0 Mbps
      * 36.0 Mbps
      * 48.0 Mbps
      * 54.0 Mbps
    Frequencies:
      * 5180 MHz [36] (17.0 dBm)
      * 5200 MHz [40] (17.0 dBm)
      * 5220 MHz [44] (17.0 dBm)
      * 5240 MHz [48] (17.0 dBm)
      * 5260 MHz [52] (23.0 dBm) (no IR, radar detection)
        DFS state: usable (for 7648 sec)
        DFS CAC time: 60000 ms
      * 5280 MHz [56] (23.0 dBm) (no IR, radar detection)
        DFS state: usable (for 7648 sec)
        DFS CAC time: 60000 ms
      * 5300 MHz [60] (23.0 dBm) (no IR, radar detection)
        DFS state: usable (for 7648 sec)
        DFS CAC time: 60000 ms
      * 5320 MHz [64] (23.0 dBm) (no IR, radar detection)
        DFS state: usable (for 7648 sec)
        DFS CAC time: 60000 ms
      * 5500 MHz [100] (20.0 dBm) (no IR, radar detection)
        DFS state: usable (for 7648 sec)
        DFS CAC time: 60000 ms
      * 5520 MHz [104] (20.0 dBm) (no IR, radar detection)
        DFS state: usable (for 7648 sec)
        DFS CAC time: 60000 ms
      * 5540 MHz [108] (20.0 dBm) (no IR, radar detection)
        DFS state: usable (for 7648 sec)
        DFS CAC time: 60000 ms
      * 5560 MHz [112] (20.0 dBm) (no IR, radar detection)
        DFS state: usable (for 7648 sec)
        DFS CAC time: 60000 ms
      * 5580 MHz [116] (20.0 dBm) (no IR, radar detection)
        DFS state: usable (for 7648 sec)
        DFS CAC time: 60000 ms
      * 5600 MHz [120] (disabled)
      * 5620 MHz [124] (disabled)
      * 5640 MHz [128] (disabled)
      * 5660 MHz [132] (30.0 dBm) (no IR, radar detection)
        DFS state: usable (for 7648 sec)
        DFS CAC time: 60000 ms
      * 5680 MHz [136] (30.0 dBm) (no IR, radar detection)
        DFS state: usable (for 7648 sec)
        DFS CAC time: 60000 ms
      * 5700 MHz [140] (30.0 dBm) (no IR, radar detection)
        DFS state: usable (for 7648 sec)
        DFS CAC time: 60000 ms
      * 5745 MHz [149] (30.0 dBm)
      * 5765 MHz [153] (30.0 dBm)
      * 5785 MHz [157] (30.0 dBm)
      * 5805 MHz [161] (30.0 dBm)
      * 5825 MHz [165] (30.0 dBm)
  Supported commands:
     * new_interface
     * set_interface
     * new_key
     * start_ap
     * new_station
     * set_bss
     * authenticate
     * associate
     * deauthenticate
     * disassociate
     * join_ibss
     * remain_on_channel
     * set_tx_bitrate_mask
     * frame
     * frame_wait_cancel
     * set_wiphy_netns
     * set_channel
     * set_wds_peer
     * tdls_mgmt
     * tdls_oper
     * probe_client
     * set_noack_map
     * register_beacons
     * start_p2p_device
     * set_mcast_rate
     * channel_switch
     * Unknown command (104)
     * connect
     * disconnect
  Supported TX frame types:
     * IBSS: 0x00 0x10 0x20 0x30 0x40 0x50 0x60 0x70 0x80 0x90 0xa0 0xb0 0xc0 0xd0 0xe0 0xf0
     * managed: 0x00 0x10 0x20 0x30 0x40 0x50 0x60 0x70 0x80 0x90 0xa0 0xb0 0xc0 0xd0 0xe0 0xf0
     * AP: 0x00 0x10 0x20 0x30 0x40 0x50 0x60 0x70 0x80 0x90 0xa0 0xb0 0xc0 0xd0 0xe0 0xf0
     * AP/VLAN: 0x00 0x10 0x20 0x30 0x40 0x50 0x60 0x70 0x80 0x90 0xa0 0xb0 0xc0 0xd0 0xe0 0xf0
     * mesh point: 0x00 0x10 0x20 0x30 0x40 0x50 0x60 0x70 0x80 0x90 0xa0 0xb0 0xc0 0xd0 0xe0 0xf0
     * P2P-client: 0x00 0x10 0x20 0x30 0x40 0x50 0x60 0x70 0x80 0x90 0xa0 0xb0 0xc0 0xd0 0xe0 0xf0
     * P2P-GO: 0x00 0x10 0x20 0x30 0x40 0x50 0x60 0x70 0x80 0x90 0xa0 0xb0 0xc0 0xd0 0xe0 0xf0
     * P2P-device: 0x00 0x10 0x20 0x30 0x40 0x50 0x60 0x70 0x80 0x90 0xa0 0xb0 0xc0 0xd0 0xe0 0xf0
  Supported RX frame types:
     * IBSS: 0x40 0xb0 0xc0 0xd0
     * managed: 0x40 0xd0
     * AP: 0x00 0x20 0x40 0xa0 0xb0 0xc0 0xd0
     * AP/VLAN: 0x00 0x20 0x40 0xa0 0xb0 0xc0 0xd0
     * mesh point: 0xb0 0xc0 0xd0
     * P2P-client: 0x40 0xd0
     * P2P-GO: 0x00 0x20 0x40 0xa0 0xb0 0xc0 0xd0
     * P2P-device: 0x40 0xd0
  software interface modes (can always be added):
     * AP/VLAN
     * monitor
  valid interface combinations:
     * #{ managed } <= 2048, #{ AP } <= 8, #{ P2P-client, P2P-GO } <= 1,
       total <= 2048, #channels <= 1, STA/AP BI must match
     * #{ WDS } <= 2048,
       total <= 2048, #channels <= 1, STA/AP BI must match
     * #{ IBSS, AP } <= 1,
       total <= 1, #channels <= 1, STA/AP BI must match, radar detect widths: { 20 MHz (no HT), 20 MHz }

  HT Capability overrides:
     * MCS: ff ff ff ff ff ff ff ff ff ff
     * maximum A-MSDU length
     * supported channel width
     * short GI for 40 MHz
     * max A-MPDU length exponent
     * min MPDU start spacing
  Device supports TX status socket option.
  Device supports HT-IBSS.
  Device supports SAE with AUTHENTICATE command
  Device supports low priority scan.
  Device supports scan flush.
  Device supports AP scan.
  Device supports per-vif TX power setting
  P2P GO supports CT window setting
  Driver supports a userspace MPM
  Device supports active monitor (which will ACK incoming frames)
  Driver/device bandwidth changes during BSS lifetime (AP/GO mode)

"""

_HOSTAPD_CONFIG = """ctrl_interface=/var/run/hostapd
interface=wlan0
bridge=
ssid=TEST_SSID
auth_algs=1
hw_mode=g
channel=1
country_code=US
ieee80211d=1
ieee80211h=1
ieee80211n=1






ht_capab=[HT20][RX-STBC1]

"""

_HOSTAPD_CONFIG_WPA = """wpa=2
wpa_passphrase=asdfqwer
wpa_key_mgmt=WPA-PSK
wpa_pairwise=CCMP
"""


class FakeOptDict(object):
  """A fake options.OptDict containing default values."""
  band = '2.4 5'
  channel = 'auto'
  autotype = 'NONDFS'
  ssid = 'TEST_SSID'
  encryption = 'WPA2_PSK_AES'
  force_restart = False
  hidden_mode = False
  enable_wmm = False
  short_guard_interval = False
  protocols = 'a/b/g/n/ac'
  width = '20'
  bridge = ''
  extra_short_timeout_intervals = False
  persist = False
  interface_suffix = ''


# pylint: disable=protected-access
@wvtest.wvtest
def generate_hostapd_config_test():
  """Tests generate_hostapd_config."""
  # Test a simple case.
  config = configs.generate_hostapd_config(
      _PHY_INFO, 'wlan0', '2.4', '1', '20', set(('a', 'b', 'g', 'n', 'ac')),
      'asdfqwer', FakeOptDict)
  wvtest.WVPASSEQ('\n'.join([_HOSTAPD_CONFIG, _HOSTAPD_CONFIG_WPA]), config)

  # Test with no encryption.
  default_encryption, FakeOptDict.encryption = FakeOptDict.encryption, 'NONE'
  config = configs.generate_hostapd_config(
      _PHY_INFO, 'wlan0', '2.4', '1', '20', set(('a', 'b', 'g', 'n', 'ac')),
      'asdfqwer', FakeOptDict)
  wvtest.WVPASSEQ(_HOSTAPD_CONFIG, config)
  FakeOptDict.encryption = default_encryption

  # Now enable extra short timeout intervals and the Wifi80211k experiment.
  experiment._EXPERIMENTS_TMP_DIR = '/tmp'
  experiment._EXPERIMENTS_DIR = '/tmp'
  open('/tmp/Wifi80211k.available', 'a').close()
  open('/tmp/Wifi80211k.active', 'a').close()
  FakeOptDict.extra_short_timeout_intervals = True
  new_config = '\n'.join((
      '\n'.join([_HOSTAPD_CONFIG, _HOSTAPD_CONFIG_WPA]),
      configs._EXPERIMENT_80211K_TPL.format(interface='wlan0'),
      configs._EXTRA_SHORT_TIMEOUT_INTERVALS_TPL))
  config = configs.generate_hostapd_config(
      _PHY_INFO, 'wlan0', '2.4', '1', '20', set(('a', 'b', 'g', 'n', 'ac')),
      'asdfqwer', FakeOptDict)
  wvtest.WVPASSEQ(new_config, config)


if __name__ == '__main__':
  wvtest.wvtest_main()