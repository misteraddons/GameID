# GameID
Identify a game using [GameDB](https://github.com/niemasd/GameDB). Supported consoles:

* `Amiga` - Commodore Amiga
* `Atari2600` - Atari 2600
* `Atari5200` - Atari 5200
* `Atari7800` - Atari 7800
* `AtariJaguar` - Atari Jaguar
* `AtariLynx` - Atari Lynx
* `AtariST` - Atari ST
* `C64` - Commodore 64
* `CasioLoopy` - Casio Loopy
* `ColecoVision` - Coleco ColecoVision
* `FMTowns` - Fujitsu FM Towns
* `GameCom` - Tiger Game.com
* `GameGear` - Sega Game Gear
* `GameWatch` - Nintendo Game & Watch
* `GB` - Nintendo Game Boy
* `GBA` - Nintendo Game Boy Advance
* `GBC` - Nintendo Game Boy Color
* `GC` - Nintendo GameCube
* `Genesis` - Sega Genesis
* `MSX` - Microsoft MSX
* `MSX2` - Microsoft MSX2
* `MasterSystem` - Sega Master System
* `MegaDuck` - Welback Mega Duck
* `N64` - Nintendo 64
* `N64DD` - Nintendo 64DD
* `NES` - Nintendo Entertainment System
* `NGP` - SNK Neo Geo Pocket
* `NGPC` - SNK Neo Geo Pocket Color
* `NeoGeoCD` - SNK Neo Geo CD
* `NintendoFDS` - Nintendo Family Computer Disk System
* `PC98` - NEC PC-98
* `PCEngine` - PC Engine/TurboGrafx-16
* `PCEngineSuperGrafx` - PC Engine SuperGrafx
* `PS2` - Sony PlayStation 2
* `PSP` - Sony PlayStation Portable
* `PSX` - Sony PlayStation
* `Satellaview` - Nintendo Satellaview
* `Saturn` - Sega Saturn
* `Sega32X` - Sega 32X
* `SegaCD` - Sega CD
* `SegaPico` - Sega PICO
* `SegaSG1000` - Sega SG-1000
* `SNES` - Super Nintendo Entertainment System
* `SufamiTurbo` - Nintendo Sufami Turbo
* `Supervision` - Watara Supervision
* `Vectrex` - GCE Vectrex
* `WonderSwan` - Bandai WonderSwan
* `WonderSwanColor` - Bandai WonderSwan Color

## Usage

For manually checking individual games, we recommend using the [GameID web app](https://niema.net/GameID). For bulk/programmatic lookups, we recommend using the command line Python script, [`GameID.py`](GameID.py):

```
usage: GameID.py [-h] -i INPUT -c CONSOLE [-d DATABASE] [-o OUTPUT] [--delimiter DELIMITER] [--prefer_gamedb]

options:
  -h, --help                         show this help message and exit
  -i INPUT, --input INPUT            Input Game File (default: None)
  -c CONSOLE, --console CONSOLE      Console
  -d DATABASE, --database DATABASE   GameID Database (db.pkl.gz) (default: None)
  -o OUTPUT, --output OUTPUT         Output File (default: stdout)
  --delimiter DELIMITER              Delimiter (default: '\t')
  --prefer_gamedb                    Prefer Metadata in GameDB (rather than metadata loaded from game) (default: False)
```

If the database ([`db.pkl.gz`](db.pkl.gz)) is not provided via `-d`, it will be downloaded from this repo. This is **very slow**, so we strongly recommend providing it if you are running GameID in bulk (or if your environment does not have internet connection).

This tool is being actively developed, and updates will be pushed somewhat frequently. As such, be sure to periodically `git pull` an up-to-date version of this repository to ensure you have access to all of the latest features and optimizations.

### Example: Identify a Game

```bash
./GameID.py -d db.pkl.gz -c <CONSOLE> -i <GAME_FILE>
```

### Example: Identify All PSX Games in Directory (recursive)

```bash
find psx_games/ -type f -iname "*.cue" -o -iname "*.iso" | parallel --jobs 8 ./GameID.py -d db.pkl.gz -c PSX -i "{}" ">" "{}.meta.txt"
```

### Build Database

```bash
rm -f db.pkl.gz && ./scripts/build_db.py db.pkl.gz
```

## Game Identification Methodology

GameID uses various techniques to identify games depending on the console and ROM format. Each system employs the most appropriate method based on its technical characteristics and available metadata.

### Header-Based Identification Systems

**Commodore Amiga**
- **Disk Formats**: ADF, ADZ, DMS, IPF multi-format support
- **Motorola 68000**: Processor architecture identification
- **Disk Sizes**: Standard Amiga floppy disk size validation
- **File Systems**: OFS/FFS detection capabilities

**Atari 7800**
- **Header Location**: 128-byte header at offset 0x01-0x10
- **Signature**: "ATARI7800" ASCII string at offset 0x01
- **Additional Data**: Header validation and banking scheme detection
- **ROM Sizes**: 16KB, 32KB, 48KB with banking support

**Atari Lynx**
- **Header Location**: 64-byte LNX header at beginning of ROM
- **Signature**: "LYNX" magic word
- **Header Data**: ROM size, page size, version information extraction
- **Validation**: Checksum verification and size consistency checks

**ColecoVision**
- **Header Location**: Boot signature at offset 0x8000-0x8002
- **Signature**: 0xAA55 or 0x55AA boot signature patterns
- **ROM Sizes**: 8KB, 16KB, 24KB, 32KB standard cartridge sizes
- **Multiple Signatures**: Handles both signature variants

**Commodore 64**
- **CRT Format**: "C64 CARTRIDGE" ASCII header with cartridge type extraction
- **PRG Format**: 2-byte little-endian load address parsing at start
- **D64 Format**: 1541 disk image (174,848 bytes standard size)
- **BIN Format**: Raw binary identification
- **Multi-Format**: Extension-based format determination (.crt, .prg, .d64, .bin)

**Nintendo Game Boy / Game Boy Color**
- **Header Location**: 0x0104-0x0150 ROM region with extensive metadata
- **Logo Verification**: Nintendo logo validation at 0x0104-0x0134 (required for boot)
- **Internal Title**: 11-16 byte game title at 0x0134-0x013F/0x0144
- **System Detection**: CGB flag determines Game Boy Color compatibility
- **Cartridge Analysis**: ROM/RAM size calculation, banking scheme detection
- **Dual Checksums**: Header checksum (0x014D) and global checksum (0x014E-0x014F)
- **Database Lookup**: Uses (internal_title, global_checksum) tuple for identification
- **Manufacturing Data**: Licensee codes, manufacturer codes, ROM version extraction

**Nintendo Game Boy Advance**
- **Header Location**: 0x04-0xBC ROM region
- **Logo Verification**: Nintendo logo validation at 0x04-0xA0 (96 bytes)
- **Game Metadata**: Internal title (0xA0-0xAC), game code (0xAC-0xB0)
- **Publisher Info**: Maker code at 0xB0-0xB2
- **Hardware Details**: Main unit code, device type, software version
- **Database Lookup**: Uses 4-character game_code as primary key
- **Title Extraction**: 12-byte internal title with proper encoding

**Nintendo GameCube**
- **Header Location**: First 0x0440 bytes of ISO image
- **Game Identity**: Game ID (0x0000-0x0004) and maker code (0x0004-0x0006)
- **Internal Title**: Large title field at 0x0020-0x0400 (992 bytes)
- **Disc Metadata**: Disk ID, version, and audio streaming information
- **Database Lookup**: Uses 4-character game ID (middle part of DOL-XXXX-XXX serial)
- **Multi-region**: Handles different regional variants and revisions

**Nintendo 64**
- **Endianness Detection**: Automatic big-endian/little-endian detection and conversion
- **Header Location**: 0x20-0x40 ROM region after endianness correction
- **Game Identity**: Cartridge ID (0x3C-0x3E) combined with country code (0x3E-0x40)
- **Internal Name**: 20-byte title at 0x20-0x34
- **Serial Construction**: Combines 2-byte cartridge ID + 1-byte country code
- **Database Lookup**: Uses 3-character serial (last 3 chars of NUS-NXXX-XXX format)
- **Region Detection**: Country code determines NTSC/PAL region

**Nintendo 64DD**
- **Header Pattern**: 0xE8, 0x48 byte signature (consistent across all disks)
- **Media Type**: 64MB magnetic disk format identification
- **System Area**: Detects presence of system area in disk image
- **Validation**: Header pattern matching for disk integrity

**Nintendo FDS (Family Computer Disk System)**
- **Header Signature**: "FDS\x1A" (0x46, 0x44, 0x53, 0x1A) at offset 0x00
- **Disk Info**: Disk info block parsing for additional metadata
- **Manufacturer**: Manufacturer code extraction from header
- **Format**: Disk image format with filesystem structure

**Nintendo Sufami Turbo**
- **Header Signature**: "BANDAI SFC-ADX" ASCII string in first 16 bytes
- **System Type**: SNES add-on identification
- **Manufacturer**: Bandai-specific header validation
- **ROM Sizes**: 512KB (4Mbit), 1MB (8Mbit)

**SNK Neo Geo Pocket**
- **License Header**: "LICENSED BY SNK CORPORATION" at offset 0x00-0x1C
- **Game Title**: 12-byte internal title extraction at offset 0x24-0x30
- **System Detection**: Byte at 0x22 determines NGP (0x00) vs NGPC (0x10)
- **Processor**: Toshiba TLCS-900H identification

**SNK Neo Geo Pocket Color**
- **Same Header Structure**: Identical to NGP with system type differentiation
- **Content Classification**: Filename parsing for Magazine, SoundLink, Data Pack types
- **Enhanced Features**: Color system detection via header analysis
- **Broadcasting**: Special content type identification

**Sony PlayStation Portable (PSP)**
- **ISO9660 Structure**: UMD disc image parsing with filesystem analysis
- **UMD_DATA.BIN**: Key identification file containing serial number
- **Serial Extraction**: Reads until '|' delimiter character in UMD_DATA.BIN
- **Multi-layered**: ISO UUID, volume ID, and UMD data combination
- **Database Lookup**: Uses extracted serial as key in PSP database
- **Region Detection**: Serial prefix indicates regional variant

**Super Nintendo Entertainment System (SNES)**
- **Header Detection**: Intelligent LoROM/HiROM header location detection
- **Copier Header**: Automatic 512-byte copier header removal when present
- **Checksum Validation**: Verifies checksum + complement = 65535 for integrity
- **Internal Metadata**: 21-byte internal name, developer ID, ROM version
- **ROM Analysis**: Memory mapping detection (LoROM/HiROM), speed detection
- **Coprocessor Detection**: Special chip identification (DSP, SuperFX, etc.)
- **Database Lookup**: Uses (developer_ID, internal_name_hex, rom_version, checksum) tuple
- **Advanced Features**: Handles extended ROM types and hardware variations

### Pattern Detection Systems

**Sega Genesis**
- **Magic Word Search**: Scans for multiple SEGA-related signatures in 0x100-0x200 range
- **Comprehensive Header**: Extracts system type, publisher, domestic/overseas titles
- **Release Metadata**: Build date, software type, ID, and revision information
- **Memory Mapping**: ROM/RAM ranges, device support, region codes
- **Checksum Verification**: ROM checksum validation when present
- **Database Lookup**: Uses sanitized ID (removes spaces, dashes) as key
- **Modem Support**: Special hardware detection for specific titles

**Game Gear / Master System**
- **TMR SEGA Signature**: "TMR SEGA" ASCII string at multiple locations (0x7FF0, 0x3FF0, 0x1FF0)
- **Checksum Validation**: Optional checksum at standard locations (many ROMs have 0x0000)
- **Region Detection**: ROM size and region code analysis
- **System Differentiation**: Game Gear vs Master System detection

**PC Engine / SuperGrafx**
- **Pattern Analysis**: Statistical analysis of 6502-like instruction patterns
- **No Standard Header**: Raw binary pattern detection
- **System Variant**: .pce vs .sgx extension determines variant
- **ROM Sizes**: 128KB to 2MB standard ranges

**Sega 32X**
- **Genesis Header**: Combines Genesis header detection with 32X patterns
- **SEGA Signature**: Multiple location searches for "SEGA" signature
- **Banking Detection**: ROM banking scheme analysis
- **Hybrid System**: Genesis compatibility with 32X enhancements

**Sega Saturn**
- **Magic Word Search**: "SEGA SATURN" signature detection in disc header
- **Comprehensive Metadata**: Manufacturer ID, game ID, version information
- **Release Information**: Build date (YYYYMMDD), internal title extraction
- **Regional Support**: Target area codes and device compatibility flags
- **Database Lookup**: Uses cleaned serial (removes spaces, dashes) as key
- **Disc Analysis**: Multi-layer disc structure parsing for complex games

**Sega CD**
- **Magic Word Detection**: Searches for SEGA magic words in first 0x300 bytes
- **Extensive Header**: Volume name, system name, disc ID extraction
- **Date Processing**: Build date (MMDDYYYY) and release date parsing
- **Multi-language**: Domestic and overseas title extraction
- **Hardware Codes**: Device support and region compatibility detection
- **Database Lookup**: Uses sanitized ID (removes '#', '-', spaces) as key
- **Backward Compatibility**: Handles various Sega CD revision differences

**Sega SG-1000**
- **Z80 Pattern Detection**: Searches for Z80 instruction sequences and opcodes
- **Scoring System**: Weighted scoring based on pattern frequency and likelihood
- **No Standard Header**: Pure pattern-based identification
- **Raw Analysis**: Binary instruction pattern recognition

### Size-Based Identification Systems

**Atari 2600**
- **Banking Schemes**: ROM size determines banking type (F8, F6, F4, FE, 3F, etc.)
- **Size Categories**: 2KB, 4KB, 8KB, 16KB, 32KB standard sizes
- **No Headers**: Pure size-based banking detection
- **Memory Mapping**: Banking scheme consistency validation

**Atari 5200**
- **ROM Sizes**: 4KB, 8KB, 16KB, 32KB, 40KB standard cartridge sizes
- **Optional Header**: 0x58 ('5X') pattern detection when present
- **Banking Analysis**: Memory banking scheme identification
- **Atari 8-bit**: Family compatibility detection

**Atari Jaguar**
- **Size Range**: 128KB to 6MB cartridge range
- **Universal Header**: Jaguar-specific header parsing when available
- **ROM Validation**: Size consistency with known formats
- **Large ROMs**: Support for CD-ROM sized games

**GCE Vectrex**
- **Size Validation**: 4KB, 8KB, 12KB, 16KB standard ROM sizes
- **Text Extraction**: ASCII pattern matching for copyright and titles
- **Processor**: Motorola 6809 system identification
- **Copyright Detection**: "GCE" string detection in ROM data

**Nintendo Game & Watch**
- **Microcontroller Dumps**: 1856 bytes (early), 4KB (later) standard sizes
- **Sharp SM5xx**: Series processor identification
- **No Headers**: Filename-based identification primary method
- **Size Categories**: Precise size matching for validation

### Format-Specific Identification Systems

**Atari ST**
- **IPF Format**: "CAPS" header for Interchangeable Preservation Format
- **Multiple Formats**: IPF, ST, STX, MSA format support
- **Disk Images**: 3.5" floppy disk format identification
- **Preservation**: Handles disk preservation metadata

**Commodore Amiga**
- **Disk Formats**: ADF, ADZ, DMS, IPF multi-format support
- **Motorola 68000**: Processor architecture identification
- **Disk Sizes**: Standard Amiga floppy disk size validation
- **File Systems**: OFS/FFS detection capabilities

**Nintendo Satellaview**
- **SNES Base**: SNES-compatible ROM structure with broadcast extensions
- **Content Types**: Magazine, SoundLink, Data Pack, Memory Pack classification
- **Broadcasting**: St.GIGA satellite system identification
- **Filename Analysis**: No-Intro convention parsing for content type

### Database-Only Identification Systems

**Nintendo Entertainment System (NES)**
- **CRC32 Primary**: Simple but highly effective full-ROM CRC32 calculation
- **Entire ROM**: Processes complete ROM file for checksum generation
- **Database Lookup**: Uses CRC32 integer value as direct key in NES database
- **No Header Parsing**: Relies entirely on mathematical fingerprinting
- **Regional Variants**: Database contains all regional ROM variations
- **Simplicity**: Most straightforward identification method in GameID

**SNK Neo Geo CD**
- **ISO Metadata**: Relies on disc filesystem UUID and volume ID
- **Dual-key Strategy**: Primary lookup uses (UUID, volume_ID) tuple
- **Fallback Method**: Secondary lookup uses volume_ID only
- **Minimal Processing**: No game data parsing, pure disc metadata approach
- **Database Structure**: Handles both composite and single-field keys
- **Disc Variants**: Supports different pressing variants of same game

**Sony PlayStation (PSX) / PlayStation 2 (PS2)**
- **Multi-strategy Approach**: Progressive fallback system for robust identification
- **Primary Method**: Scans root directory for files matching SXXX_XXX.XX pattern
- **Secondary Method**: Uses ISO volume ID when file scan fails
- **Tertiary Method**: Filename extraction as final fallback
- **Serial Normalization**: Converts hyphens to underscores (SXXX-XXX → SXXX_XXX)
- **Redump Integration**: Supports Redump naming conventions as alternate keys
- **Regional Processing**: Handles different regional serial formats
- **Database Optimization**: Pre-computed ID prefix lists for performance

**Microsoft MSX / MSX2**
- **CRC32 Lookup**: Primary identification via database matching
- **Z80A Processor**: System architecture identification
- **ROM Sizes**: 8KB-512KB cartridge size categories
- **Regional Focus**: Primarily Japanese market software

**Sega PICO**
- **Educational System**: Children's software identification
- **Genesis Compatible**: Motorola 68000 processor, .md extension
- **Database Matching**: CRC32 with filename parsing
- **Target Audience**: Educational content classification

### Minimal Implementation Systems

**Casio Loopy, Tiger Game.com, Watara Supervision, Welback Mega Duck**
- **Basic Identification**: File size validation + CRC32 database lookup
- **Processor Info**: System-specific processor identification (SH-1, SM8521, 65C02, LR35902)
- **Region Parsing**: No-Intro filename convention cleanup
- **Simplified**: No complex header parsing required

**Fujitsu FM Towns, NEC PC-98**
- **Computer Platforms**: Japanese computer market focus
- **Disk Images**: CD-ROM and floppy disk format identification
- **x86 Architecture**: Intel processor family identification (80386DX, 8086/80286)
- **Database Primary**: CRC32 matching with basic metadata

### Universal Techniques

**CRC32 Database Matching**
- Every system calculates CRC32 checksum of entire ROM/disk image
- Primary identification method when headers fail or are unavailable
- Database lookup provides definitive game identification

**Filename Analysis**
- No-Intro naming convention parsing for all systems
- Region extraction (Japan, USA, Europe) and cleanup
- Version information (Proto, Beta, Demo, Rev) identification
- Title extraction with standardized formatting

**Size Validation**
- ROM/disk size categories specific to each system
- Banking scheme detection based on size patterns
- Format validation (standard vs non-standard sizes)
- Consistency checks across identification methods

**Multi-Format Support**
- Extension-based initial format detection
- Header validation when available for verification
- Content analysis for format confirmation
- Fallback methods when primary detection fails

This comprehensive approach ensures accurate identification across 47 different gaming platforms, from simple 2KB Atari 2600 cartridges to complex Sony PlayStation disc images, using the most appropriate technique for each system's unique characteristics. The methodologies range from sophisticated multi-layered header parsing (SNES, Genesis) to elegant mathematical fingerprinting (NES), with each system's approach optimized for its specific technical constraints and available metadata structures.

## Acknowledgements

* Thanks to [MiSTer Addons](https://misteraddons.com/) for the idea and for help with testing!
* Thanks to [Artemio Urbina](https://junkerhq.net/) and the other developers of the [240p Test Suite](https://artemiourbina.itch.io/240p-test-suite), which we use as [example files](https://github.com/niemasd/GameID/tree/main/example)!
* Thanks to [Daniel Ji](https://github.com/daniel-ji) for creating the Pyodide web app!
* Site favicon by open source project [Twemoji](https://github.com/twitter/twemoji") licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
