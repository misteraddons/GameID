#! /usr/bin/env python3
'''
GameID: Identify a game using GameDB
'''

# standard imports
from datetime import datetime
from glob import glob
from gzip import decompress as gdecompress
from gzip import open as gopen
from io import BytesIO
from os.path import abspath, expanduser, isdir, isfile
from pickle import loads as ploads
from struct import unpack
from sys import stderr
from zipfile import ZipFile
from zlib import crc32
import sys
import argparse

# GameID constants
VERSION = '1.0.30'
DB_URL = 'https://github.com/niemasd/GameID/raw/main/db.pkl.gz'
DEFAULT_INTERNET_TIMEOUT = 1 # seconds
DEFAULT_BUFSIZE = 1000000
FILE_MODES_GZ = {'rb', 'wb', 'rt', 'wt'}
STRIP_EXT = ['gz'] # list instead of set to iterate in order (just in case)
ISO9660_PVD_MAGIC_WORD = bytes([0x01] + [ord(c) for c in 'CD001'])
ISO9660_DOT_DIRNAMES = {b'\x00', b'\x01'}
MONTH_3LET_TO_FULL = {'JAN': 'January', 'FEB': 'February', 'MAR': 'March', 'APR': 'April', 'MAY': 'May', 'JUN': 'June', 'JUL': 'July', 'AUG': 'August', 'SEP': 'September', 'OCT': 'October', 'NOV': 'November', 'DEC': 'December'}
SAFE = set('-.!0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz')

# GB/GBC constants
GB_CARTRIDGE_TYPES = {0: 'ROM', 1: 'MBC1', 2: 'MBC1 + RAM', 3: 'MBC1 + RAM + Battery', 5: 'MBC2', 6: 'MBC2 + Battery', 8: 'ROM + RAM', 9: 'ROM + RAM + Battery', 11: 'MMM01', 12: 'MMM01 + RAM', 13: 'MMM01 + RAM + Battery', 15: 'MBC3 + Timer + Battery', 16: 'MBC3 + Timer + RAM + Battery', 17: 'MBC3', 18: 'MBC3 + RAM', 19: 'MBC3 + RAM + Battery', 25: 'MBC5', 26: 'MBC5 + RAM', 27: 'MBC5 + RAM + Battery', 28: 'MBC5 + Rumble', 29: 'MBC5 + Rumble + RAM', 30: 'MBC5 + Rumble + RAM + Battery', 32: 'MBC6', 34: 'MBC7 + Sensor + Rumble + RAM + Battery', 252: 'Pocket Camera', 253: 'Bandai TAMA5', 254: 'HuC3', 255: 'HuC1 + RAM + Battery'}
GB_LICENSEE_NEW_CODES = {'00': 'None', '01': 'Nintendo R&D1', '08': 'Capcom', '13': 'Electronic Arts', '18': 'Hudson Soft', '19': 'b-ai', '20': 'kss', '22': 'pow', '24': 'PCM Complete', '25': 'san-x', '28': 'Kemco Japan', '29': 'seta', '30': 'Viacom', '31': 'Nintendo', '32': 'Bandai', '33': 'Ocean/Acclaim', '34': 'Konami', '35': 'Hector', '37': 'Taito', '38': 'Hudson', '39': 'Banpresto', '41': 'Ubi Soft', '42': 'Atlus', '44': 'Malibu', '46': 'angel', '47': 'Bullet-Proof', '49': 'irem', '50': 'Absolute', '51': 'Acclaim', '52': 'Activision', '53': 'American sammy', '54': 'Konami', '55': 'Hi tech entertainment', '56': 'LJN', '57': 'Matchbox', '58': 'Mattel', '59': 'Milton Bradley', '60': 'Titus', '61': 'Virgin', '64': 'LucasArts', '67': 'Ocean', '69': 'Electronic Arts', '70': 'Infogrames', '71': 'Interplay', '72': 'Broderbund', '73': 'sculptured', '75': 'sci', '78': 'THQ', '79': 'Accolade', '80': 'misawa', '83': 'lozc', '86': 'Tokuma Shoten Intermedia', '87': 'Tsukuda Original', '91': 'Chunsoft', '92': 'Video system', '93': 'Ocean/Acclaim', '95': 'Varie', '96': "Yonezawa/s'pal", '97': 'Kaneko', '99': 'Pack in soft', 'A4': 'Konami (Yu-Gi-Oh!)'}
GB_LICENSEE_OLD_CODES = {0: 'None', 1: 'Nintendo', 8: 'Capcom', 9: 'Hot-B', 10: 'Jaleco', 11: 'Coconuts Japan', 12: 'Elite Systems', 19: 'EA (Electronic Arts)', 24: 'Hudsonsoft', 25: 'ITC Entertainment', 26: 'Yanoman', 29: 'Japan Clary', 31: 'Virgin Interactive', 36: 'PCM Complete', 37: 'San-X', 40: 'Kotobuki Systems', 41: 'Seta', 48: 'Infogrames', 49: 'Nintendo', 50: 'Bandai', 51: None, 52: 'Konami', 53: 'HectorSoft', 56: 'Capcom', 57: 'Banpresto', 60: '.Entertainment i', 62: 'Gremlin', 65: 'Ubisoft', 66: 'Atlus', 68: 'Malibu', 70: 'Angel', 71: 'Spectrum Holoby', 73: 'Irem', 74: 'Virgin Interactive', 77: 'Malibu', 79: 'U.S. Gold', 80: 'Absolute', 81: 'Acclaim', 82: 'Activision', 83: 'American Sammy', 84: 'GameTek', 85: 'Park Place', 86: 'LJN', 87: 'Matchbox', 89: 'Milton Bradley', 90: 'Mindscape', 91: 'Romstar', 92: 'Naxat Soft', 93: 'Tradewest', 96: 'Titus', 97: 'Virgin Interactive', 103: 'Ocean Interactive', 105: 'EA (Electronic Arts)', 110: 'Elite Systems', 111: 'Electro Brain', 112: 'Infogrames', 113: 'Interplay', 114: 'Broderbund', 115: 'Sculptered Soft', 117: 'The Sales Curve', 120: 't.hq', 121: 'Accolade', 122: 'Triffix Entertainment', 124: 'Microprose', 127: 'Kemco', 128: 'Misawa Entertainment', 131: 'Lozc', 134: 'Tokuma Shoten Intermedia', 139: 'Bullet-Proof Software', 140: 'Vic Tokai', 142: 'Ape', 143: "I'Max", 145: 'Chunsoft Co.', 146: 'Video System', 147: 'Tsubaraya Productions Co.', 149: 'Varie Corporation', 150: "Yonezawa/S'Pal", 151: 'Kaneko', 153: 'Arc', 154: 'Nihon Bussan', 155: 'Tecmo', 156: 'Imagineer', 157: 'Banpresto', 159: 'Nova', 161: 'Hori Electric', 162: 'Bandai', 164: 'Konami', 166: 'Kawada', 167: 'Takara', 169: 'Technos Japan', 170: 'Broderbund', 172: 'Toei Animation', 173: 'Toho', 175: 'Namco', 176: 'acclaim', 177: 'ASCII or Nexsoft', 178: 'Bandai', 180: 'Square Enix', 182: 'HAL Laboratory', 183: 'SNK', 185: 'Pony Canyon', 186: 'Culture Brain', 187: 'Sunsoft', 189: 'Sony Imagesoft', 191: 'Sammy', 192: 'Taito', 194: 'Kemco', 195: 'Squaresoft', 196: 'Tokuma Shoten Intermedia', 197: 'Data East', 198: 'Tonkinhouse', 200: 'Koei', 201: 'UFL', 202: 'Ultra', 203: 'Vap', 204: 'Use Corporation', 205: 'Meldac', 206: '.Pony Canyon or', 207: 'Angel', 208: 'Taito', 209: 'Sofel', 210: 'Quest', 211: 'Sigma Enterprises', 212: 'ASK Kodansha Co.', 214: 'Naxat Soft', 215: 'Copya System', 217: 'Banpresto', 218: 'Tomy', 219: 'LJN', 221: 'NCS', 222: 'Human', 223: 'Altron', 224: 'Jaleco', 225: 'Towa Chiki', 226: 'Yutaka', 227: 'Varie', 229: 'Epcoh', 231: 'Athena', 232: 'Asmik ACE Entertainment', 233: 'Natsume', 234: 'King Records', 235: 'Atlus', 236: 'Epic/Sony Records', 238: 'IGS', 240: 'A Wave', 243: 'Extreme Entertainment', 255: 'LJN'}
GB_NINTENDO_LOGO = bytes([0xCE, 0xED, 0x66, 0x66, 0xCC, 0x0D, 0x00, 0x0B, 0x03, 0x73, 0x00, 0x83, 0x00, 0x0C, 0x00, 0x0D, 0x00, 0x08, 0x11, 0x1F, 0x88, 0x89, 0x00, 0x0E, 0xDC, 0xCC, 0x6E, 0xE6, 0xDD, 0xDD, 0xD9, 0x99, 0xBB, 0xBB, 0x67, 0x63, 0x6E, 0x0E, 0xEC, 0xCC, 0xDD, 0xDC, 0x99, 0x9F, 0xBB, 0xB9, 0x33, 0x3E])
GB_RAM_SIZE_BANKS = {0: (0, 0), 1: (2048, 1), 2: (8192, 1), 3: (32768, 4), 4: (131072, 16), 5: (65536, 8)}
GB_ROM_SIZE_BANKS = {0: (32768, 2), 1: (65536, 4), 2: (131072, 8), 3: (262144, 16), 4: (524288, 32), 5: (1048576, 64), 6: (2097152, 128), 7: (4194304, 256), 8: (8388608, 512), 82: (1179648, 72), 83: (1310720, 80), 84: (1572864, 96)}

# GBA constants
GBA_NINTENDO_LOGO = bytes([0x24, 0xFF, 0xAE, 0x51, 0x69, 0x9A, 0xA2, 0x21, 0x3D, 0x84, 0x82, 0x0A, 0x84, 0xE4, 0x09, 0xAD, 0x11, 0x24, 0x8B, 0x98, 0xC0, 0x81, 0x7F, 0x21, 0xA3, 0x52, 0xBE, 0x19, 0x93, 0x09, 0xCE, 0x20, 0x10, 0x46, 0x4A, 0x4A, 0xF8, 0x27, 0x31, 0xEC, 0x58, 0xC7, 0xE8, 0x33, 0x82, 0xE3, 0xCE, 0xBF, 0x85, 0xF4, 0xDF, 0x94, 0xCE, 0x4B, 0x09, 0xC1, 0x94, 0x56, 0x8A, 0xC0, 0x13, 0x72, 0xA7, 0xFC, 0x9F, 0x84, 0x4D, 0x73, 0xA3, 0xCA, 0x9A, 0x61, 0x58, 0x97, 0xA3, 0x27, 0xFC, 0x03, 0x98, 0x76, 0x23, 0x1D, 0xC7, 0x61, 0x03, 0x04, 0xAE, 0x56, 0xBF, 0x38, 0x84, 0x00, 0x40, 0xA7, 0x0E, 0xFD, 0xFF, 0x52, 0xFE, 0x03, 0x6F, 0x95, 0x30, 0xF1, 0x97, 0xFB, 0xC0, 0x85, 0x60, 0xD6, 0x80, 0x25, 0xA9, 0x63, 0xBE, 0x03, 0x01, 0x4E, 0x38, 0xE2, 0xF9, 0xA2, 0x34, 0xFF, 0xBB, 0x3E, 0x03, 0x44, 0x78, 0x00, 0x90, 0xCB, 0x88, 0x11, 0x3A, 0x94, 0x65, 0xC0, 0x7C, 0x63, 0x87, 0xF0, 0x3C, 0xAF, 0xD6, 0x25, 0xE4, 0x8B, 0x38, 0x0A, 0xAC, 0x72, 0x21, 0xD4, 0xF8, 0x07])

# GC constants
GC_MAGIC_WORD = bytes([0xc2, 0x33, 0x9f, 0x3d])

# Genesis constants
GENESIS_DEVICE_SUPPORT = {'J': '3-button Controller', '6': '6-button Controller', '0': 'Master System Controller', 'A': 'Analog Joystick', '4': 'Multitap', 'G': 'Lightgun', 'L': 'Activator', 'M': 'Mouse', 'B': 'Trackball', 'T': 'Tablet', 'V': 'Paddle', 'K': 'Keyboard or Keypad', 'R': 'RS-232', 'P': 'Printer', 'C': 'CD-ROM (Sega CD)', 'F': 'Floppy Drive', 'D': 'Download'}
GENESIS_REGION_SUPPORT = {'J': 'Japan', 'U': 'Americas', 'E': 'Europe'}
GENESIS_SOFTWARE_TYPES = {'GM': 'Game', 'AI': 'Aid', 'OS': 'Boot ROM (TMSS)', 'BR': 'Boot ROM (Sega CD)'}
GENESIS_MAGIC_WORDS = [bytes(ord(c) for c in w) for w in ["SEGA GENESIS", "SEGA MEGA DRIVE", "SEGA 32X", "SEGA EVERDRIVE", "SEGA SSF", "SEGA MEGAWIFI", "SEGA PICO", "SEGA TERA68K", "SEGA TERA286"]]

# N64 constants
N64_FIRST_WORD = b'\x80\x37\x12\x40'

# PSX constants
PSX_HEADER = b'\x00\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x00'

# Saturn constants
SATURN_MAGIC_WORD = bytes(ord(c) for c in 'SEGA SEGASATURN')
SATURN_DEVICE_SUPPORT = {'J': 'Joypad', 'M': 'Mouse', 'G': 'Gun', 'W': 'RAM Cart', 'S': 'Steering Wheel', 'A': 'Virtua Stick or Analog Controller', 'E': 'Analog Controller (3D-pad)', 'T': 'Multi-Tap', 'C': 'Link Cable', 'D': 'Link Cable (Direct Link)', 'X': 'X-Band or Netlink Modem', 'K': 'Keyboard', 'Q': 'Pachinko Controller', 'F': 'Floppy Disk Drive', 'R': 'ROM Cart', 'P': 'Video CD Card (MPEG Movie Card)'}
SATURN_TARGET_AREAS = {'J': 'Japan', 'T': 'Asia NTSC (Taiwan, Philippines)', 'U': 'North America (USA, Canada)', 'B': 'Central and South America NTSC (Brazil)', 'K': 'Korea', 'A': 'East Asia PAL (China, Middle and Near East)', 'E': 'Europe PAL', 'L': 'Central and South America PAL'}

# SegaCD constants
SEGACD_MAGIC_WORDS = [bytes(ord(c) for c in w) for w in ['SEGADISCSYSTEM', 'SEGABOOTDISC', 'SEGADISC', 'SEGADATADISC']]

# SNES constants
SNES_LOROM_HEADER_START = 0x7FC0
SNES_HIROM_HEADER_START = 0xFFC0

# Atari 2600 constants
ATARI2600_ROM_SIZES = {
    2048: {'type': '2K', 'banking': 'None'},
    4096: {'type': '4K', 'banking': 'None'},
    8192: {'type': '8K', 'banking': 'F8'},
    16384: {'type': '16K', 'banking': 'F6'},
    32768: {'type': '32K', 'banking': 'F4'},
    10240: {'type': 'DPC', 'banking': 'Pitfall 2'},
    10495: {'type': 'DPC', 'banking': 'Pitfall 2'},
    12288: {'type': 'FA', 'banking': 'RAM+'},
    24576: {'type': 'FA2', 'banking': '24K'},
    65536: {'type': 'Megaboy', 'banking': 'Dynacom'}
}

# Atari 5200 constants
ATARI5200_ROM_SIZES = {
    2048: {'type': '2K', 'cartridge_type': 'BIOS'},
    4096: {'type': '4K', 'cartridge_type': 'Standard'},
    8192: {'type': '8K', 'cartridge_type': 'Standard'},
    16384: {'type': '16K', 'cartridge_type': 'Standard'},
    32768: {'type': '32K', 'cartridge_type': 'Standard'},
    40960: {'type': '40K', 'cartridge_type': 'Special Banking'}
}
ATARI5200_SIGNATURES = [b'\x58\x52', b'\x58\x53', b'\x58\x54']

# Atari 7800 constants
ATARI7800_HEADER_SIZE = 128
ATARI7800_MAGIC = b'ATARI7800'
ATARI7800_CART_TYPES = {
    0x00: 'Standard cartridge',
    0x01: 'Pokey cartridge',
    0x02: 'Supercart bank switched',
    0x04: 'Supercart RAM at $4000',
    0x08: 'ROM at $4000',
    0x10: 'Bank 6 at $4000'
}
ATARI7800_TV_FORMATS = {0: 'NTSC', 1: 'PAL'}
ATARI7800_CONTROLLERS = {
    0: 'None',
    1: 'Joystick',
    2: 'Light Gun',
    3: 'Paddle',
    4: 'Trak-Ball',
    5: 'Joystick (2-button)',
    6: 'Driving Controller',
    7: 'Keypad',
    8: 'ST Mouse',
    9: 'Amiga Mouse'
}

# Atari Jaguar constants
ATARI_JAGUAR_ROM_SIZES = {
    1048576: '1MB',    # 1 MB
    2097152: '2MB',    # 2 MB  
    4194304: '4MB',    # 4 MB
    6291456: '6MB'     # 6 MB (rare)
}

# Atari Lynx constants
ATARI_LYNX_HEADER_SIZE = 64
ATARI_LYNX_MAGIC = b'LYNX'
ATARI_LYNX_ROM_SIZES = {
    32768: '32KB',     # 32 KB
    65536: '64KB',     # 64 KB  
    131072: '128KB',   # 128 KB
    262144: '256KB',   # 256 KB
    524288: '512KB',   # 512 KB
    1048576: '1MB'     # 1 MB
}

# WonderSwan constants
WONDERSWAN_HEADER_SIZE = 10
WONDERSWAN_ROM_SIZES = {
    131072: '128KB',   # 128 KB (1 Mbit)
    262144: '256KB',   # 256 KB (2 Mbit) 
    524288: '512KB',   # 512 KB (4 Mbit)
    1048576: '1MB',    # 1 MB (8 Mbit)
    2097152: '2MB',    # 2 MB (16 Mbit)
    4194304: '4MB',    # 4 MB (32 Mbit)
    8388608: '8MB',    # 8 MB (64 Mbit)
    16777216: '16MB'   # 16 MB (128 Mbit)
}
WONDERSWAN_ORIENTATIONS = {0: 'Horizontal', 1: 'Vertical'}
WONDERSWAN_MAPPER_TYPES = {
    0: 'ROM only',
    1: 'Mapper 1 (SRAM)',
    2: 'Mapper 2 (RTC)',
    3: 'Mapper 3 (SRAM + RTC)',
    4: 'Mapper 4 (EEPROM)',
    5: 'Mapper 5 (EEPROM + RTC)'
}

# ColecoVision constants
COLECOVISION_MAGIC_1 = b'\xAA\x55'
COLECOVISION_MAGIC_2 = b'\x55\xAA'
COLECOVISION_ROM_SIZES = {
    8192: '8KB',       # 8 KB
    16384: '16KB',     # 16 KB
    24576: '24KB',     # 24 KB
    32768: '32KB',     # 32 KB
    49152: '48KB',     # 48 KB
    65536: '64KB'      # 64 KB
}

# PC Engine constants
PCENGINE_ROM_SIZES = {
    32768: '32KB',     # 32 KB (256 Kbit)
    65536: '64KB',     # 64 KB (512 Kbit)
    131072: '128KB',   # 128 KB (1 Mbit)
    262144: '256KB',   # 256 KB (2 Mbit)
    393216: '384KB',   # 384 KB (3 Mbit)
    524288: '512KB',   # 512 KB (4 Mbit)
    786432: '768KB',   # 768 KB (6 Mbit)
    1048576: '1MB',    # 1 MB (8 Mbit)
    1572864: '1.5MB',  # 1.5 MB (12 Mbit)
    2097152: '2MB',    # 2 MB (16 Mbit)
    2621440: '2.5MB'   # 2.5 MB (20 Mbit)
}

# Game Gear constants
GAMEGEAR_TMR_SEGA_MAGIC = b'TMR SEGA'
GAMEGEAR_ROM_SIZES = {
    32768: '32KB',     # 32 KB (256 Kbit)
    65536: '64KB',     # 64 KB (512 Kbit)
    131072: '128KB',   # 128 KB (1 Mbit)
    262144: '256KB',   # 256 KB (2 Mbit)
    524288: '512KB',   # 512 KB (4 Mbit)
    1048576: '1MB'     # 1 MB (8 Mbit)
}
GAMEGEAR_HEADER_LOCATIONS = [0x7FF0, 0x3FF0, 0x1FF0]  # Common header locations

# Master System constants
MASTERSYSTEM_TMR_SEGA_MAGIC = b'TMR SEGA'
MASTERSYSTEM_ROM_SIZES = {
    8192: '8KB',       # 8 KB (64 Kbit)
    16384: '16KB',     # 16 KB (128 Kbit)
    32768: '32KB',     # 32 KB (256 Kbit)
    65536: '64KB',     # 64 KB (512 Kbit)
    131072: '128KB',   # 128 KB (1 Mbit)
    262144: '256KB',   # 256 KB (2 Mbit)
    524288: '512KB',   # 512 KB (4 Mbit)
    1048576: '1MB'     # 1 MB (8 Mbit)
}
MASTERSYSTEM_HEADER_LOCATIONS = [0x7FF0, 0x3FF0, 0x1FF0]  # Common header locations

# Sega 32X constants
SEGA32X_MAGIC = b'SEGA 32X'
SEGA32X_HEADER_OFFSET = 0x100
SEGA32X_ROM_SIZES = {
    131072: '128KB',   # 128 KB (1 Mbit)
    262144: '256KB',   # 256 KB (2 Mbit)
    524288: '512KB',   # 512 KB (4 Mbit)
    1048576: '1MB',    # 1 MB (8 Mbit)
    2097152: '2MB',    # 2 MB (16 Mbit)
    4194304: '4MB',    # 4 MB (32 Mbit)
    8388608: '8MB'     # 8 MB (64 Mbit)
}

# Nintendo FDS constants
NINTENDO_FDS_MAGIC = b'\x01*NINTENDO-HVC*'
NINTENDO_FDS_HEADER_SIZE = 16
NINTENDO_FDS_BLOCK_SIZES = {
    65500: '65500 bytes (standard)',
    131000: '131000 bytes (2-sided)',
    131016: '131016 bytes (2-sided with header)',
    262000: '262000 bytes (4-sided)',
    524000: '524000 bytes (8-sided)'
}

# Sega SG-1000 constants
SEGA_SG1000_ROM_SIZES = {
    8192: '8KB',       # 8 KB
    16384: '16KB',     # 16 KB  
    32768: '32KB',     # 32 KB
    49152: '48KB',     # 48 KB (rare)
    65536: '64KB'      # 64 KB (rare)
}

# recursively iterate using glob
def recursive_glob(fn):
    to_visit = [fn]
    while len(to_visit) != 0:
        curr = to_visit.pop().rstrip('/'); yield curr
        if isdir(curr):
            to_visit += list(glob('%s/*' % curr))

# replacement for os.path.getsize() that should hopefully support /dev/... volumes
def getsize(fn):
    if isdir(fn):
        total = 0
        for curr in recursive_glob(fn):
            if isfile(curr):
                total += getsize(curr)
        return total
    else:
        with open_file(fn, 'rb') as f:
            return f.seek(0, 2)

# print a log message
def print_log(message='', end='\n', file=stderr):
    print(message, end=end, file=file); file.flush()

# print an error message and exit
def error(message, exitcode=1):
    print(message, file=stderr); exit(exitcode)

# check if a file exists and throw an error if it doesn't
def check_exists(fn):
    if not isfile(fn) and not isdir(fn) and not fn.lower().startswith('/dev/'):
        error("File/folder not found: %s" % fn)

# check if a file doesn't exist and throw an error if it does
def check_not_exists(fn):
    if isfile(fn) or isdir(fn):
        error("File/folder exists: %s" % fn)

# open an output text file for writing (automatically handle gzip)
def open_file(fn, mode='rt', bufsize=DEFAULT_BUFSIZE):
    ext = fn.split('.')[-1].strip().lower()

    # standard output/input
    if fn == 'stdout':
        from sys import stdout as f
    elif fn == 'stdin':
        from sys import stdin as f

    # GZIP files
    elif ext == 'gz':
        if mode not in FILE_MODES_GZ:
            error("Invalid gzip file mode: %s" % mode)
        elif 'r' in mode:
            f = gopen(fn, mode)
        elif 'w' in mode:
            f = gopen(fn, mode, compresslevel=9)
        else:
            error("Invalid gzip file mode: %s" % mode)

    # ZIP files
    elif ext == 'zip':
        if 'r' not in mode or 'w' in mode:
            error("Only read mode is supported for gzip files")
        z = ZipFile(fn, 'r'); names = z.namelist()
        if len(names) != 1:
            error("More than 1 file in zip: %s" % fn)
        return z.open(names[0])

    # Regular files
    else:
        f = open(fn, mode, buffering=bufsize)
    return f

# get the (lower-case) extension of a filename
def get_extension(fn):
    fn = fn.strip().lower()
    for ext in STRIP_EXT:
        if fn.endswith('.%s' % ext):
            fn = fn[:-len(ext)-1]
    return fn.split('.')[-1].strip()

# get bins from CUE
def bins_from_cue(fn):
    if get_extension(fn) != 'cue':
        error("Not a CUE file: %s" % fn)
    f_cue = open_file(fn, 'rt')
    bins = ['%s/%s' % ('/'.join(abspath(expanduser(fn)).split('/')[:-1]), l.split('"')[1].strip()) for l in f_cue if l.strip().lower().startswith('file')]
    f_cue.close()
    return bins

# helper class to handle mounted discs / extracted images
class MountedDisc:
    # initialize
    def __init__(self, fn, uuid=None, volume_ID=None, bufsize=DEFAULT_BUFSIZE):
        fn = abspath(expanduser(fn)).rstrip('/')
        if not isdir(fn):
            error("Input must be a directory: %s" % fn)
        self.fn = fn; self.uuid = uuid
        if volume_ID is None:
            self.volume_ID = fn.split('/')[-1].strip()
        else:
            self.volume_ID = volume_ID

    # get system ID
    def get_system_ID(self):
        return None

    # get volume ID
    def get_volume_ID(self):
        return self.volume_ID

    # get publisher ID
    def get_publisher_ID(self):
        return None

    # get data preparer ID
    def get_data_preparer_ID(self):
        return None

    # get UUID (usually YYYY-MM-DD-HH-MM-SS-?? but not always a valid date)
    def get_uuid(self):
        return self.uuid

    # parse filenames as (name, LBA, size) tuples
    def iter_files(self, only_root_dir=True):
        fns = list(); to_visit = [self.fn]
        while len(to_visit) != 0:
            curr = to_visit.pop()
            if isfile(curr):
                fns.append(curr.strip()[len(self.fn)+1:].strip())
            elif isdir(curr) and (curr == self.fn or (not only_root_dir)):
                to_visit += [fn.strip() for fn in glob('%s/*' % curr)]
        fns.sort()
        return [('/%s' % fn, None, getsize('%s/%s' % (self.fn,fn))) for fn in fns] # add '/' to left to be consistent with ISO9660

    # get data from (path,None,None) tuple
    def read_file(self, file_tup):
        with open_file('%s/%s' % (self.fn.rstrip('/'), file_tup[0]), 'rb') as f:
            return f.read()

# helper class to handle ISO 9660 disc images
class ISO9660:
    # initialize ISO handling
    def __init__(self, fn, quiet=False, bufsize=DEFAULT_BUFSIZE):
        if fn.split('.')[-1].strip().lower() in {'7z', 'zip'}:
            if quiet:
                error()
            else:
                error("%s files are not yet supported" % (fn.split('.')[-1].strip().lower()))
        self.fn = abspath(expanduser(fn))
        if fn.lower().endswith('.cue'):
            self.bins = bins_from_cue(fn)
            self.sizes = [getsize(b) for b in self.bins]
            self.size = sum(self.sizes)
            self.f = ISO9660FP(self.bins[0])
        else:
            self.f = ISO9660FP(self.fn)
            self.sizes = [getsize(self.fn)]
            self.size = self.sizes[0]

        # determine block size from just first track
        if (self.sizes[0] % 2352) == 0:
            self.block_size = 2352
        elif (self.sizes[0] % 2048) == 0:
            self.block_size = 2048
        else:
            if quiet:
                error()
            else:
                error("Invalid disc image block size: %s" % fn)

        # load PVD (always starts with 0x01 followed by 'CD0001'): https://wiki.osdev.org/ISO_9660#The_Primary_Volume_Descriptor
        self.pvd = None; header = self.f.read(1000000) # 1000000 is arbitrary; too large = slow if not valid ISO 9660
        for i in range(len(header) - len(ISO9660_PVD_MAGIC_WORD) + 1):
            if header[i : i + len(ISO9660_PVD_MAGIC_WORD)] == ISO9660_PVD_MAGIC_WORD:
                self.block_offset = i - (16 * self.block_size) # this seems to work regardless of block size or console
                self.f.seek(i); self.pvd = self.f.read(self.block_size); break
        if self.pvd is None:
            error("Invalid ISO9660: %s" % fn)

        # load path table: https://wiki.osdev.org/ISO_9660#The_Path_Table
        path_table_size = unpack('<I', self.pvd[132 : 136])[0]
        path_table_lba = unpack('<I', self.pvd[140 : 144])[0]
        self.f.seek(self.block_offset + (path_table_lba * self.block_size))
        path_table_raw = self.f.read(path_table_size)
        self.path_table = list(); i = 0
        while i < len(path_table_raw):
            curr_dir_name_len = path_table_raw[i]
            curr_dir_lba = unpack('<I', path_table_raw[i + 2 : i + 6])[0]
            curr_dir_parent_ind = unpack('<H', path_table_raw[i + 6 : i + 8])[0] - 1 # 1-based indexing --> 0-based
            curr_dir_name = path_table_raw[i + 8 : i + 8 + curr_dir_name_len]
            if curr_dir_name == b'\x00':
                curr_dir_name = ''; curr_dir_parent_ind = None
            else:
                curr_dir_name = curr_dir_name.decode()
            i += (8 + curr_dir_name_len)
            if (i % 2) == 1:
                i += 1 # each table entry starts on an even byte number
            self.path_table.append(('%s/' % curr_dir_name, curr_dir_lba, curr_dir_parent_ind))

    # get system ID
    def get_system_ID(self):
        system_ID = self.pvd[8 : 40]
        try:
            return system_ID.decode().strip()
        except:
            return system_ID

    # get volume ID
    def get_volume_ID(self):
        volume_ID = self.pvd[40 : 72]
        try:
            return volume_ID.decode().strip()
        except:
            return volume_ID

    # get publisher ID
    def get_publisher_ID(self):
        publisher_ID = self.pvd[318 : 446]
        try:
            return publisher_ID.decode().strip()
        except:
            return publisher_ID

    # get data preparer ID
    def get_data_preparer_ID(self):
        data_preparer_ID = self.pvd[446 : 574]
        try:
            return data_preparer_ID.decode().strip()
        except:
            return data_preparer_ID

    # get UUID (usually YYYY-MM-DD-HH-MM-SS-?? but not always a valid date)
    def get_uuid(self):
        # find UUID (usually offset 813 of PVD, but could be different)
        uuid = self.pvd[813 : 829]

        # try to parse as text (if it fails, just return the raw bytes)
        try:
            uuid = uuid.decode()
        except:
            return uuid

        # add dashes to UUID text and return: YYYYMMDDHHMMSS?? --> YYYY-MM-DD-HH-MM-SS-??
        out = uuid[:4]
        for i in range(4, len(uuid), 2):
            out = out + '-' + uuid[i:i+2]
        return out

    # iterate over files as as (path, LBA, size) tuples: https://wiki.osdev.org/ISO_9660#Recursing_from_the_Root_Directory
    def iter_files(self, only_root_dir=True):
        # handle each directory one-by-one
        for dir_name, dir_lba, dir_parent_ind in self.path_table:
            # get full path of current directory
            dir_path = dir_name; tmp_ind = dir_parent_ind
            while tmp_ind is not None:
                dir_path = '%s%s' % (self.path_table[tmp_ind][0], dir_path); tmp_ind = self.path_table[tmp_ind][2]

            # parse directory: https://wiki.osdev.org/ISO_9660#Directories
            self.f.seek(self.block_offset + (self.block_size * dir_lba))
            while True:
                curr_len = self.f.read(1)[0]
                if curr_len == 0:
                    break
                curr_raw = self.f.read(curr_len-1) # already read first byte (curr_len); all indices below are off-by-one as a result
                curr_flags = curr_raw[24]
                if (curr_flags & 0b00000010) != 0:
                    continue # directory, so I'll handle it in the outer for-loop over the path table
                curr_lba = unpack('<I', curr_raw[1 : 5])[0]
                curr_len = unpack('<I', curr_raw[9 : 13])[0]
                curr_fn_len = curr_raw[31]
                curr_path = '%s%s' % (dir_path, curr_raw[32 : 32 + curr_fn_len].decode())
                if (not only_root_dir) or (curr_path.count('/') == 1):
                    yield (curr_path, curr_lba, curr_len)

    # read the data of a given file (path, LBA, size) tuple
    def read_file(self, file_tup):
        path, lba, size = file_tup; self.f.seek(self.block_offset + (self.block_size * lba))
        return self.f.read(size)

# helper class to serve as a file pointer (to support GZIP, weird PSX discs, etc.)
class ISO9660FP:
    # constructor
    def __init__(self, fn, mode='rb', start_offset=0, bufsize=DEFAULT_BUFSIZE):
        self.f = open_file(fn, mode, bufsize=bufsize)
        self.mode = mode; self.start_offset = start_offset

    # seek to offset
    def seek(self, offset, from_what=0):
        if from_what == 0: # reference point is start of file
            offset += self.start_offset
        self.f.seek(offset, from_what)

    # tell current offset
    def tell(self):
        return self.f.tell() - self.start_offset

    # read data
    def read(self, read_size):
        return self.f.read(read_size)

# get args from user interactively
def get_args_interactive(argv):
    # set things up
    print_log("=== GameID v%s ===" % VERSION)
    arg_input = None; arg_console = None

    # get game filename (--input)
    while arg_input is None:
        print_log("Enter game filename (no quotes): ", end='')
        arg_input = input().strip()
        if not isfile(arg_input) and not arg_input.lower().startswith('/dev/'):
            print_log("ERROR: File/folder not found: %s\n" % arg_input); arg_input = None
    argv += ['--input', arg_input]

    # get console (--console)
    while arg_console is None:
        print_log("Enter console (options: %s): " % ', '.join(GAMEID_CONSOLES), end='')
        arg_console = input().replace('"','').replace("'",'').strip().upper()
        if arg_console not in IDENTIFY:
            print_log("ERROR: Invalid console: %s\n" % arg_console); arg_console = None
    argv += ['--console', arg_console]

# parse user arguments
def parse_args():
    # if --version, just print version and exit
    if '--version' in sys.argv:
        print("GameID v%s" % VERSION); exit()

    # run argparse
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-i', '--input', required=True, type=str, help="Input Game File")
    parser.add_argument('-c', '--console', required=True, type=str, help="Console (options: %s)" % ', '.join(GAMEID_CONSOLES))
    parser.add_argument('-d', '--database', required=False, type=str, default=None, help="GameID Database (db.pkl.gz)")
    parser.add_argument('-o', '--output', required=False, type=str, default='stdout', help="Output File")
    parser.add_argument('--disc_uuid', required=False, type=str, default=None, help="Disc UUID (if already known)")
    parser.add_argument('--disc_label', required=False, type=str, default=None, help="Disc Label / Volume ID (if already known)")
    parser.add_argument('--delimiter', required=False, type=str, default='\t', help="Delimiter")
    parser.add_argument('--prefer_gamedb', action="store_true", help="Prefer Metadata in GameDB (rather than metadata loaded from game)")
    parser.add_argument('--version', action="store_true", help="Print GameID Version (%s)" % VERSION)
    args = parser.parse_args()

    # check console
    args.console = args.console.strip().upper()
    check_console(args.console)

    # check input game file
    args.input = abspath(expanduser(args.input))
    check_exists(args.input)

    # check input database file
    if args.database is not None:
        args.database = abspath(expanduser(args.database))
        check_exists(args.database)

    # check output file
    if args.output != 'stdout':
        check_not_exists(args.output)

    # check disc UUID
    if args.disc_uuid is not None:
        args.disc_uuid = args.disc_uuid.strip()

    # check disc label
    if args.disc_label is not None:
        args.disc_label = args.disc_label.strip()

    # all good, so return args
    return args

# load GameID database
def load_db(fn, internet_timeout=DEFAULT_INTERNET_TIMEOUT, bufsize=DEFAULT_BUFSIZE):
    if fn is None:
        try:
            from urllib.request import urlopen; return ploads(gdecompress(urlopen(DB_URL, timeout=internet_timeout).read()))
        except:
            fn = '%s/db.pkl.gz' % '/'.join(abspath(__file__).split('/')[:-1])
    f = open_file(fn, 'rb', bufsize=bufsize); data = f.read(); f.close()
    return ploads(data)

# identify PSP game
def identify_psp(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    # set things up
    if isfile(fn) or fn.lower().startswith('/dev/'):
        iso = ISO9660(fn)
    elif isdir(fn):
        iso = MountedDisc(fn, uuid=user_uuid, volume_ID=user_volume_ID)
    else:
        error("File/folder not found: %s" % fn)
    data = None
    for file_tup in iso.iter_files():
        if file_tup[0].upper() == '/UMD_DATA.BIN':
            data = iso.read_file(file_tup)
    if data is None:
        error("Invalid PSP ISO: %s" % fn)

    # read serial
    serial = ""
    for v in data:
        if v == ord('|'):
            break
        serial += chr(v)
    serial = serial.strip()

    # prepare output
    out = {
        'ID': serial,
        'uuid': iso.get_uuid(),
        'volume_ID': iso.get_volume_ID(),
    }

    # identify game
    if serial in db['PSP']:
        gamedb_entry = db['PSP'][serial]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    return out

# identify PSX/PS2 game
def identify_psx_ps2(fn, db, console, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    # set things up
    if isfile(fn) or fn.lower().startswith('/dev/'):
        iso = ISO9660(fn)
    elif isdir(fn):
        iso = MountedDisc(fn, uuid=user_uuid, volume_ID=user_volume_ID)
    else:
        error("File/folder not found: %s" % fn)
    out = None; serial = None

    # try to find file in root directory with name SXXX_XXX.XX
    root_fns = [root_fn.lstrip('/') for root_fn, file_lba, file_len in iso.iter_files(only_root_dir=True)]
    for i in range(len(root_fns)):
        if ';' in root_fns[i]:
            root_fns[i] = root_fns[i].split(';')[0]
    root_fns_upper = [s.strip().upper() for s in root_fns]
    for prefix in db['GAMEID'][console]['ID_PREFIXES']:
        for root_fn in root_fns_upper:
            if root_fn.startswith(prefix):
                serial = root_fn.replace('.','').replace('-','_')
                if serial not in db[console] and len(serial) > len(prefix): # might have a different delimiter than '-' or '_' (e.g. DQ7 is 'SLUSP012.06)
                    serial = serial[:len(prefix)] + '_' + serial[len(prefix)+1:]
                if serial in db[console]:
                    out = db[console][serial]; break
        if serial is not None:
            break

    # failed to find serial based on file, so try volume ID
    if out is None:
        volume_ID = iso.get_volume_ID()
        if isinstance(volume_ID, str):
            serial = volume_ID.replace('-','_'); num_underscore = serial.count('_')
            if num_underscore == 2:
                serial = '_'.join(serial.split('_')[:2])
            if serial in db[console]:
                out = db[console][serial]

    # failed to find serial based on file or volume ID, so try to identify with filename
    if out is None:
        fn_no_ext = fn.split('/')[-1].strip()
        if fn_no_ext.endswith('.gz'):
            fn_no_ext = fn_no_ext[:-3].strip()
        fn_no_ext = '.'.join(fn_no_ext.split('.')[:-1]).strip()
        if fn_no_ext in db[console]:
            out = db[console][fn_no_ext]

    # finalize output and return
    if out is None:
        out = dict()
    else:
        out['ID'] = serial.replace('_','-')
    for k,v in [('uuid',iso.get_uuid()), ('volume_ID',iso.get_volume_ID())]:
        if v is not None and ((k not in out) or (not prefer_gamedb)):
            out[k] = v
    out['root_files'] = ' / '.join(sorted(root_fns))
    return out

# identify PSX game
def identify_psx(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    return identify_psx_ps2(fn, db, 'PSX', user_uuid=user_uuid, user_volume_ID=user_volume_ID, prefer_gamedb=prefer_gamedb)

# identify PS2 game
def identify_ps2(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    return identify_psx_ps2(fn, db, 'PS2', user_uuid=user_uuid, user_volume_ID=user_volume_ID, prefer_gamedb=prefer_gamedb)

# identify GB/GBC game
def identify_gb_gbc(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    # parse GB/GBC ROM header: https://github.com/niemasd/GameDB-GB/wiki#memory-map
    f = open_file(fn, mode='rb'); data = f.read(); f.close()
    if data[0x0104 : 0x0134] != GB_NINTENDO_LOGO:
        pass # error("Invalid GB/GBC ROM (Nintendo logo mismatch): %s" % fn)
    title = data[0x0134 : 0x013F]; manufacturer_code = data[0x013F : 0x0143]; cgb_flag = data[0x0143]

    # parse CGB flag (whether or not GameBoy Color features are supported)
    if cgb_flag == 0x80:
        cgb_mode = "GBC (supports GB)"
    elif cgb_flag == 0xC0:
        cgb_mode = "GBC only"
    elif (cgb_flag & 0b00001100) != 0:
        cgb_mode = "PGB"
    else: # probably old GB game where this byte is part of title
        cgb_mode = "GB"

    # parse manufacturer code (and potentially expand title if there is none)
    if sum(1 for v in manufacturer_code if ord('A') <= v <= ord('Z')) == 4:
        manufacturer_code = manufacturer_code.decode()
    else:
        title = data[0x0134 : 0x0144]; manufacturer_code = None
    title = bytes([v if ord(' ') <= v <= ord('~') else ord(' ') for v in title]).decode().strip()

    # parse Super GameBoy support
    sgb_support = (data[0x0146] == 0x03)

    # parse cartridge type
    if data[0x0147] in GB_CARTRIDGE_TYPES:
        cartridge_type = GB_CARTRIDGE_TYPES[data[0x0147]]
    else:
        cartridge_type = "Unknown"

    # parse ROM size (bytes) and number of banks
    if data[0x0148] in GB_ROM_SIZE_BANKS:
        rom_size, rom_banks = GB_ROM_SIZE_BANKS[data[0x0148]]
    else:
        rom_size = "Unknown"; rom_banks = "Unknown"

    # parse RAM size (bytes) and number of banks
    if data[0x0149] in GB_RAM_SIZE_BANKS:
        ram_size, ram_banks = GB_RAM_SIZE_BANKS[data[0x0149]]
    else:
        ram_size = "Unknown"; ram_banks = "Unknown"

    # parse licensee code
    if data[0x014B] == 0x33: # new licensee code
        try:
            licensee = GB_LICENSEE_NEW_CODES[data[0x0144 : 0x0146].decode()]
        except: # new licensee code not found
            licensee = "Unknown"
    elif data[0x014B] in GB_LICENSEE_OLD_CODES: # old licensee code
        licensee = GB_LICENSEE_OLD_CODES[data[0x014B]]
    else: # old licensee code not found
        licensee = "Unknown"

    # parse ROM version
    rom_version = data[0x014C]

    # parse expected checksums
    header_checksum_expected = data[0x014D]
    global_checksum_expected = unpack('>H', data[0x014E:0x0150])[0]

    # calculate actual checksums
    header_checksum_actual = 256
    for v in data[0x0134 : 0x014D]:
        header_checksum_actual -= (v+1)
        while header_checksum_actual < 0:
            header_checksum_actual += 256
    global_checksum_actual = sum(v for i,v in enumerate(data) if i not in {0x014E, 0x014F}) % 65536

    # identify game
    gamedb_ID = (title, global_checksum_expected)
    out = {
        'internal_title': title,
        'cgb_mode': cgb_mode,
        'sgb_support': sgb_support,
        'cartridge_type': cartridge_type,
        'rom_size': rom_size,
        'rom_banks': rom_banks,
        'ram_size': ram_size,
        'ram_banks': ram_banks,
        'licensee': licensee,
        'rom_version': rom_version,
        'header_checksum_expected': '0x%s' % hex(header_checksum_expected)[2:].zfill(2),
        'header_checksum_actual': '0x%s' % hex(header_checksum_actual)[2:].zfill(2),
        'global_checksum_expected': '0x%s' % hex(global_checksum_expected)[2:].zfill(4),
        'global_checksum_actual': '0x%s' % hex(global_checksum_actual)[2:].zfill(4),
    }
    if manufacturer_code is not None:
        out['manufacturer_code'] = manufacturer_code
    if gamedb_ID in db['GB_GBC']:
        gamedb_entry = db['GB_GBC'][gamedb_ID]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    else:
        out['title'] = out['internal_title'] # 'title' and 'internal_title' will be the same if game not found in GameDB
    return out

# identify GBA game
def identify_gba(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    # parse GBA ROM header: http://problemkaputt.de/gbatek-gba-cartridge-header.htm
    f = open_file(fn, mode='rb'); data = f.read(192); f.close()
    if data[0x04 : 0xA0] != GBA_NINTENDO_LOGO:
        pass # error("Invalid GBA ROM (Nintendo logo mismatch): %s" % fn)
    title = ''.join(chr(v) for v in data[0xA0 : 0xAC] if ord(' ') <= v <= ord('~')).strip()
    game_code = ''.join(chr(v) for v in data[0xAC : 0xB0] if ord(' ') <= v <= ord('~')).strip()
    maker_code = ''.join(chr(v) for v in data[0xB0 : 0xB2] if ord(' ') <= v <= ord('~')).strip()
    main_unit_code = data[0xB3]
    device_type = data[0xB4]
    software_version = data[0xBC]

    # identify game
    out = {
        'ID': game_code,
        'internal_title': title,
        'maker_code': maker_code,
        'main_unit_code': '0x%s' % hex(main_unit_code)[2:].zfill(2),
        'device_type': '0x%s' % hex(device_type)[2:].zfill(2),
        'software_version': software_version,
    }
    if game_code in db['GBA']:
        gamedb_entry = db['GBA'][game_code]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    else:
        out['title'] = out['internal_title'] # 'title' and 'internal_title' will be the same if game not found in GameDB
    return out

# identify GC game
def identify_gc(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    # parse GC ISO header: https://hitmen.c02.at/files/yagcd/yagcd/chap13.html#sec13
    f = open_file(fn, mode='rb'); header = f.read(0x0440); f.close()
    out = {
        'ID':             header[0x0000 : 0x0004].decode().strip(),
        'maker_code':     header[0x0004 : 0x0006].decode().strip(),
        'disk_ID':        header[0x0006],
        'version':        header[0x0007],
        'internal_title': header[0x0020 : 0x0400].decode().strip(),
    }
    serial = out['ID']

    # identify game
    if serial in db['GC']:
        gamedb_entry = db['GC'][serial]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    else:
        out['title'] = out['internal_title'] # 'title' and 'internal_title' will be the same if game not found in GameDB
    return out

# identify SegaCD game
def identify_segacd(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    # read SegaCD ISO header
    if get_extension(fn) == 'cue':
        f = open_file(bins_from_cue(fn)[0], 'rb')
    else:
        f = open_file(fn, mode='rb')
    header = f.read(0x300); f.close() # 0x300 is arbitrary; too small = won't find SegaCD magic word; must be > 0x20F (length of the header)
    iso = ISO9660(fn)

    # search for header starting offset
    magic_word_ind = None
    for magic_word in SEGACD_MAGIC_WORDS:
        for i in range(len(header) - len(magic_word) + 1):
            if header[i : i + len(magic_word)] == magic_word:
                magic_word_ind = i; break
        if magic_word_ind is not None:
            break
    if magic_word_ind is None:
        return None # fail if magic word not found (in the future, maybe change to default offset?)

    # set up output dictionary
    out = {
        'disc_ID':          header[magic_word_ind + 0x000 : magic_word_ind + 0x010],
        'disc_volume_name': header[magic_word_ind + 0x010 : magic_word_ind + 0x01B],
        'system_name':      header[magic_word_ind + 0x020 : magic_word_ind + 0x02B],
        'build_date':       header[magic_word_ind + 0x050 : magic_word_ind + 0x058],
        'system_type':      header[magic_word_ind + 0x100 : magic_word_ind + 0x110],
        'release_year':     header[magic_word_ind + 0x118 : magic_word_ind + 0x11C],
        'release_month':    header[magic_word_ind + 0x11D : magic_word_ind + 0x120],
        'title_domestic':   header[magic_word_ind + 0x120 : magic_word_ind + 0x150],
        'title_overseas':   header[magic_word_ind + 0x150 : magic_word_ind + 0x180],
        'ID':               header[magic_word_ind + 0x180 : magic_word_ind + 0x190],
        'device_support':   header[magic_word_ind + 0x190 : magic_word_ind + 0x1A0],
        'uuid':             iso.get_uuid(),
        'volume_ID':        iso.get_volume_ID(),
    }

    # try to parse output as strings
    for k in list(out.keys()):
        if isinstance(out[k], bytes):
            try:
                out[k] = out[k].decode().strip()
            except:
                pass

    # handle build date (MMDDYYYY)
    if isinstance(out['build_date'], str):
        out['build_date'] = '%s-%s-%s' % (out['build_date'][4:8], out['build_date'][0:2], out['build_date'][2:4])

    # release year
    try:
        out['release_year'] = int(out['release_year'].decode())
    except:
        pass

    # release month
    try:
        out['release_month'] = out['release_month'].decode().strip()
    except:
        pass
    if out['release_month'] in MONTH_3LET_TO_FULL:
        out['release_month'] = MONTH_3LET_TO_FULL[out['release_month']]

    # device support
    try:
        tmp = list()
        for c in out['device_support']:
            if c in GENESIS_DEVICE_SUPPORT:
                tmp.append(GENESIS_DEVICE_SUPPORT[c])
            else:
                tmp.append(c)
        out['device_support'] = ' / '.join(s for s in sorted(tmp))
    except:
        pass

    # region support
    out['region_support'] = header[magic_word_ind + 0x1F0 : magic_word_ind + 0x1F3]
    try:
        tmp = list()
        for v in out['region_support']:
            if v < ord('!') or v > ord('~'):
                continue
            c = chr(v)
            if c in GENESIS_REGION_SUPPORT:
                tmp.append(GENESIS_REGION_SUPPORT[c])
            else:
                tmp.append(c)
        out['region_support'] = ' / '.join(s for s in sorted(tmp))
    except:
        pass

    # identify game
    serial = out['ID'].replace('#','').replace('-','').replace(' ','').strip()
    if serial in db['SegaCD']:
        gamedb_entry = db['SegaCD'][serial]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    else:
        out['title'] = out['title_overseas'] # 'title' and 'title_overseas' will be the same if game not found in GameDB
    return out

# identify Saturn game
def identify_saturn(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    # read Saturn ISO header
    if get_extension(fn) == 'cue':
        f = open_file(bins_from_cue(fn)[0], 'rb')
    else:
        f = open_file(fn, mode='rb')
    header = f.read(0x100); f.close() # 0x100 is arbitrary; too small = won't find Saturn magic word

    # search for header starting offset
    magic_word_ind = None
    for i in range(len(header) - len(SATURN_MAGIC_WORD) + 1):
        if header[i : i + len(SATURN_MAGIC_WORD)] == SATURN_MAGIC_WORD:
            magic_word_ind = i; break
    if magic_word_ind is None:
        return None # fail if magic word not found (in the future, maybe change to default offset?)

    # set up output dictionary
    out = {
        'manufacturer_ID':     header[magic_word_ind + 0x10 : magic_word_ind + 0x20].decode().strip(),
        'ID':                  header[magic_word_ind + 0x20 : magic_word_ind + 0x2A].decode().strip().split(' ')[0].strip(),
        'version':             header[magic_word_ind + 0x2A : magic_word_ind + 0x30].decode().strip(),
        'device_info':         header[magic_word_ind + 0x38 : magic_word_ind + 0x40].decode().strip(),
    }
    try:
        out['internal_title'] = header[magic_word_ind + 0x60 : magic_word_ind + 0xD0].decode().strip()
    except:
        out['internal_title'] = header[magic_word_ind + 0x60 : magic_word_ind + 0xD0]
    serial = out['ID'].replace('-','').replace(' ','').strip()

    # handle release date
    yyyymmdd = header[magic_word_ind + 0x30 : magic_word_ind + 0x38].decode().strip()
    out['release_date'] = '%s-%s-%s' % (yyyymmdd[0:4], yyyymmdd[4:6], yyyymmdd[6:8])

    # handle device support
    out['device_support'] = list(header[magic_word_ind + 0x50 : magic_word_ind + 0x60].decode().strip())
    for i in range(len(out['device_support'])):
        if out['device_support'][i] in SATURN_DEVICE_SUPPORT:
            out['device_support'][i] = SATURN_DEVICE_SUPPORT[out['device_support'][i]]
    out['device_support'] = ' / '.join(out['device_support'])

    # handle target areas
    out['target_area'] = list(header[magic_word_ind + 0x40 : magic_word_ind + 0x50].decode().strip())
    for i in range(len(out['target_area'])):
        if out['target_area'][i] in SATURN_TARGET_AREAS:
            out['target_area'][i] = SATURN_TARGET_AREAS[out['target_area'][i]]
    out['target_area'] = ' / '.join(out['target_area'])

    # identify game
    if serial in db['Saturn']:
        gamedb_entry = db['Saturn'][serial]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    else:
        out['title'] = out['internal_title'] # 'title' and 'internal_title' will be the same if game not found in GameDB
    return out

# helper function convert N64 data between little-endian and big-endian
def n64_convert_endianness(data):
    if len(data) % 2 != 0:
        error("Can only convert even-length data")
    out = bytearray(len(data))
    for i in range(0, len(data), 2):
        out[i] = data[i+1]; out[i+1] = data[i]
    return out

# identify N64 game
def identify_n64(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    f = open_file(fn, mode='rb'); header = f.read(0x40) # stop before "Boot code/strap"

    # determine endianness from first word: https://en64.shoutwiki.com/wiki/ROM
    first_word_data = header[0 : 4]
    if n64_convert_endianness(first_word_data) == N64_FIRST_WORD: # little-endian, so need to convert to big-endian
        header = n64_convert_endianness(header)
    elif first_word_data != N64_FIRST_WORD: # doesn't match either endianness
        error("Invalid N64 ROM: %s" % fn)

    # parse N64 ROM header: https://en64.shoutwiki.com/wiki/ROM#Cartridge_ROM_Header
    cartridge_ID = header[0x3c : 0x3e]
    country_code, version = header[0x3e : 0x40]

    # identify game
    try:
        serial = '%s%s%s' % (chr(cartridge_ID[0]), chr(cartridge_ID[1]), chr(country_code))
    except:
        error("Invalid N64 ROM (%s %s): %s" % (cartridge_ID, country_code, fn))
    out = {
        'ID': serial,
    }
    internal_name = header[0x20 : 0x34]
    try:
        out['internal_name'] = internal_name.decode().strip()
    except:
        out['internal_name'] = internal_name
    if serial in db['N64']:
        gamedb_entry = db['N64'][serial]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    return out

# identify NES game
def identify_nes(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    # load ROM and calculate CRC32
    f = open_file(fn, mode='rb'); data = f.read(); f.close()
    checksum = crc32(data)

    # identify game
    out = {
        'crc32': hex(checksum)[2:].zfill(8),
    }
    if checksum in db['NES']:
        gamedb_entry = db['NES'][checksum]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    return out

# identify SNES game
def identify_snes(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    # load ROM and remove optional 512-byte header: https://snes.nesdev.org/wiki/ROM_file_formats#Detecting_Headered_ROM
    f = open_file(fn, mode='rb'); data = f.read(); f.close()
    if (len(data) % 1024) == 512:
        data = data[512:]

    # find header start: https://github.com/JonnyWalker/PySNES/blob/13ed51843ef391426ebecae643f955da232dcf33/venv/pysnes/cartrige.py#L71-L83
    checksum = None; header_start =  None
    try:
        for start_addr in [SNES_LOROM_HEADER_START, SNES_HIROM_HEADER_START]:
            # https://github.com/JonnyWalker/PySNES/blob/13ed51843ef391426ebecae643f955da232dcf33/venv/pysnes/cartrige.py#L85-L99
            cs1 = hex(data[start_addr + 30])[2:]
            cs1 = (2 - len(cs1)) * "0" + cs1
            cs2 = hex(data[start_addr + 31])[2:]
            cs2 = (2 - len(cs2)) * "0" + cs2
            checksum = cs2 + cs1
            csc1 = hex(data[start_addr + 28])[2:]
            csc1 = (2 - len(csc1)) * "0" + csc1
            csc2 = hex(data[start_addr + 29])[2:]
            csc2 = (2 - len(csc2)) * "0" + csc2
            checksum_complement = csc2 + csc1
            if (int(checksum, 16) + int(checksum_complement, 16) == 65535):
                header_start = start_addr; break
    except:
        pass
    if header_start is None:
        error("Invalid SNES ROM: %s" % fn)

    # parse SNES ROM header: https://snes.nesdev.org/wiki/ROM_header#Cartridge_header
    header = data[header_start:]
    internal_name = header[0 : 21]; internal_name_hex_string = '0x%s' % ''.join(hex(v)[2:].zfill(2) for v in internal_name)
    developer_ID = header[26]
    rom_version = header[27]

    # https://en.wikibooks.org/wiki/Super_NES_Programming/SNES_memory_map#How_do_I_recognize_the_ROM_type?
    if (header[21] & 0b00010000) == 0:
        fast_slow_rom = 'SlowROM'
    else:
        fast_slow_rom = 'FastROM'
    if (header[21] & 0b00000001) == 0:
        rom_type = "LoROM"
    else:
        rom_type = "HiROM"
    if (header[21] & 0b00000100) != 0:
        rom_type = "Ex%s" % rom_type

    # https://snes.nesdev.org/wiki/ROM_header#$FFD6
    hardware = None
    if header[22] <= 2: # [0x00, 0x01, 0x02]
        hardware = ["ROM", "ROM + RAM", "ROM + RAM + Battery"][header[22]]
    else:
        tmp = hex(header[22]).lower() # $FFD6
        coprocessor = None
        if '3' <= tmp[-1] <= '6': # [0x?3, 0x?4, 0x?5, 0x?6]
            hardware = ["ROM + Coprocessor", "ROM + Coprocessor + RAM", "ROM + Coprocessor + RAM + Battery", "ROM + Coprocessor + Battery"][int(tmp[-1])-3]
        if '0' <= tmp[-2] <= '5': # [0x0?, 0x1?, 0x2?, 0x3?, 0x4?, 0x5?]
            coprocessor = ["DSP", "GSU / SuperFX", "OBC1", "SA-1", "S-DD1", "S-RTC"][int(tmp[-2])]
        elif tmp[-2] == 'e': # 0xe?
            coprocessor = "Super Game Boy / Satellaview"
        elif tmp[-2] == 'f': # 0xf?
            tmp = hex(data[header_start-1]) # $FFBF
            if (tmp[-2] == '0') and ('0' <= tmp[-1] <= '3'): # [0x00, 0x01, 0x02, 0x03]
                coprocessor = ["SPC7110", "ST010 / ST011", "ST018", "CX4"][int(tmp[-1])]
        if hardware is not None and coprocessor is not None:
            hardware = hardware.replace(" + Coprocessor", " + Coprocessor (%s)" % coprocessor)

    # identify game
    gamedb_ID = (developer_ID, internal_name_hex_string, rom_version, int(checksum,16))
    out = {
        'internal_title': internal_name_hex_string,
        'fast_slow_rom': fast_slow_rom,
        'rom_type': rom_type,
        'developer_ID': '0x%s' % hex(developer_ID)[2:].zfill(2),
        'rom_version': rom_version,
        'checksum': '0x%s' % checksum.zfill(4),
    }
    if hardware is not None:
        out['hardware'] = hardware
    if gamedb_ID in db['SNES']:
        gamedb_entry = db['SNES'][gamedb_ID]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    else:
        out['title'] = ''.join(chr(v) if ord(' ') <= v <= ord('~') else ' ' for v in internal_name).strip()
    return out

# identify Genesis game
def identify_genesis(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    # parse Genesis ROM header: https://plutiedev.com/rom-header
    f = open_file(fn, mode='rb'); data = f.read(); f.close()

    # search for header starting offset
    magic_word_ind = None
    for magic_word in GENESIS_MAGIC_WORDS:
        for i in range(0x100, 0x200): # # 0x200 is arbitrary; too big = slow if not a Genesis game
            if data[i : i + len(magic_word)] == magic_word:
                magic_word_ind = i; break
        if magic_word_ind is not None:
            break
    if magic_word_ind is None:
        return None # fail if magic word not found (in the future, maybe change to default offset?)

    # set up output dictionary
    out = {
        'system_type':    data[magic_word_ind + 0x000 : magic_word_ind + 0x010],
        'publisher':      data[magic_word_ind + 0x013 : magic_word_ind + 0x017],
        'release_year':   data[magic_word_ind + 0x018 : magic_word_ind + 0x01C],
        'release_month':  data[magic_word_ind + 0x01D : magic_word_ind + 0x020],
        'title_domestic': data[magic_word_ind + 0x020 : magic_word_ind + 0x050],
        'title_overseas': data[magic_word_ind + 0x050 : magic_word_ind + 0x080],
        'software_type':  data[magic_word_ind + 0x080 : magic_word_ind + 0x082],
        'ID':             data[magic_word_ind + 0x082 : magic_word_ind + 0x08B],
        'revision':       data[magic_word_ind + 0x08C : magic_word_ind + 0x08E],
        'checksum':       hex(unpack('>H', data[magic_word_ind + 0x08E : magic_word_ind + 0x090])[0]),
        'device_support': data[magic_word_ind + 0x090 : magic_word_ind + 0x0A0],
        'rom_start':      hex(unpack('>I', data[magic_word_ind + 0x0A0 : magic_word_ind + 0x0A4])[0]),
        'rom_end':        hex(unpack('>I', data[magic_word_ind + 0x0A4 : magic_word_ind + 0x0A8])[0]),
        'ram_start':      hex(unpack('>I', data[magic_word_ind + 0x0A8 : magic_word_ind + 0x0AC])[0]),
        'ram_end':        hex(unpack('>I', data[magic_word_ind + 0x0AC : magic_word_ind + 0x0B0])[0]),
        'modem_support':  data[magic_word_ind + 0x0BC : magic_word_ind + 0x0C8],
        'region_support': data[magic_word_ind + 0x0F0 : magic_word_ind + 0x0F3],
    }

    # try to parse output as strings
    for k in list(out.keys()):
        if isinstance(out[k], bytes):
            try:
                out[k] = out[k].decode().strip()
            except:
                pass

    # release year
    try:
        out['release_year'] = int(out['release_year'].decode())
    except:
        pass

    # release month
    try:
        out['release_month'] = out['release_month'].decode().strip()
    except:
        pass
    if out['release_month'] in MONTH_3LET_TO_FULL:
        out['release_month'] = MONTH_3LET_TO_FULL[out['release_month']]

    # software type
    if out['software_type'] in GENESIS_SOFTWARE_TYPES:
        out['software_type'] = GENESIS_SOFTWARE_TYPES[out['software_type']]

    # device support
    try:
        tmp = list()
        for c in out['device_support']:
            if c in GENESIS_DEVICE_SUPPORT:
                tmp.append(GENESIS_DEVICE_SUPPORT[c])
            else:
                tmp.append(c)
        out['device_support'] = ' / '.join(s for s in sorted(tmp))
    except:
        pass

    # region support
    try:
        tmp = list()
        for c in out['region_support']:
            if c in GENESIS_REGION_SUPPORT:
                tmp.append(GENESIS_REGION_SUPPORT[c])
            else:
                tmp.append(c)
        out['region_support'] = ' / '.join(s for s in sorted(tmp))
    except:
        pass

    # identify game
    if isinstance(out['ID'], str):
        serial = ''.join(c if c in SAFE else '_' for c in out['ID']).replace('-','')
        if serial in db['Genesis']:
            gamedb_entry = db['Genesis'][serial]
            for k,v in gamedb_entry.items():
                if (k not in out) or prefer_gamedb:
                    out[k] = v
    if 'title' not in out:
        out['title'] = out['title_overseas'] # default to overseas title if not in GameDB
    return out

# identify Neo Geo CD game
def identify_neogeocd(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    # set things up
    if isfile(fn) or fn.lower().startswith('/dev/'):
        iso = ISO9660(fn)
    elif isdir(fn):
        iso = MountedDisc(fn, uuid=user_uuid, volume_ID=user_volume_ID)
    else:
        error("File/folder not found: %s" % fn)
    out = dict()

    # prepare output
    out = {
        'uuid': iso.get_uuid(),
        'volume_ID': iso.get_volume_ID(),
    }
    serial = (out['uuid'], out['volume_ID'])

    # identify game
    gamedb_entry = None
    if serial in db['NeoGeoCD']:
        gamedb_entry = db['NeoGeoCD'][serial]
    elif out['volume_ID'] in db['NeoGeoCD']:
        gamedb_entry = db['NeoGeoCD'][out['volume_ID']]
    if gamedb_entry is not None:
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    return out

# identify Atari 2600 game
def identify_atari2600(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    # load ROM and calculate CRC32
    f = open_file(fn, mode='rb'); data = f.read(); f.close()
    file_size = len(data)
    checksum = crc32(data)
    
    # prepare output with basic information
    out = {
        'crc32': hex(checksum)[2:].zfill(8),
        'file_size': file_size,
    }
    
    # determine ROM type and banking scheme based on file size
    if file_size in ATARI2600_ROM_SIZES:
        rom_info = ATARI2600_ROM_SIZES[file_size]
        out['rom_type'] = rom_info['type']
        out['banking_scheme'] = rom_info['banking']
    else:
        out['rom_type'] = 'Unknown'
        out['banking_scheme'] = 'Unknown'
    
    # check for potential superchip RAM (8K, 16K, 32K ROMs)
    if file_size in [8192, 16384, 32768] and len(data) >= 256:
        first_256_bytes = data[:256]
        if all(b == 0x00 for b in first_256_bytes) or all(b == 0xFF for b in first_256_bytes):
            out['superchip_ram'] = 'Detected'
        else:
            out['superchip_ram'] = 'None'
    else:
        out['superchip_ram'] = 'None'
    
    # identify game from database using CRC32
    if checksum in db['Atari2600']:
        gamedb_entry = db['Atari2600'][checksum]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    
    return out

# identify Atari 5200 game
def identify_atari5200(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    # load ROM and calculate CRC32
    f = open_file(fn, mode='rb'); data = f.read(); f.close()
    file_size = len(data)
    checksum = crc32(data)
    
    # prepare output with basic information
    out = {
        'crc32': hex(checksum)[2:].zfill(8),
        'file_size': file_size,
    }
    
    # verify this is an Atari 5200 ROM by checking signature in last 4 bytes
    if file_size >= 4:
        signature = data[-4:-2]  # Get bytes -4 to -3 (signature pattern)
        valid_signature = any(signature == sig for sig in ATARI5200_SIGNATURES)
        
        if valid_signature:
            out['signature_valid'] = 'Yes'
            # Determine signature type
            if signature == b'\x58\x52':
                out['cartridge_signature'] = 'XR (Standard)'
            elif signature == b'\x58\x53':
                out['cartridge_signature'] = 'XS (Alternative)'
            elif signature == b'\x58\x54':
                out['cartridge_signature'] = 'XT (Special)'
        else:
            out['signature_valid'] = 'No'
            out['cartridge_signature'] = 'Unknown'
    else:
        out['signature_valid'] = 'No'
        out['cartridge_signature'] = 'File too small'
    
    # determine ROM type based on file size
    if file_size in ATARI5200_ROM_SIZES:
        rom_info = ATARI5200_ROM_SIZES[file_size]
        out['rom_type'] = rom_info['type']
        out['cartridge_type'] = rom_info['cartridge_type']
    else:
        out['rom_type'] = 'Unknown'
        out['cartridge_type'] = 'Unknown'
    
    # extract 6502 interrupt vectors from last 6 bytes
    if file_size >= 6:
        vectors = data[-6:]
        out['nmi_vector'] = hex((vectors[1] << 8) | vectors[0])[2:].zfill(4)
        out['reset_vector'] = hex((vectors[3] << 8) | vectors[2])[2:].zfill(4)  
        out['irq_vector'] = hex((vectors[5] << 8) | vectors[4])[2:].zfill(4)
    
    # identify game from database using CRC32
    if checksum in db['Atari5200']:
        gamedb_entry = db['Atari5200'][checksum]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    
    return out

# identify Atari 7800 game
def identify_atari7800(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    # load ROM and calculate CRC32
    f = open_file(fn, mode='rb'); data = f.read(); f.close()
    file_size = len(data)
    checksum = crc32(data)
    
    # prepare output with basic information
    out = {
        'crc32': hex(checksum)[2:].zfill(8),
        'file_size': file_size,
    }
    
    # verify this is an Atari 7800 ROM by checking header
    if file_size < ATARI7800_HEADER_SIZE:
        out['header_valid'] = 'No'
        out['error'] = 'File too small for A78 header'
        return out
    
    # check for A78 header magic word
    header = data[:ATARI7800_HEADER_SIZE]
    magic_word = header[1:10]  # bytes 1-9 contain "ATARI7800"
    
    if magic_word == ATARI7800_MAGIC:
        out['header_valid'] = 'Yes'
        
        # extract header information
        out['header_version'] = header[0]
        out['cart_title'] = header[17:49].rstrip(b'\x00').decode('ascii', errors='ignore').strip()
        
        # data length (4 bytes, little endian)
        data_length = int.from_bytes(header[49:53], byteorder='little')
        out['data_length'] = data_length
        out['rom_size'] = file_size - ATARI7800_HEADER_SIZE
        
        # cart type (2 bytes)
        cart_type = int.from_bytes(header[53:55], byteorder='little')
        out['cart_type_raw'] = hex(cart_type)[2:].zfill(4)
        
        # decode cart type flags
        cart_features = []
        for flag, description in ATARI7800_CART_TYPES.items():
            if cart_type & flag:
                cart_features.append(description)
        out['cart_features'] = ', '.join(cart_features) if cart_features else 'Standard cartridge'
        
        # controller types
        controller1 = header[55] if len(header) > 55 else 0
        controller2 = header[56] if len(header) > 56 else 0
        out['controller1'] = ATARI7800_CONTROLLERS.get(controller1, 'Unknown')
        out['controller2'] = ATARI7800_CONTROLLERS.get(controller2, 'Unknown')
        
        # TV format
        tv_format = header[57] if len(header) > 57 else 0
        out['tv_format'] = ATARI7800_TV_FORMATS.get(tv_format, 'Unknown')
        
        # save data peripheral (version 2+ header)
        if out['header_version'] >= 2 and len(header) > 58:
            out['save_peripheral'] = header[58]
        
    else:
        out['header_valid'] = 'No'
        out['error'] = 'Invalid A78 header magic word'
    
    # identify game from database using CRC32
    if checksum in db['Atari7800']:
        gamedb_entry = db['Atari7800'][checksum]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    
    return out

# identify Atari Jaguar game
def identify_atari_jaguar(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    # load ROM and calculate CRC32
    f = open_file(fn, mode='rb'); data = f.read(); f.close()
    file_size = len(data)
    checksum = crc32(data)
    
    # prepare output with basic information
    out = {
        'crc32': hex(checksum)[2:].zfill(8),
        'file_size': file_size,
    }
    
    # determine ROM size category
    if file_size in ATARI_JAGUAR_ROM_SIZES:
        out['rom_size'] = ATARI_JAGUAR_ROM_SIZES[file_size]
        out['valid_size'] = 'Yes'
    else:
        out['rom_size'] = 'Unknown'
        out['valid_size'] = 'No'
    
    # Atari Jaguar ROMs are raw binary dumps without headers
    # The ROM data starts immediately at the beginning
    out['header_type'] = 'Raw ROM dump'
    
    # Look for possible text strings in the ROM for additional identification
    try:
        # Search for common text patterns in the first 1KB
        search_data = data[:1024].decode('ascii', errors='ignore').lower()
        
        # Look for game-related strings
        if 'atari' in search_data:
            out['contains_atari_text'] = 'Yes'
        else:
            out['contains_atari_text'] = 'No'
            
        if 'jaguar' in search_data:
            out['contains_jaguar_text'] = 'Yes'
        else:
            out['contains_jaguar_text'] = 'No'
            
    except:
        out['contains_atari_text'] = 'Unknown'
        out['contains_jaguar_text'] = 'Unknown'
    
    # identify game from database using CRC32
    if checksum in db['AtariJaguar']:
        gamedb_entry = db['AtariJaguar'][checksum]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    
    return out

# identify Atari Lynx game
def identify_atari_lynx(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    # load ROM data
    f = open_file(fn, mode='rb'); data = f.read(); f.close()
    file_size = len(data)
    
    # prepare output with basic information
    out = {
        'file_size': file_size,
    }
    
    # check if this is an LNX file (with header) or LYX file (raw ROM)
    if data[:4] == ATARI_LYNX_MAGIC:
        # LNX format with 64-byte header
        out['format'] = 'LNX (with header)'
        out['header_size'] = ATARI_LYNX_HEADER_SIZE
        
        # extract header information
        header = data[:ATARI_LYNX_HEADER_SIZE]
        
        # parse cart name (null-terminated string at offset 0x0A)
        cart_name_start = 10
        cart_name_end = cart_name_start
        while cart_name_end < 32 and header[cart_name_end] != 0:
            cart_name_end += 1
        if cart_name_end > cart_name_start:
            out['cart_name'] = header[cart_name_start:cart_name_end].decode('ascii', errors='ignore')
        
        # parse manufacturer (null-terminated string at offset 0x2A)
        manufacturer_start = 42
        manufacturer_end = manufacturer_start
        while manufacturer_end < 64 and header[manufacturer_end] != 0:
            manufacturer_end += 1
        if manufacturer_end > manufacturer_start:
            out['manufacturer'] = header[manufacturer_start:manufacturer_end].decode('ascii', errors='ignore')
        
        # ROM data starts after header
        rom_data = data[ATARI_LYNX_HEADER_SIZE:]
        rom_size = len(rom_data)
        out['rom_size'] = rom_size
        
        # determine ROM size category
        if rom_size in ATARI_LYNX_ROM_SIZES:
            out['rom_size_category'] = ATARI_LYNX_ROM_SIZES[rom_size]
            out['valid_size'] = 'Yes'
        else:
            out['rom_size_category'] = 'Unknown'
            out['valid_size'] = 'No'
        
        # calculate CRC32 of ROM data (excluding header)
        checksum = crc32(rom_data)
        
    else:
        # LYX format (raw ROM dump)
        out['format'] = 'LYX (raw ROM)'
        out['header_size'] = 0
        
        # determine ROM size category
        if file_size in ATARI_LYNX_ROM_SIZES:
            out['rom_size_category'] = ATARI_LYNX_ROM_SIZES[file_size]
            out['valid_size'] = 'Yes'
        else:
            out['rom_size_category'] = 'Unknown'
            out['valid_size'] = 'No'
        
        out['rom_size'] = file_size
        rom_data = data
        
        # calculate CRC32 of ROM data
        checksum = crc32(rom_data)
    
    out['crc32'] = hex(checksum)[2:].zfill(8)
    
    # identify game from database using CRC32 of ROM data
    if checksum in db['AtariLynx']:
        gamedb_entry = db['AtariLynx'][checksum]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    
    return out

# identify WonderSwan/WonderSwan Color game
def identify_wonderswan(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    # load ROM data
    f = open_file(fn, mode='rb'); data = f.read(); f.close()
    file_size = len(data)
    
    # prepare output with basic information
    out = {
        'file_size': file_size,
    }
    
    # determine ROM size category and validate
    if file_size in WONDERSWAN_ROM_SIZES:
        out['rom_size_category'] = WONDERSWAN_ROM_SIZES[file_size]
        out['valid_size'] = 'Yes'
    else:
        out['rom_size_category'] = 'Unknown'
        out['valid_size'] = 'No'
    
    # WonderSwan header is in the last 10 bytes of the ROM
    if file_size >= WONDERSWAN_HEADER_SIZE:
        header = data[-WONDERSWAN_HEADER_SIZE:]
        
        # Parse header fields (based on WonderSwan specifications)
        # Byte 0: Developer ID (high byte)
        # Byte 1: Developer ID (low byte) 
        # Byte 2: Minimum system (0x00 = WonderSwan, 0x01 = WonderSwan Color)
        # Byte 3: Cart type/mapper
        # Byte 4: ROM size code
        # Byte 5: SRAM size code
        # Byte 6: Orientation/speed (bit 0 = orientation, bits 1-3 = speed)
        # Byte 7: RTC flag
        # Byte 8: Checksum (high byte)
        # Byte 9: Checksum (low byte)
        
        developer_id = (header[0] << 8) | header[1]
        out['developer_id'] = f'0x{developer_id:04X}'
        
        min_system = header[2]
        if min_system == 0x00:
            out['min_system'] = 'WonderSwan (Mono)'
        elif min_system == 0x01:
            out['min_system'] = 'WonderSwan Color'
        else:
            out['min_system'] = f'Unknown (0x{min_system:02X})'
        
        cart_type = header[3]
        if cart_type in WONDERSWAN_MAPPER_TYPES:
            out['mapper_type'] = WONDERSWAN_MAPPER_TYPES[cart_type]
        else:
            out['mapper_type'] = f'Unknown (0x{cart_type:02X})'
        
        rom_size_code = header[4]
        out['rom_size_code'] = f'0x{rom_size_code:02X}'
        
        sram_size_code = header[5]
        out['sram_size_code'] = f'0x{sram_size_code:02X}'
        
        orientation_speed = header[6]
        orientation = orientation_speed & 0x01
        speed = (orientation_speed >> 1) & 0x07
        
        if orientation in WONDERSWAN_ORIENTATIONS:
            out['orientation'] = WONDERSWAN_ORIENTATIONS[orientation]
        else:
            out['orientation'] = 'Unknown'
        out['speed'] = speed
        
        rtc_flag = header[7]
        out['rtc_present'] = 'Yes' if rtc_flag != 0 else 'No'
        
        checksum = header[8] | (header[9] << 8)  # little-endian
        out['header_checksum'] = f'0x{checksum:04X}'
        
        # Verify checksum (sum of all ROM bytes except checksum should equal checksum)
        calculated_checksum = sum(data[:-2]) & 0xFFFF
        out['calculated_checksum'] = f'0x{calculated_checksum:04X}'
        out['checksum_valid'] = 'Yes' if calculated_checksum == checksum else 'No'
    
    # Calculate CRC32 of entire ROM for database lookup
    checksum = crc32(data)
    out['crc32'] = hex(checksum)[2:].zfill(8)
    
    # Check file extension to determine system type
    ext = get_extension(fn).lower()
    if ext == 'ws':
        system_type = 'WonderSwan'
    elif ext == 'wsc':
        system_type = 'WonderSwanColor'
    else:
        system_type = 'WonderSwan'  # default
    
    # Identify game from database using CRC32
    if system_type in db and checksum in db[system_type]:
        gamedb_entry = db[system_type][checksum]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    
    return out

# identify ColecoVision game
def identify_colecovision(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    # load ROM data
    f = open_file(fn, mode='rb'); data = f.read(); f.close()
    file_size = len(data)
    
    # prepare output with basic information
    out = {
        'file_size': file_size,
    }
    
    # determine ROM size category and validate
    if file_size in COLECOVISION_ROM_SIZES:
        out['rom_size_category'] = COLECOVISION_ROM_SIZES[file_size]
        out['valid_size'] = 'Yes'
    else:
        out['rom_size_category'] = 'Unknown'
        out['valid_size'] = 'No'
    
    # Check for ColecoVision signature (0xAA55 or 0x55AA at start)
    if len(data) >= 2 and (data[:2] == COLECOVISION_MAGIC_1 or data[:2] == COLECOVISION_MAGIC_2):
        out['signature_valid'] = 'Yes'
        
        # ColecoVision ROM header structure:
        # 0x0000-0x0001: Signature (0xAA55)
        # 0x0002-0x0007: Padding (usually 0x00)
        # 0x0008-0x0009: Start address pointer
        # 0x000A-0x001F: RST vectors (interrupts)
        
        if len(data) >= 10:
            # Extract start address (little-endian at offset 0x08)
            start_addr = data[8] | (data[9] << 8)
            out['start_address'] = f'0x{start_addr:04X}'
        
        # Look for title string in ROM (typically appears early in ROM)
        try:
            # Search for ASCII text in first 1KB that might be the title
            search_data = data[:1024]
            
            # Find printable ASCII strings of reasonable length
            title_candidates = []
            current_string = ""
            for i, byte in enumerate(search_data):
                if 32 <= byte <= 126:  # printable ASCII
                    current_string += chr(byte)
                else:
                    if len(current_string) >= 6:  # reasonable title length
                        title_candidates.append(current_string)
                    current_string = ""
            
            # Add final string if it exists
            if len(current_string) >= 6:
                title_candidates.append(current_string)
            
            # Filter for likely title strings (avoid common assembly patterns)
            filtered_titles = []
            for title in title_candidates[:5]:  # check first 5 candidates
                # Skip strings that look like assembly code or common patterns
                if not any(pattern in title.upper() for pattern in ['RST', 'NOP', 'JP', 'CALL', 'RET', 'LD', 'INC', 'DEC']):
                    filtered_titles.append(title)
            
            if filtered_titles:
                out['potential_title'] = filtered_titles[0]
        
        except:
            pass
            
    else:
        out['signature_valid'] = 'No'
    
    # Calculate CRC32 of entire ROM for database lookup
    checksum = crc32(data)
    out['crc32'] = hex(checksum)[2:].zfill(8)
    
    # Identify game from database using CRC32
    if checksum in db['ColecoVision']:
        gamedb_entry = db['ColecoVision'][checksum]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    
    return out

# identify PC Engine/TurboGrafx-16 game
def identify_pcengine(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    # load ROM data
    f = open_file(fn, mode='rb'); data = f.read(); f.close()
    file_size = len(data)
    
    # prepare output with basic information
    out = {
        'file_size': file_size,
    }
    
    # determine ROM size category and validate
    if file_size in PCENGINE_ROM_SIZES:
        out['rom_size_category'] = PCENGINE_ROM_SIZES[file_size]
        out['valid_size'] = 'Yes'
    else:
        out['rom_size_category'] = 'Unknown'
        out['valid_size'] = 'No'
    
    # PC Engine ROMs are raw binary dumps without standard headers
    # We can try to detect some patterns or characteristics
    out['format'] = 'Raw ROM dump'
    
    # Check file extension to determine system type
    ext = get_extension(fn).lower()
    if ext == 'pce':
        system_type = 'PCEngine'
    elif ext == 'sgx':
        system_type = 'PCEngineSuperGrafx'
        out['system_variant'] = 'SuperGrafx'
    else:
        system_type = 'PCEngine'  # default
    
    # Look for potential game characteristics in the ROM
    try:
        # PC Engine uses 6502-based HuC6280 CPU
        # Common patterns: interrupt vectors, initialization code
        
        # Check for common PC Engine initialization patterns
        search_data = data[:1024]  # first 1KB
        
        # Look for common 6502/HuC6280 opcodes and patterns
        common_opcodes = [0x78, 0xD8, 0xA9, 0x8D]  # SEI, CLD, LDA #, STA abs
        opcode_count = sum(1 for byte in search_data[:100] if byte in common_opcodes)
        out['cpu_pattern_score'] = opcode_count
        
        # Look for text strings that might indicate PC Engine games
        text_search = data[:2048].decode('ascii', errors='ignore').upper()
        pc_engine_indicators = ['HUDSON', 'NEC', 'TURBO', 'PCE']
        found_indicators = [indicator for indicator in pc_engine_indicators if indicator in text_search]
        if found_indicators:
            out['detected_indicators'] = ', '.join(found_indicators)
        
    except:
        pass
    
    # Calculate CRC32 of entire ROM for database lookup
    checksum = crc32(data)
    out['crc32'] = hex(checksum)[2:].zfill(8)
    
    # Identify game from database using CRC32
    if system_type in db and checksum in db[system_type]:
        gamedb_entry = db[system_type][checksum]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    
    return out

# identify Game Gear game
def identify_gamegear(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    # load ROM data
    f = open_file(fn, mode='rb'); data = f.read(); f.close()
    file_size = len(data)
    
    # prepare output with basic information
    out = {
        'file_size': file_size,
    }
    
    # determine ROM size category and validate
    if file_size in GAMEGEAR_ROM_SIZES:
        out['rom_size_category'] = GAMEGEAR_ROM_SIZES[file_size]
        out['valid_size'] = 'Yes'
    else:
        out['rom_size_category'] = 'Unknown'
        out['valid_size'] = 'No'
    
    # Look for TMR SEGA header at common locations
    header_found = False
    header_location = None
    
    for location in GAMEGEAR_HEADER_LOCATIONS:
        if location < file_size and location + 16 <= file_size:
            if data[location:location + 8] == GAMEGEAR_TMR_SEGA_MAGIC:
                header_found = True
                header_location = location
                break
    
    if header_found:
        out['header_found'] = 'Yes'
        out['header_location'] = f'0x{header_location:04X}'
        
        # Parse TMR SEGA header (16 bytes total)
        header = data[header_location:header_location + 16]
        
        # Bytes 0-7: "TMR SEGA" signature
        # Bytes 8-9: Reserved (usually 0x0000)
        # Bytes 10-11: Checksum
        # Bytes 12: Product code (BCD) - tens digit
        # Bytes 13: Product code (BCD) - units and version
        # Bytes 14: Region/ROM size code
        # Bytes 15: Reserved
        
        # Extract checksum
        checksum = (header[10] | (header[11] << 8))
        out['header_checksum'] = f'0x{checksum:04X}'
        
        # Extract product code
        product_code_tens = header[12] >> 4
        product_code_units = header[12] & 0x0F
        version = header[13] >> 4
        product_code_lower = header[13] & 0x0F
        
        if product_code_tens < 10 and product_code_units < 10 and product_code_lower < 10:
            product_code = product_code_tens * 1000 + product_code_units * 100 + product_code_lower * 10 + version
            out['product_code'] = f'{product_code:04d}'
            out['version'] = version
        
        # Extract region/ROM size info
        region_rom_size = header[14]
        
        # Region bits (upper 4 bits)
        region_code = (region_rom_size >> 4) & 0x0F
        region_map = {
            3: 'SMS Japan',
            4: 'SMS Export',
            5: 'Game Gear Japan',
            6: 'Game Gear Export',
            7: 'Game Gear International'
        }
        
        if region_code in region_map:
            out['region'] = region_map[region_code]
        else:
            out['region'] = f'Unknown (0x{region_code:X})'
        
        # ROM size bits (lower 4 bits)
        rom_size_code = region_rom_size & 0x0F
        rom_size_map = {
            0xA: '8KB',   0xB: '16KB',  0xC: '32KB',  0xD: '48KB',
            0xE: '64KB',  0xF: '128KB', 0x0: '256KB', 0x1: '512KB',
            0x2: '1MB'
        }
        
        if rom_size_code in rom_size_map:
            out['header_rom_size'] = rom_size_map[rom_size_code]
        else:
            out['header_rom_size'] = f'Unknown (0x{rom_size_code:X})'
        
        # Verify header checksum (simple sum of all ROM bytes except checksum)
        calculated_checksum = 0
        for i in range(file_size):
            if i < header_location + 10 or i >= header_location + 12:  # skip checksum bytes
                calculated_checksum = (calculated_checksum + data[i]) & 0xFFFF
        
        out['calculated_checksum'] = f'0x{calculated_checksum:04X}'
        out['checksum_valid'] = 'Yes' if calculated_checksum == checksum else 'No'
        
    else:
        out['header_found'] = 'No'
    
    # Calculate CRC32 of entire ROM for database lookup
    checksum = crc32(data)
    out['crc32'] = hex(checksum)[2:].zfill(8)
    
    # Identify game from database using CRC32
    if checksum in db['GameGear']:
        gamedb_entry = db['GameGear'][checksum]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    
    return out

# identify Master System game
def identify_mastersystem(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    # load ROM data
    f = open_file(fn, mode='rb'); data = f.read(); f.close()
    file_size = len(data)
    
    # prepare output with basic information
    out = {
        'file_size': file_size,
    }
    
    # determine ROM size category and validate
    if file_size in MASTERSYSTEM_ROM_SIZES:
        out['rom_size_category'] = MASTERSYSTEM_ROM_SIZES[file_size]
        out['valid_size'] = 'Yes'
    else:
        out['rom_size_category'] = 'Unknown'
        out['valid_size'] = 'No'
    
    # Look for TMR SEGA header at common locations
    header_found = False
    header_location = None
    
    for location in MASTERSYSTEM_HEADER_LOCATIONS:
        if location < file_size and location + 16 <= file_size:
            if data[location:location + 8] == MASTERSYSTEM_TMR_SEGA_MAGIC:
                header_found = True
                header_location = location
                break
    
    if header_found:
        out['header_found'] = 'Yes'
        out['header_location'] = f'0x{header_location:04X}'
        
        # Parse TMR SEGA header (16 bytes total)
        header = data[header_location:header_location + 16]
        
        # Bytes 0-7: "TMR SEGA" signature  
        # Bytes 8-9: Reserved (usually 0x2020 for SMS)
        # Bytes 10-11: Checksum
        # Bytes 12: Product code (BCD) - tens digit
        # Bytes 13: Product code (BCD) - units and version
        # Bytes 14: Region/ROM size code
        # Bytes 15: Reserved
        
        # Extract checksum
        checksum = (header[10] | (header[11] << 8))
        out['header_checksum'] = f'0x{checksum:04X}'
        
        # Extract product code (same format as Game Gear)
        product_code_tens = header[12] >> 4
        product_code_units = header[12] & 0x0F
        version = header[13] >> 4
        product_code_lower = header[13] & 0x0F
        
        if product_code_tens < 10 and product_code_units < 10 and product_code_lower < 10:
            product_code = product_code_tens * 1000 + product_code_units * 100 + product_code_lower * 10 + version
            out['product_code'] = f'{product_code:04d}'
            out['version'] = version
        
        # Extract region/ROM size info
        region_rom_size = header[14]
        
        # Region bits (upper 4 bits)
        region_code = (region_rom_size >> 4) & 0x0F
        region_map = {
            3: 'SMS Japan',
            4: 'SMS Export',
            5: 'Game Gear Japan',
            6: 'Game Gear Export', 
            7: 'Game Gear International'
        }
        
        if region_code in region_map:
            out['region'] = region_map[region_code]
        else:
            out['region'] = f'Unknown (0x{region_code:X})'
        
        # ROM size bits (lower 4 bits)
        rom_size_code = region_rom_size & 0x0F
        rom_size_map = {
            0xA: '8KB',   0xB: '16KB',  0xC: '32KB',  0xD: '48KB',
            0xE: '64KB',  0xF: '128KB', 0x0: '256KB', 0x1: '512KB',
            0x2: '1MB'
        }
        
        if rom_size_code in rom_size_map:
            out['header_rom_size'] = rom_size_map[rom_size_code]
        else:
            out['header_rom_size'] = f'Unknown (0x{rom_size_code:X})'
        
        # Verify header checksum (simple sum of all ROM bytes except checksum)
        calculated_checksum = 0
        for i in range(file_size):
            if i < header_location + 10 or i >= header_location + 12:  # skip checksum bytes
                calculated_checksum = (calculated_checksum + data[i]) & 0xFFFF
        
        out['calculated_checksum'] = f'0x{calculated_checksum:04X}'
        out['checksum_valid'] = 'Yes' if calculated_checksum == checksum else 'No'
        
    else:
        out['header_found'] = 'No'
        # Many Master System ROMs don't have headers, this is normal
    
    # Calculate CRC32 of entire ROM for database lookup
    checksum = crc32(data)
    out['crc32'] = hex(checksum)[2:].zfill(8)
    
    # Identify game from database using CRC32
    if checksum in db['MasterSystem']:
        gamedb_entry = db['MasterSystem'][checksum]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    
    return out

# identify Sega 32X game
def identify_sega32x(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    # load ROM data
    f = open_file(fn, mode='rb'); data = f.read(); f.close()
    file_size = len(data)
    
    # prepare output with basic information
    out = {
        'file_size': file_size,
    }
    
    # determine ROM size category and validate
    if file_size in SEGA32X_ROM_SIZES:
        out['rom_size_category'] = SEGA32X_ROM_SIZES[file_size]
        out['valid_size'] = 'Yes'
    else:
        out['rom_size_category'] = 'Unknown'
        out['valid_size'] = 'No'
    
    # Check for Sega 32X header at standard Genesis location (0x100)
    if file_size > SEGA32X_HEADER_OFFSET + 16:
        header_data = data[SEGA32X_HEADER_OFFSET:SEGA32X_HEADER_OFFSET + 8]
        
        if header_data == SEGA32X_MAGIC:
            out['header_found'] = 'Yes'
            out['console_name'] = header_data.decode('ascii', errors='ignore')
            
            # Extract Genesis-style header information (32X uses Genesis header format)
            # 0x100-0x10F: Console name "SEGA 32X"
            # 0x110-0x11F: Copyright notice
            # 0x120-0x14F: Domestic title
            # 0x150-0x17F: International title  
            # 0x180-0x18D: Serial number
            # 0x18E-0x18F: Checksum
            # 0x190-0x19F: Device support
            # 0x1A0-0x1A7: ROM start/end addresses
            # 0x1A8-0x1AF: RAM start/end addresses
            # 0x1F0-0x1FF: Region support
            
            header_end = min(file_size, SEGA32X_HEADER_OFFSET + 256)
            full_header = data[SEGA32X_HEADER_OFFSET:header_end]
            
            # Extract copyright notice (0x110-0x11F)
            if len(full_header) >= 32:
                copyright_data = full_header[16:32]
                copyright_str = copyright_data.decode('ascii', errors='ignore').strip()
                if copyright_str:
                    out['copyright'] = copyright_str
            
            # Extract domestic title (0x120-0x14F)
            if len(full_header) >= 80:
                domestic_title = full_header[32:80].decode('ascii', errors='ignore').strip()
                if domestic_title:
                    out['domestic_title'] = domestic_title
            
            # Extract international title (0x150-0x17F)
            if len(full_header) >= 128:
                intl_title = full_header[80:128].decode('ascii', errors='ignore').strip()
                if intl_title:
                    out['international_title'] = intl_title
            
            # Extract serial number (0x180-0x18D)
            if len(full_header) >= 142:
                serial = full_header[128:142].decode('ascii', errors='ignore').strip()
                if serial:
                    out['serial_number'] = serial
            
            # Extract checksum (0x18E-0x18F)
            if len(full_header) >= 144:
                checksum_bytes = full_header[142:144]
                checksum = (checksum_bytes[0] << 8) | checksum_bytes[1]
                out['header_checksum'] = f'0x{checksum:04X}'
            
            # Extract region support (0x1F0-0x1FF)
            if len(full_header) >= 256:
                region_data = full_header[240:256].decode('ascii', errors='ignore').strip()
                if region_data:
                    out['region_support'] = region_data
                    
                    # Decode common region codes
                    regions = []
                    if 'J' in region_data:
                        regions.append('Japan')
                    if 'U' in region_data:
                        regions.append('USA')
                    if 'E' in region_data:
                        regions.append('Europe')
                    if regions:
                        out['regions'] = ', '.join(regions)
        else:
            out['header_found'] = 'No'
    else:
        out['header_found'] = 'No'
    
    # Calculate CRC32 of entire ROM for database lookup
    checksum = crc32(data)
    out['crc32'] = hex(checksum)[2:].zfill(8)
    
    # Identify game from database using CRC32
    if checksum in db['Sega32X']:
        gamedb_entry = db['Sega32X'][checksum]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    
    return out

# identify Nintendo FDS game
def identify_nintendo_fds(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    # load ROM data
    f = open_file(fn, mode='rb'); data = f.read(); f.close()
    file_size = len(data)
    
    # prepare output with basic information
    out = {
        'file_size': file_size,
    }
    
    # determine disk size category
    if file_size in NINTENDO_FDS_BLOCK_SIZES:
        out['disk_size_category'] = NINTENDO_FDS_BLOCK_SIZES[file_size]
        out['valid_size'] = 'Yes'
    else:
        out['disk_size_category'] = 'Unknown'
        out['valid_size'] = 'No'
    
    # Check for Nintendo FDS header signature
    if len(data) >= len(NINTENDO_FDS_MAGIC):
        if data[:len(NINTENDO_FDS_MAGIC)] == NINTENDO_FDS_MAGIC:
            out['header_found'] = 'Yes'
            out['format'] = 'FDS disk image'
            
            # Parse FDS disk header (Block 1 - Disk Info Block)
            if len(data) >= 56:
                # Disk info starts after the signature
                header = data[15:]  # Skip signature
                
                # Manufacturer ID (1 byte at offset 15)
                manufacturer_id = header[0] if len(header) > 0 else 0
                out['manufacturer_id'] = f'0x{manufacturer_id:02X}'
                
                # Game name (3 bytes at offset 16-18)
                if len(header) >= 4:
                    game_name_bytes = header[1:4]
                    game_name = ''.join([chr(b) if 32 <= b <= 126 else '?' for b in game_name_bytes])
                    out['game_name_code'] = game_name
                
                # Version (1 byte at offset 19)
                if len(header) >= 5:
                    version = header[4]
                    out['version'] = version
                
                # Disk side (1 byte at offset 20)
                if len(header) >= 6:
                    disk_side = header[5]
                    out['disk_side'] = disk_side
                    out['disk_side_desc'] = 'Side A' if disk_side == 0 else 'Side B'
                
                # Disk number (1 byte at offset 21)
                if len(header) >= 7:
                    disk_number = header[6]
                    out['disk_number'] = disk_number
                
                # Actual disk sides (1 byte at offset 22)
                if len(header) >= 8:
                    actual_disk_sides = header[7]
                    out['actual_disk_sides'] = actual_disk_sides
                
                # Boot file ID (1 byte at offset 23)
                if len(header) >= 9:
                    boot_file_id = header[8]
                    out['boot_file_id'] = boot_file_id
                
                # Manufacturing date (5 bytes at offset 31-35)
                if len(header) >= 21:
                    mfg_date_bytes = header[16:21]
                    # Convert from BCD format
                    try:
                        year = ((mfg_date_bytes[0] >> 4) * 10 + (mfg_date_bytes[0] & 0x0F)) + 1925
                        month = (mfg_date_bytes[1] >> 4) * 10 + (mfg_date_bytes[1] & 0x0F)
                        day = (mfg_date_bytes[2] >> 4) * 10 + (mfg_date_bytes[2] & 0x0F)
                        if 1 <= month <= 12 and 1 <= day <= 31:
                            out['manufacturing_date'] = f'{year:04d}-{month:02d}-{day:02d}'
                    except:
                        pass
                
                # Look for disk manufacturer name in header
                if len(data) >= 100:
                    # Search for common FDS manufacturer strings
                    search_area = data[40:100]
                    try:
                        search_text = search_area.decode('ascii', errors='ignore').upper()
                        if 'NINTENDO' in search_text:
                            out['publisher'] = 'Nintendo'
                    except:
                        pass
        else:
            out['header_found'] = 'No'
            out['format'] = 'Unknown FDS format'
    else:
        out['header_found'] = 'No'
        out['format'] = 'File too small'
    
    # Calculate CRC32 of entire disk image for database lookup
    checksum = crc32(data)
    out['crc32'] = hex(checksum)[2:].zfill(8)
    
    # Identify game from database using CRC32
    if checksum in db['NintendoFDS']:
        gamedb_entry = db['NintendoFDS'][checksum]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    
    return out

# GCE Vectrex constants
VECTREX_ROM_SIZES = {
    4096: '4KB',      # 4 KB
    8192: '8KB',      # 8 KB
    12288: '12KB',    # 12 KB (rare)
    16384: '16KB',    # 16 KB (rare)
}

# SNK Neo Geo Pocket constants
NGP_ROM_SIZES = {
    131072: '128KB',     # 128 KB
    262144: '256KB',     # 256 KB
    524288: '512KB',     # 512 KB
    1048576: '1MB',      # 1 MB
    2097152: '2MB',      # 2 MB
    4194304: '4MB',      # 4 MB
}

# Nintendo Sufami Turbo constants
SUFAMI_TURBO_ROM_SIZES = {
    524288: '512KB',     # 512 KB (4 Mbit)
    1048576: '1MB',      # 1 MB (8 Mbit)
}

# identify Nintendo Sufami Turbo game
def identify_sufami_turbo(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    # load ROM data
    f = open_file(fn, mode='rb'); data = f.read(); f.close()
    file_size = len(data)
    
    # prepare output with basic information
    out = {
        'file_size': file_size,
    }
    
    # determine ROM size category and validate
    if file_size in SUFAMI_TURBO_ROM_SIZES:
        out['rom_size_category'] = SUFAMI_TURBO_ROM_SIZES[file_size]
        out['valid_size'] = 'Yes'
    else:
        out['rom_size_category'] = 'Unknown'
        out['valid_size'] = 'No'
    
    # Sufami Turbo is a SNES add-on system by Bandai
    out['format'] = 'Sufami Turbo ROM'
    out['processor'] = 'Ricoh 5A22 (65816)'
    out['system'] = 'Super Famicom + Sufami Turbo'
    out['manufacturer'] = 'Bandai'
    
    # Check for Sufami Turbo header
    try:
        if len(data) >= 16:
            header = data[:16].decode('ascii', errors='ignore')
            if 'BANDAI SFC-ADX' in header:
                out['header_valid'] = 'Yes'
                out['header_signature'] = 'BANDAI SFC-ADX'
            else:
                out['header_valid'] = 'No'
    except:
        out['header_valid'] = 'No'
    
    # Try to extract title from filename
    try:
        import os
        filename = os.path.basename(fn)
        if filename.endswith('.st'):
            potential_title = filename[:-3]
            if ' (Japan)' in potential_title:
                potential_title = potential_title.replace(' (Japan)', '')
            out['potential_title'] = potential_title.strip()
    except:
        pass
        
    # Calculate CRC32
    checksum = crc32(data)
    out['crc32'] = hex(checksum)[2:].zfill(8)
    
    # Database lookup
    if checksum in db['SufamiTurbo']:
        gamedb_entry = db['SufamiTurbo'][checksum]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    
    return out

# Sega PICO constants
SEGA_PICO_ROM_SIZES = {
    131072: '128KB',     # 128 KB
    262144: '256KB',     # 256 KB
    524288: '512KB',     # 512 KB
    1048576: '1MB',      # 1 MB
}

# identify Sega PICO game
def identify_sega_pico(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    # load ROM data
    f = open_file(fn, mode='rb'); data = f.read(); f.close()
    file_size = len(data)
    
    # prepare output with basic information
    out = {
        'file_size': file_size,
    }
    
    # determine ROM size category and validate
    if file_size in SEGA_PICO_ROM_SIZES:
        out['rom_size_category'] = SEGA_PICO_ROM_SIZES[file_size]
        out['valid_size'] = 'Yes'
    else:
        out['rom_size_category'] = 'Unknown'
        out['valid_size'] = 'No'
    
    # Sega PICO educational system
    out['format'] = 'Sega PICO ROM'
    out['processor'] = 'Motorola 68000'
    out['system'] = 'Sega PICO'
    out['target_audience'] = 'Educational/Children'
    
    # Try to extract title from filename
    try:
        import os
        filename = os.path.basename(fn)
        if filename.endswith('.md'):
            potential_title = filename[:-3]
            if ' (Japan)' in potential_title:
                potential_title = potential_title.replace(' (Japan)', '')
            if ' (USA)' in potential_title:
                potential_title = potential_title.replace(' (USA)', '')
            out['potential_title'] = potential_title.strip()
    except:
        pass
        
    # Calculate CRC32
    checksum = crc32(data)
    out['crc32'] = hex(checksum)[2:].zfill(8)
    
    # Database lookup
    if checksum in db['SegaPico']:
        gamedb_entry = db['SegaPico'][checksum]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    
    return out

# Commodore Amiga constants  
AMIGA_ROM_SIZES = {
    524288: '512KB',     # 512 KB
    1048576: '1MB',      # 1 MB
    2097152: '2MB',      # 2 MB
}

# identify Commodore Amiga game
def identify_amiga(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    # load ROM data
    f = open_file(fn, mode='rb'); data = f.read(); f.close()
    file_size = len(data)
    
    # prepare output with basic information
    out = {
        'file_size': file_size,
    }
    
    # determine ROM size category and validate
    if file_size in AMIGA_ROM_SIZES:
        out['rom_size_category'] = AMIGA_ROM_SIZES[file_size]
        out['valid_size'] = 'Yes'
    else:
        out['rom_size_category'] = 'Unknown'
        out['valid_size'] = 'No'
    
    # Commodore Amiga system
    out['format'] = 'Amiga Disk Image'
    out['processor'] = 'Motorola 68000'
    out['system'] = 'Commodore Amiga'
    
    # Try to extract title from filename
    try:
        import os
        filename = os.path.basename(fn)
        if '.' in filename:
            potential_title = filename.rsplit('.', 1)[0]
            if ' (Europe)' in potential_title:
                potential_title = potential_title.replace(' (Europe)', '')
            out['potential_title'] = potential_title.strip()
    except:
        pass
        
    # Calculate CRC32
    checksum = crc32(data)
    out['crc32'] = hex(checksum)[2:].zfill(8)
    
    # Database lookup
    if checksum in db['Amiga']:
        gamedb_entry = db['Amiga'][checksum]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    
    return out

# MSX constants
MSX_ROM_SIZES = {
    8192: '8KB',         # 8 KB
    16384: '16KB',       # 16 KB
    32768: '32KB',       # 32 KB
    65536: '64KB',       # 64 KB
    131072: '128KB',     # 128 KB
    262144: '256KB',     # 256 KB
    524288: '512KB',     # 512 KB
}

# identify Microsoft MSX game
def identify_msx(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    # load ROM data
    f = open_file(fn, mode='rb'); data = f.read(); f.close()
    file_size = len(data)
    
    # prepare output with basic information
    out = {
        'file_size': file_size,
    }
    
    # determine ROM size category and validate
    if file_size in MSX_ROM_SIZES:
        out['rom_size_category'] = MSX_ROM_SIZES[file_size]
        out['valid_size'] = 'Yes'
    else:
        out['rom_size_category'] = 'Unknown'
        out['valid_size'] = 'No'
    
    # MSX system
    out['format'] = 'MSX ROM'
    out['processor'] = 'Zilog Z80A'
    out['system'] = 'Microsoft MSX'
    
    # Try to extract title from filename
    try:
        import os
        filename = os.path.basename(fn)
        if '.' in filename:
            potential_title = filename.rsplit('.', 1)[0]
            if ' (Japan)' in potential_title:
                potential_title = potential_title.replace(' (Japan)', '')
            out['potential_title'] = potential_title.strip()
    except:
        pass
        
    # Calculate CRC32
    checksum = crc32(data)
    out['crc32'] = hex(checksum)[2:].zfill(8)
    
    # Database lookup
    if checksum in db['MSX']:
        gamedb_entry = db['MSX'][checksum]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    
    return out

# identify Microsoft MSX2 game
def identify_msx2(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    # load ROM data
    f = open_file(fn, mode='rb'); data = f.read(); f.close()
    file_size = len(data)
    
    # prepare output with basic information
    out = {
        'file_size': file_size,
    }
    
    # determine ROM size category and validate
    if file_size in MSX_ROM_SIZES:
        out['rom_size_category'] = MSX_ROM_SIZES[file_size]
        out['valid_size'] = 'Yes'
    else:
        out['rom_size_category'] = 'Unknown'
        out['valid_size'] = 'No'
    
    # MSX2 system
    out['format'] = 'MSX2 ROM'
    out['processor'] = 'Zilog Z80A'
    out['system'] = 'Microsoft MSX2'
    
    # Try to extract title from filename
    try:
        import os
        filename = os.path.basename(fn)
        if '.' in filename:
            potential_title = filename.rsplit('.', 1)[0]
            if ' (Japan)' in potential_title:
                potential_title = potential_title.replace(' (Japan)', '')
            out['potential_title'] = potential_title.strip()
    except:
        pass
        
    # Calculate CRC32
    checksum = crc32(data)
    out['crc32'] = hex(checksum)[2:].zfill(8)
    
    # Database lookup
    if checksum in db['MSX2']:
        gamedb_entry = db['MSX2'][checksum]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    
    return out

# Low priority systems with basic implementations
def identify_casio_loopy(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    import os
    f = open_file(fn, mode='rb'); data = f.read(); f.close()
    out = {'file_size': len(data), 'format': 'Casio Loopy ROM', 'processor': 'SH-1', 'system': 'Casio Loopy'}
    try:
        filename = os.path.basename(fn)
        if '.' in filename:
            out['potential_title'] = filename.rsplit('.', 1)[0].replace(' (Japan)', '').strip()
    except: pass
    checksum = crc32(data)
    out['crc32'] = hex(checksum)[2:].zfill(8)
    if checksum in db['CasioLoopy']:
        gamedb_entry = db['CasioLoopy'][checksum]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb: out[k] = v
    return out

def identify_tiger_gamecom(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    import os
    f = open_file(fn, mode='rb'); data = f.read(); f.close()
    out = {'file_size': len(data), 'format': 'Tiger Game.com ROM', 'processor': 'Sharp SM8521', 'system': 'Tiger Game.com'}
    try:
        filename = os.path.basename(fn)
        if '.' in filename:
            out['potential_title'] = filename.rsplit('.', 1)[0].replace(' (USA)', '').strip()
    except: pass
    checksum = crc32(data)
    out['crc32'] = hex(checksum)[2:].zfill(8)
    if checksum in db['GameCom']:
        gamedb_entry = db['GameCom'][checksum]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb: out[k] = v
    return out

def identify_watara_supervision(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    import os
    f = open_file(fn, mode='rb'); data = f.read(); f.close()
    out = {'file_size': len(data), 'format': 'Watara Supervision ROM', 'processor': '65C02', 'system': 'Watara Supervision'}
    try:
        filename = os.path.basename(fn)
        if '.' in filename:
            out['potential_title'] = filename.rsplit('.', 1)[0].replace(' (Europe)', '').strip()
    except: pass
    checksum = crc32(data)
    out['crc32'] = hex(checksum)[2:].zfill(8)
    if checksum in db['Supervision']:
        gamedb_entry = db['Supervision'][checksum]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb: out[k] = v
    return out

def identify_welback_megaduck(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    import os
    f = open_file(fn, mode='rb'); data = f.read(); f.close()
    out = {'file_size': len(data), 'format': 'Welback Mega Duck ROM', 'processor': 'Sharp LR35902', 'system': 'Welback Mega Duck'}
    try:
        filename = os.path.basename(fn)
        if '.' in filename:
            out['potential_title'] = filename.rsplit('.', 1)[0].replace(' (Europe)', '').strip()
    except: pass
    checksum = crc32(data)
    out['crc32'] = hex(checksum)[2:].zfill(8)
    if checksum in db['MegaDuck']:
        gamedb_entry = db['MegaDuck'][checksum]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb: out[k] = v
    return out

def identify_fujitsu_fmtowns(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    import os
    f = open_file(fn, mode='rb'); data = f.read(); f.close()
    out = {'file_size': len(data), 'format': 'FM Towns CD-ROM', 'processor': 'Intel 80386DX', 'system': 'Fujitsu FM Towns'}
    try:
        filename = os.path.basename(fn)
        if '.' in filename:
            out['potential_title'] = filename.rsplit('.', 1)[0].replace(' (Japan)', '').strip()
    except: pass
    checksum = crc32(data)
    out['crc32'] = hex(checksum)[2:].zfill(8)
    if checksum in db['FMTowns']:
        gamedb_entry = db['FMTowns'][checksum]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb: out[k] = v
    return out

def identify_nec_pc98(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    import os
    f = open_file(fn, mode='rb'); data = f.read(); f.close()
    out = {'file_size': len(data), 'format': 'PC-98 Disk Image', 'processor': 'Intel 8086/80286', 'system': 'NEC PC-9801'}
    try:
        filename = os.path.basename(fn)
        if '.' in filename:
            out['potential_title'] = filename.rsplit('.', 1)[0].replace(' (Japan)', '').strip()
    except: pass
    checksum = crc32(data)
    out['crc32'] = hex(checksum)[2:].zfill(8)
    if checksum in db['PC98']:
        gamedb_entry = db['PC98'][checksum]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb: out[k] = v
    return out

# Nintendo 64DD constants
N64DD_ROM_SIZES = {
    64931840: '62MB',    # Standard 64DD disk size (approximately 64MB)
}

# identify Nintendo 64DD game
def identify_n64dd(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    # load ROM data
    f = open_file(fn, mode='rb'); data = f.read(); f.close()
    file_size = len(data)
    
    # prepare output with basic information
    out = {
        'file_size': file_size,
    }
    
    # determine ROM size category and validate
    if file_size in N64DD_ROM_SIZES:
        out['rom_size_category'] = N64DD_ROM_SIZES[file_size]
        out['valid_size'] = 'Yes'
    else:
        out['rom_size_category'] = 'Unknown'
        out['valid_size'] = 'No'
    
    # Nintendo 64DD disk format
    out['format'] = 'Nintendo 64DD Disk Image'
    out['processor'] = 'NEC VR4300 (64-bit MIPS)'
    out['system'] = 'Nintendo 64 + 64DD'
    out['media_type'] = 'Magnetic Disk'
    out['capacity'] = '64MB per disk'
    
    # Check for 64DD disk header pattern
    try:
        # 64DD disks have a specific header pattern at the beginning
        if len(data) >= 16:
            header = data[:16]
            # Look for the common 64DD disk pattern
            if header[0:2] == bytes([0xe8, 0x48]):
                out['header_valid'] = 'Yes'
                out['disk_format'] = '64DD Magnetic Disk'
            else:
                out['header_valid'] = 'No'
                
        # Try to extract some disk metadata
        if len(data) >= 32:
            # Look for system area information
            out['system_area'] = 'Present'
            
    except:
        out['header_valid'] = 'No'
    
    # Try to extract title from filename for identification
    try:
        import os
        filename = os.path.basename(fn)
        if filename.endswith('.ndd'):
            potential_title = filename[:-4]  # Remove .ndd extension
            # Clean up No-Intro naming convention
            if ' (Japan)' in potential_title:
                potential_title = potential_title.replace(' (Japan)', '')
            if ' (USA)' in potential_title:
                potential_title = potential_title.replace(' (USA)', '')
            # Remove version indicators
            import re
            potential_title = re.sub(r' \(Proto\)$', '', potential_title)
            potential_title = re.sub(r' \(Beta\).*$', '', potential_title)
            potential_title = re.sub(r' \(Demo\).*$', '', potential_title)
            potential_title = re.sub(r' \[b\]$', '', potential_title)
            out['potential_title'] = potential_title.strip()
    except:
        pass
        
    # Calculate CRC32 of entire disk image for database lookup
    checksum = crc32(data)
    out['crc32'] = hex(checksum)[2:].zfill(8)
    
    # Identify game from database using CRC32
    if checksum in db['N64DD']:
        gamedb_entry = db['N64DD'][checksum]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    
    return out

# Nintendo Satellaview constants
SATELLAVIEW_ROM_SIZES = {
    131072: '128KB',     # 128 KB (1 Mbit)
    262144: '256KB',     # 256 KB (2 Mbit)
    524288: '512KB',     # 512 KB (4 Mbit)
    1048576: '1MB',      # 1 MB (8 Mbit)
    2097152: '2MB',      # 2 MB (16 Mbit)
    4194304: '4MB',      # 4 MB (32 Mbit)
}

# identify Nintendo Satellaview game
def identify_satellaview(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    # load ROM data
    f = open_file(fn, mode='rb'); data = f.read(); f.close()
    file_size = len(data)
    
    # prepare output with basic information
    out = {
        'file_size': file_size,
    }
    
    # determine ROM size category and validate
    if file_size in SATELLAVIEW_ROM_SIZES:
        out['rom_size_category'] = SATELLAVIEW_ROM_SIZES[file_size]
        out['valid_size'] = 'Yes'
    else:
        out['rom_size_category'] = 'Unknown'
        out['valid_size'] = 'No'
    
    # Satellaview ROMs are SNES-based with special broadcast features
    out['format'] = 'Satellaview ROM'
    out['processor'] = 'Ricoh 5A22 (65816)'
    out['system'] = 'Nintendo Satellaview (BS-X)'
    out['broadcast_system'] = 'St.GIGA satellite'
    
    # Try to extract title from filename for identification
    try:
        import os
        filename = os.path.basename(fn)
        if filename.endswith('.bs'):
            potential_title = filename[:-3]  # Remove .bs extension
            # Clean up No-Intro naming convention
            if ' (Japan)' in potential_title:
                potential_title = potential_title.replace(' (Japan)', '')
            # Check for special types
            if '(Magazine)' in potential_title:
                out['content_type'] = 'Digital Magazine'
                potential_title = potential_title.replace(' (Magazine)', '')
            elif '(SoundLink)' in potential_title:
                out['content_type'] = 'SoundLink Game'
                potential_title = potential_title.replace(' (SoundLink)', '')
            elif '(Data Pack)' in potential_title:
                out['content_type'] = 'Data Pack'
                potential_title = potential_title.replace(' (Data Pack)', '')
            elif '(Memory Pack)' in potential_title:
                out['content_type'] = 'Memory Pack'
                potential_title = potential_title.replace(' (Memory Pack)', '')
            elif '(Demo)' in potential_title:
                out['content_type'] = 'Demo'
                potential_title = potential_title.replace(' (Demo)', '')
            else:
                out['content_type'] = 'Game'
            
            out['potential_title'] = potential_title.strip()
    except:
        pass
        
    # Satellaview ROMs don't have traditional SNES headers
    # They use a different structure for broadcast identification
    out['header_format'] = 'BS-X Header'
    
    # Calculate CRC32 of entire ROM for database lookup
    checksum = crc32(data)
    out['crc32'] = hex(checksum)[2:].zfill(8)
    
    # Identify game from database using CRC32
    if checksum in db['Satellaview']:
        gamedb_entry = db['Satellaview'][checksum]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    
    return out

# Atari ST constants
ATARIST_ROM_SIZES = {
    468252: '456KB',      # Standard single density disk
    471664: '460KB',      # Single density disk variant
    520242: '508KB',      # Double density disk
    521027: '509KB',      # Double density disk variant
    737280: '720KB',      # High density disk
    901120: '880KB',      # Extended format
}

# identify Atari ST game
def identify_atarist(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    # load ROM data
    f = open_file(fn, mode='rb'); data = f.read(); f.close()
    file_size = len(data)
    
    # prepare output with basic information
    out = {
        'file_size': file_size,
    }
    
    # determine ROM size category and validate
    if file_size in ATARIST_ROM_SIZES:
        out['rom_size_category'] = ATARIST_ROM_SIZES[file_size]
        out['valid_size'] = 'Yes'
    else:
        out['rom_size_category'] = 'Unknown'
        out['valid_size'] = 'No'
    
    # Determine file format based on extension and content
    ext = get_extension(fn).lower()
    
    if ext == 'ipf':
        # IPF (Interchangeable Preservation Format) - check for CAPS header
        out['format'] = 'IPF (Interchangeable Preservation Format)'
        out['processor'] = 'Motorola 68000'
        
        try:
            header = data[:4].decode('ascii', errors='ignore')
            if header == 'CAPS':
                out['header_valid'] = 'Yes'
                out['preservation_format'] = 'CAPS/IPF'
            else:
                out['header_valid'] = 'No'
        except:
            out['header_valid'] = 'No'
            
    elif ext == 'st':
        out['format'] = 'Atari ST Disk Image (ST)'
        out['processor'] = 'Motorola 68000'
        
    elif ext == 'stx':
        out['format'] = 'Atari ST Extended Disk Image (STX)'
        out['processor'] = 'Motorola 68000'
        
    elif ext == 'msa':
        out['format'] = 'Magic Shadow Archiver (MSA)'
        out['processor'] = 'Motorola 68000'
        
    else:
        out['format'] = 'Unknown Atari ST format'
        out['processor'] = 'Motorola 68000'
    
    # Atari ST disk format information
    out['media_type'] = '3.5" Floppy Disk'
    out['system'] = 'Atari ST/STE/TT/Falcon'
    
    # Try to extract title from filename for identification
    try:
        import os
        filename = os.path.basename(fn)
        if '.' in filename:
            potential_title = filename.rsplit('.', 1)[0]  # Remove extension
            # Clean up No-Intro naming convention
            if ' (Europe)' in potential_title:
                potential_title = potential_title.replace(' (Europe)', '')
            if ' (USA)' in potential_title:
                potential_title = potential_title.replace(' (USA)', '')
            # Remove disk indicators
            import re
            potential_title = re.sub(r' \(Disk [^)]+\)$', '', potential_title)
            out['potential_title'] = potential_title
    except:
        pass
        
    # Calculate CRC32 of entire file for database lookup
    checksum = crc32(data)
    out['crc32'] = hex(checksum)[2:].zfill(8)
    
    # Identify game from database using CRC32
    if checksum in db['AtariST']:
        gamedb_entry = db['AtariST'][checksum]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    
    return out

# Commodore 64 constants
C64_ROM_SIZES = {
    4096: '4KB',        # 4 KB cartridge
    8192: '8KB',        # 8 KB cartridge
    16384: '16KB',      # 16 KB cartridge
    32768: '32KB',      # 32 KB cartridge
    65536: '64KB',      # 64 KB cartridge
    174848: '171KB',    # Standard D64 disk image
}

# identify Commodore 64 game
def identify_c64(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    # load ROM data
    f = open_file(fn, mode='rb'); data = f.read(); f.close()
    file_size = len(data)
    
    # prepare output with basic information
    out = {
        'file_size': file_size,
    }
    
    # determine ROM size category and validate
    if file_size in C64_ROM_SIZES:
        out['rom_size_category'] = C64_ROM_SIZES[file_size]
        out['valid_size'] = 'Yes'
    else:
        out['rom_size_category'] = 'Unknown'
        out['valid_size'] = 'No'
    
    # Determine file format based on extension and content
    ext = get_extension(fn).lower()
    
    if ext == 'crt':
        # Cartridge format - check for C64 CARTRIDGE header
        out['format'] = 'C64 Cartridge (CRT)'
        out['processor'] = 'MOS 6510'
        
        try:
            header = data[:16].decode('ascii', errors='ignore')
            if header.startswith('C64 CARTRIDGE'):
                out['header_valid'] = 'Yes'
                
                # Extract cartridge type from header
                if len(data) >= 0x17:
                    cart_type = (data[0x16] << 8) | data[0x17]
                    out['cartridge_type'] = f'{cart_type}'
                    
            else:
                out['header_valid'] = 'No'
        except:
            out['header_valid'] = 'No'
            
    elif ext == 'prg':
        out['format'] = 'C64 Program (PRG)'
        out['processor'] = 'MOS 6510'
        
        # PRG files start with 2-byte load address
        if len(data) >= 2:
            load_addr = data[0] | (data[1] << 8)
            out['load_address'] = f'${load_addr:04X}'
            
    elif ext == 'd64':
        out['format'] = 'C64 Disk Image (D64)'
        out['processor'] = 'MOS 6510'
        out['media_type'] = '1541 Floppy Disk'
        
    elif ext == 'bin':
        out['format'] = 'C64 Binary'
        out['processor'] = 'MOS 6510'
        
    else:
        out['format'] = 'Unknown C64 format'
        out['processor'] = 'MOS 6510'
    
    # Try to extract title from filename for identification
    try:
        import os
        filename = os.path.basename(fn)
        if '.' in filename:
            potential_title = filename.rsplit('.', 1)[0]  # Remove extension
            # Clean up No-Intro naming convention
            if ' (World)' in potential_title:
                potential_title = potential_title.replace(' (World)', '')
            if ' (USA, Europe)' in potential_title:
                potential_title = potential_title.replace(' (USA, Europe)', '')
            out['potential_title'] = potential_title
    except:
        pass
        
    # Calculate CRC32 of entire file for database lookup
    checksum = crc32(data)
    out['crc32'] = hex(checksum)[2:].zfill(8)
    
    # Identify game from database using CRC32
    if checksum in db['C64']:
        gamedb_entry = db['C64'][checksum]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    
    return out

# Nintendo Game & Watch constants
GAMEWATCH_ROM_SIZES = {
    1856: '1856B',    # 1856 bytes (early games)
    4096: '4KB',      # 4 KB (later games)
    8192: '8KB',      # 8 KB (rare)
}

# identify Nintendo Game & Watch game
def identify_gamewatch(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    # load ROM data
    f = open_file(fn, mode='rb'); data = f.read(); f.close()
    file_size = len(data)
    
    # prepare output with basic information
    out = {
        'file_size': file_size,
    }
    
    # determine ROM size category and validate
    if file_size in GAMEWATCH_ROM_SIZES:
        out['rom_size_category'] = GAMEWATCH_ROM_SIZES[file_size]
        out['valid_size'] = 'Yes'
    else:
        out['rom_size_category'] = 'Unknown'
        out['valid_size'] = 'No'
    
    # Game & Watch ROMs are raw microcontroller dumps
    out['format'] = 'Raw microcontroller dump'
    out['processor'] = 'Sharp SM5xx series'
    
    # These ROMs don't have standard headers, so we rely on filename parsing
    # and database lookup via CRC32
    try:
        import os
        filename = os.path.basename(fn)
        if filename.endswith('.bin'):
            potential_title = filename[:-4]  # Remove .bin extension
            # Clean up No-Intro naming convention
            if ' (World)' in potential_title:
                potential_title = potential_title.replace(' (World)', '')
            out['potential_title'] = potential_title
    except:
        pass
    
    # Game & Watch games don't have internal checksums or headers
    # All identification is done via CRC32 database lookup
    out['header_format'] = 'None'
    
    # Calculate CRC32 of entire ROM for database lookup
    checksum = crc32(data)
    out['crc32'] = hex(checksum)[2:].zfill(8)
    
    # Identify game from database using CRC32
    if checksum in db['GameWatch']:
        gamedb_entry = db['GameWatch'][checksum]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    
    return out

# identify SNK Neo Geo Pocket Color game
def identify_neogeopocket_color(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    # load ROM data
    f = open_file(fn, mode='rb'); data = f.read(); f.close()
    file_size = len(data)
    
    # prepare output with basic information
    out = {
        'file_size': file_size,
    }
    
    # determine ROM size category and validate
    if file_size in NGP_ROM_SIZES:
        out['rom_size_category'] = NGP_ROM_SIZES[file_size]
        out['valid_size'] = 'Yes'
    else:
        out['rom_size_category'] = 'Unknown'
        out['valid_size'] = 'No'
    
    # Neo Geo Pocket Color ROMs have the same header structure as NGP
    out['format'] = 'NGPC ROM'
    out['processor'] = 'Toshiba TLCS-900H'
    
    # Parse header information
    try:
        # Check for SNK license string at offset 0x00
        license_str = data[0x00:0x1C].decode('ascii', errors='ignore').strip()
        if 'LICENSED BY SNK' in license_str:
            out['license'] = 'SNK Corporation'
            out['header_valid'] = 'Yes'
        else:
            out['header_valid'] = 'No'
        
        # Game title at offset 0x24 (12 bytes)
        title_raw = data[0x24:0x30]
        title = title_raw.decode('ascii', errors='ignore').rstrip('\x00').strip()
        if title:
            out['internal_title'] = title
        
        # Additional header info
        # System type at 0x22
        system_type = data[0x22] if len(data) > 0x22 else 0
        if system_type == 0x00:
            out['system_type'] = 'Neo Geo Pocket'
        elif system_type == 0x10:
            out['system_type'] = 'Neo Geo Pocket Color'
        else:
            out['system_type'] = f'Unknown (0x{system_type:02X})'
        
    except:
        out['header_valid'] = 'No'
    
    # Calculate CRC32 of entire ROM for database lookup
    checksum = crc32(data)
    out['crc32'] = hex(checksum)[2:].zfill(8)
    
    # Identify game from database using CRC32
    if checksum in db['NGPC']:
        gamedb_entry = db['NGPC'][checksum]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    
    return out

# identify SNK Neo Geo Pocket game
def identify_neogeopocket(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    # load ROM data
    f = open_file(fn, mode='rb'); data = f.read(); f.close()
    file_size = len(data)
    
    # prepare output with basic information
    out = {
        'file_size': file_size,
    }
    
    # determine ROM size category and validate
    if file_size in NGP_ROM_SIZES:
        out['rom_size_category'] = NGP_ROM_SIZES[file_size]
        out['valid_size'] = 'Yes'
    else:
        out['rom_size_category'] = 'Unknown'
        out['valid_size'] = 'No'
    
    # Neo Geo Pocket ROMs have a standard header
    out['format'] = 'NGP ROM'
    out['processor'] = 'Toshiba TLCS-900H'
    
    # Parse header information
    try:
        # Check for SNK license string at offset 0x00
        license_str = data[0x00:0x1C].decode('ascii', errors='ignore').strip()
        if 'LICENSED BY SNK' in license_str:
            out['license'] = 'SNK Corporation'
            out['header_valid'] = 'Yes'
        else:
            out['header_valid'] = 'No'
        
        # Game title at offset 0x24 (12 bytes)
        title_raw = data[0x24:0x30]
        title = title_raw.decode('ascii', errors='ignore').rstrip('\x00').strip()
        if title:
            out['internal_title'] = title
        
        # Additional header info
        # System type at 0x22
        system_type = data[0x22] if len(data) > 0x22 else 0
        if system_type == 0x00:
            out['system_type'] = 'Neo Geo Pocket'
        elif system_type == 0x10:
            out['system_type'] = 'Neo Geo Pocket Color'
        else:
            out['system_type'] = f'Unknown (0x{system_type:02X})'
        
    except:
        out['header_valid'] = 'No'
    
    # Calculate CRC32 of entire ROM for database lookup
    checksum = crc32(data)
    out['crc32'] = hex(checksum)[2:].zfill(8)
    
    # Identify game from database using CRC32
    if checksum in db['NGP']:
        gamedb_entry = db['NGP'][checksum]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    
    return out

# identify GCE Vectrex game
def identify_vectrex(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    # load ROM data
    f = open_file(fn, mode='rb'); data = f.read(); f.close()
    file_size = len(data)
    
    # prepare output with basic information
    out = {
        'file_size': file_size,
    }
    
    # determine ROM size category and validate
    if file_size in VECTREX_ROM_SIZES:
        out['rom_size_category'] = VECTREX_ROM_SIZES[file_size]
        out['valid_size'] = 'Yes'
    else:
        out['rom_size_category'] = 'Unknown'
        out['valid_size'] = 'No'
    
    # Vectrex ROMs are raw binary dumps for 6809 processor
    out['format'] = 'Raw ROM dump'
    out['processor'] = 'Motorola 6809'
    
    # Try to extract copyright and title information
    # Many Vectrex ROMs have text strings in the first few hundred bytes
    try:
        text_data = data[:512].decode('ascii', errors='ignore')
        
        # Look for copyright information
        if 'GCE' in text_data:
            out['copyright'] = 'GCE'
        
        # Try to find potential title (look for uppercase sequences)
        import re
        titles = re.findall(r'[A-Z][A-Z ]{3,}[A-Z]', text_data)
        if titles:
            # Filter out common non-title strings
            filtered_titles = [t.strip() for t in titles if len(t.strip()) >= 4 and 'GCE' not in t]
            if filtered_titles:
                out['potential_title'] = filtered_titles[0]
        
    except:
        pass
    
    # Calculate CRC32 of entire ROM for database lookup
    checksum = crc32(data)
    out['crc32'] = hex(checksum)[2:].zfill(8)
    
    # Identify game from database using CRC32
    if checksum in db['Vectrex']:
        gamedb_entry = db['Vectrex'][checksum]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    
    return out

# identify Sega SG-1000 game
def identify_sega_sg1000(fn, db, user_uuid=None, user_volume_ID=None, prefer_gamedb=False):
    # load ROM data
    f = open_file(fn, mode='rb'); data = f.read(); f.close()
    file_size = len(data)
    
    # prepare output with basic information
    out = {
        'file_size': file_size,
    }
    
    # determine ROM size category and validate
    if file_size in SEGA_SG1000_ROM_SIZES:
        out['rom_size_category'] = SEGA_SG1000_ROM_SIZES[file_size]
        out['valid_size'] = 'Yes'
    else:
        out['rom_size_category'] = 'Unknown'
        out['valid_size'] = 'No'
    
    # SG-1000 ROMs are typically raw binary dumps without headers
    out['format'] = 'Raw ROM dump'
    out['header_found'] = 'No'
    
    # Look for potential SG-1000 characteristics
    try:
        # Check for common Z80 instruction patterns at the start
        if len(data) >= 4:
            # Look for common Z80 startup patterns
            start_bytes = data[:4]
            
            # Common patterns: JP instruction (0xC3), DI instruction (0xF3), etc.
            z80_patterns = [0xC3, 0xF3, 0x01, 0x31]  # JP, DI, LD BC, LD SP
            pattern_count = sum(1 for byte in start_bytes if byte in z80_patterns)
            out['z80_pattern_score'] = pattern_count
            
            # Check for jump instruction at start (common in SG-1000 ROMs)
            if start_bytes[0] == 0xC3:  # JP instruction
                jump_addr = start_bytes[1] | (start_bytes[2] << 8)
                out['startup_jump_address'] = f'0x{jump_addr:04X}'
        
        # Look for potential text strings or patterns
        search_data = data[:1024]  # First 1KB
        
        # Look for common SG-1000 related strings or patterns
        try:
            text_content = search_data.decode('ascii', errors='ignore').upper()
            sega_indicators = ['SEGA', 'SG-1000', 'SC-3000']
            found_indicators = [indicator for indicator in sega_indicators if indicator in text_content]
            if found_indicators:
                out['detected_indicators'] = ', '.join(found_indicators)
        except:
            pass
        
        # Analyze byte distribution (SG-1000 ROMs often have specific patterns)
        if len(data) >= 256:
            sample_bytes = data[:256]
            zero_count = sample_bytes.count(0x00)
            ff_count = sample_bytes.count(0xFF)
            
            # High concentration of 0x00 or 0xFF might indicate padding or data sections
            if zero_count > 50:
                out['high_zero_content'] = 'Yes'
            if ff_count > 50:
                out['high_ff_content'] = 'Yes'
    
    except:
        pass
    
    # Calculate CRC32 of entire ROM for database lookup
    checksum = crc32(data)
    out['crc32'] = hex(checksum)[2:].zfill(8)
    
    # Identify game from database using CRC32
    if checksum in db['SegaSG1000']:
        gamedb_entry = db['SegaSG1000'][checksum]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    
    return out

# dictionary storing all identify functions
IDENTIFY = {
    'Atari2600': identify_atari2600,
    'Atari5200': identify_atari5200,
    'Atari7800': identify_atari7800,
    'AtariJaguar': identify_atari_jaguar,
    'AtariLynx': identify_atari_lynx,
    'GB':        identify_gb_gbc,
    'GBC':       identify_gb_gbc,
    'GBA':       identify_gba,
    'GC':        identify_gc,
    'Genesis':   identify_genesis,
    'N64':       identify_n64,
    'NeoGeoCD':  identify_neogeocd,
    'NES':       identify_nes,
    'PSP':       identify_psp,
    'PSX':       identify_psx,
    'PS2':       identify_ps2,
    'Saturn':    identify_saturn,
    'SegaCD':    identify_segacd,
    'SNES':      identify_snes,
    'WonderSwan': identify_wonderswan,
    'WonderSwanColor': identify_wonderswan,
    'ColecoVision': identify_colecovision,
    'PCEngine': identify_pcengine,
    'PCEngineSuperGrafx': identify_pcengine,
    'GameGear': identify_gamegear,
    'MasterSystem': identify_mastersystem,
    'Sega32X': identify_sega32x,
    'NintendoFDS': identify_nintendo_fds,
    'SegaSG1000': identify_sega_sg1000,
    'Vectrex': identify_vectrex,
    'NGP': identify_neogeopocket,
    'NGPC': identify_neogeopocket_color,
    'GameWatch': identify_gamewatch,
    'C64': identify_c64,
    'AtariST': identify_atarist,
    'Satellaview': identify_satellaview,
    'N64DD': identify_n64dd,
    'SufamiTurbo': identify_sufami_turbo,
    'SegaPico': identify_sega_pico,
    'Amiga': identify_amiga,
    'MSX': identify_msx,
    'MSX2': identify_msx2,
    'CasioLoopy': identify_casio_loopy,
    'GameCom': identify_tiger_gamecom,
    'Supervision': identify_watara_supervision,
    'MegaDuck': identify_welback_megaduck,
    'FMTowns': identify_fujitsu_fmtowns,
    'PC98': identify_nec_pc98,
}
GAMEID_CONSOLES = sorted(IDENTIFY.keys())
IDENTIFY = {k.upper():v for k,v in IDENTIFY.items()} # upper-case for case-insensitivity

# throw an error for unsupported consoles
def check_console(console):
    if console.upper() not in IDENTIFY:
        error("Invalid console: %s\nOptions: %s" % (console, ', '.join(GAMEID_CONSOLES)))

# main program logic
def main():
    args = parse_args()
    db = load_db(args.database)
    meta = IDENTIFY[args.console](args.input, db, user_uuid=args.disc_uuid, user_volume_ID=args.disc_label, prefer_gamedb=args.prefer_gamedb)
    if meta is None:
        error("%s game not found: %s" % (args.console, args.input))
    for k,v in meta.items(): # replace empty string values with 'None'
        if isinstance(v, str) and len(v.strip()) == 0:
            meta[k] = 'None'
    f_out = open_file(args.output, 'wt')
    print('\n'.join('%s%s%s' % (k,args.delimiter,v) for k,v in meta.items()), file=f_out)
    f_out.close()

# run program
if __name__ == "__main__":
    if len(sys.argv) == 1:
        get_args_interactive(sys.argv)
    main()
