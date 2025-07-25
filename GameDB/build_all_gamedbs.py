#!/usr/bin/env python3
"""
Build GameDB for all newly supported systems from No-Intro collection
"""

import os
import sys
import struct
from zlib import crc32

def clean_title(filename):
    """Clean up title by removing No-Intro filename patterns"""
    title = filename
    if '.' in title:
        title = title.rsplit('.', 1)[0]
    
    # Remove common No-Intro patterns
    patterns_to_remove = [
        ' (USA)', ' (Europe)', ' (Japan)', ' (World)', ' (Proto)', ' (Beta)',
        ' (Rev 1)', ' (Rev A)', ' (Rev B)', ' (Rev C)', ' (Alt)', ' (Unl)', 
        ' (Pirate)', ' (Aftermarket)', ' (En)', ' (Fr)', ' (De)', ' (Es)',
        ' (It)', ' (Pt)', ' (Ja)', ' (v1.0)', ' (v1.1)', ' (v1.2)', ' (Demo)',
        ' (Sample)', ' (Kiosk)', ' (Program)', ' (Test)', ' (Homebrew)',
        ' (Public Domain)', ' (Shareware)', ' (Freeware)', ' (Alpha)',
        ' (Gamma)', ' (Delta)', ' (Final)', ' (Release)', ' (Gold)',
        ' (Master)', ' (Director\'s Cut)', ' (Special Edition)', ' (Hack)',
        ' (Translated)', ' (Fixed)', ' (Cracked)', ' (Trained)', ' (Modified)',
        ' (Patched)', ' (Updated)', ' (Enhanced)', ' (Improved)', ' (Plus)',
        ' (Deluxe)', ' (Premium)', ' (Complete)', ' (Full)', ' (Lite)',
        ' (Mini)', ' (Micro)', ' (Pocket)', ' (Mobile)', ' (Online)',
        ' (Offline)', ' (Single Player)', ' (Multiplayer)', ' (Co-op)',
        ' (Versus)', ' (Tournament)', ' (Championship)', ' (League)',
        ' (Season)', ' (Edition)', ' (Collection)', ' (Compilation)',
        ' (Anthology)', ' (Archive)', ' (Library)', ' (Museum)', ' (Retro)',
        ' (Classic)', ' (Vintage)', ' (Legacy)', ' (Heritage)', ' (History)',
        ' (Origins)', ' (Roots)', ' (Foundation)', ' (Genesis)', ' (Beginning)',
        ' (Start)', ' (First)', ' (Original)', ' (Initial)', ' (Primary)'
    ]
    
    for pattern in patterns_to_remove:
        title = title.replace(pattern, '')
    
    return title.strip()

def determine_region(filename):
    """Determine region from filename"""
    if "(Europe)" in filename or "(PAL)" in filename:
        return "PAL"
    elif "(Japan)" in filename or "(NTSC-J)" in filename:
        return "NTSC-J"
    elif "(USA)" in filename or "(NTSC-U)" in filename:
        return "NTSC-U"
    elif "(World)" in filename:
        return "NTSC-U"
    else:
        return "NTSC-U"  # Default

# ROM Header Analysis Functions

def analyze_atari7800_header(rom_data):
    """Extract Atari 7800 header metadata"""
    if len(rom_data) < 128:
        return {}
    
    if rom_data[1:9] != b'ATARI7800':
        return {}
    
    try:
        header_version = rom_data[0]
        game_title = rom_data[16:48].decode('ascii', errors='ignore').rstrip('\x00 ')
        controller_type = rom_data[53]
        cartridge_type = rom_data[54]
        region_flags = rom_data[55]
        
        return {
            'header_version': str(header_version),
            'internal_title': game_title,
            'controller_type': f"0x{controller_type:02x}",
            'cartridge_type': f"0x{cartridge_type:02x}",
            'region_flags': f"0x{region_flags:02x}"
        }
    except:
        return {}

def analyze_atari5200_header(rom_data):
    """Extract Atari 5200 title from ROM end"""
    if len(rom_data) < 32:
        return {}
    
    try:
        # Check last 32 bytes for ASCII title
        end_data = rom_data[-32:]
        title_text = ""
        for i in range(len(end_data)):
            if 32 <= end_data[i] <= 126:  # Printable ASCII
                title_text += chr(end_data[i])
            else:
                if len(title_text) > 3:  # Found a reasonable title
                    break
                title_text = ""
        
        rom_size = len(rom_data)
        banking_type = "Unknown"
        if rom_size == 4096:
            banking_type = "4K"
        elif rom_size == 8192:
            banking_type = "8K"
        elif rom_size == 16384:
            banking_type = "16K"
        elif rom_size == 32768:
            banking_type = "32K"
        elif rom_size == 40960:
            banking_type = "40K"
        
        result = {'banking_type': banking_type}
        if title_text.strip():
            result['rom_title'] = title_text.strip()
        
        return result
    except:
        return {}

def analyze_sega32x_header(rom_data):
    """Extract Sega 32X header metadata"""
    if len(rom_data) < 0x200:
        return {}
    
    header = rom_data[0x100:0x200]
    
    if header[0:8] != b'SEGA 32X':
        return {}
    
    try:
        copyright = header[0x10:0x20].decode('ascii', errors='ignore').rstrip('\x00 ')
        domestic_title = header[0x20:0x50].decode('ascii', errors='ignore').rstrip('\x00 ')
        overseas_title = header[0x50:0x80].decode('ascii', errors='ignore').rstrip('\x00 ')
        product_id = header[0x83:0x8B].decode('ascii', errors='ignore').rstrip('\x00 ')
        rom_size = struct.unpack('>I', header[0x84:0x88])[0] if len(header) >= 0x88 else 0
        region_codes = header[0xA0:0xA4].decode('ascii', errors='ignore').rstrip('\x00 ')
        
        return {
            'copyright': copyright,
            'domestic_title': domestic_title,
            'overseas_title': overseas_title,
            'product_id': product_id,
            'rom_size': str(rom_size),
            'region_codes': region_codes
        }
    except:
        return {}

def analyze_colevision_header(rom_data):
    """Extract ColecoVision header metadata"""
    if len(rom_data) < 0x50:
        return {}
    
    if not (rom_data[0] == 0xAA and rom_data[1] == 0x55):
        return {}
    
    try:
        start_address = struct.unpack('<H', rom_data[2:4])[0]
        
        # Look for ASCII text in header region
        title_text = ""
        copyright_text = ""
        
        for start in [0x20, 0x30, 0x40]:
            if start + 16 <= len(rom_data):
                text = rom_data[start:start+16].decode('ascii', errors='ignore').rstrip('\x00 ')
                if text and len(text) > 3:
                    if not title_text:
                        title_text = text
                    elif not copyright_text and text != title_text:
                        copyright_text = text
        
        result = {
            'start_address': f"0x{start_address:04x}",
            'magic_bytes': 'AA55'
        }
        
        if title_text:
            result['internal_title'] = title_text
        if copyright_text:
            result['copyright'] = copyright_text
        
        return result
    except:
        return {}

def analyze_nintendo_fds_header(rom_data):
    """Extract Nintendo FDS header metadata"""
    if len(rom_data) < 24:
        return {}
    
    if rom_data[1:15] != b'*NINTENDO-HVC*':
        return {}
    
    try:
        manufacturer_id = rom_data[15]
        game_name = rom_data[16:19].decode('ascii', errors='ignore')
        game_type = rom_data[20]
        revision = rom_data[21]
        side_number = rom_data[22] 
        disk_number = rom_data[23]
        
        return {
            'manufacturer_id': f"0x{manufacturer_id:02x}",
            'game_code': game_name,
            'game_type': f"0x{game_type:02x}",
            'revision': str(revision),
            'side_number': str(side_number),
            'disk_number': str(disk_number)
        }
    except:
        return {}

def analyze_vectrex_header(rom_data):
    """Extract Vectrex header metadata"""
    if len(rom_data) < 32:
        return {}
    
    try:
        # Look for copyright and title in first 32 bytes
        header_text = rom_data[0:32].decode('ascii', errors='ignore')
        
        copyright_year = ""
        game_title = ""
        publisher = ""
        
        # Common patterns: "g GCE 1982", "g WEB 1983", etc.
        if 'GCE' in header_text:
            publisher = 'GCE'
        elif 'WEB' in header_text:
            publisher = 'Web Entertainment'
        
        # Extract year (4 consecutive digits)
        import re
        year_match = re.search(r'19\d{2}', header_text)
        if year_match:
            copyright_year = year_match.group()
        
        # Try to extract title (printable ASCII after known patterns)
        title_start = max(header_text.find('GCE'), header_text.find('WEB'), 0) + 8
        if title_start < len(header_text):
            potential_title = header_text[title_start:].strip('\x00 ')
            if potential_title and len(potential_title) > 2:
                game_title = potential_title[:16]  # Limit length
        
        result = {}
        if copyright_year:
            result['copyright_year'] = copyright_year
        if publisher:
            result['publisher'] = publisher
        if game_title:
            result['internal_title'] = game_title
        
        return result
    except:
        return {}

def analyze_pcengine_header(rom_data):
    """Extract PC Engine header metadata"""
    try:
        rom_size = len(rom_data)
        banking_type = "Unknown"
        
        if rom_size <= 0x20000:  # 128KB
            banking_type = "No banking"
        elif rom_size <= 0x40000:  # 256KB
            banking_type = "2Mbit"
        elif rom_size <= 0x80000:  # 512KB
            banking_type = "4Mbit"
        elif rom_size <= 0x100000:  # 1MB
            banking_type = "8Mbit"
        else:
            banking_type = "Large ROM"
        
        result = {'banking_type': banking_type}
        
        # Look for NEC signature around offset 0x17
        if len(rom_data) > 0x20:
            if b'NEC' in rom_data[0x10:0x20]:
                result['nec_signature'] = 'Present'
        
        return result
    except:
        return {}

def analyze_sg1000_header(rom_data):
    """Extract SG-1000 text information"""
    if len(rom_data) < 1024:
        return {}
    
    try:
        # Look for ASCII text in first 2KB that might be title/info
        search_region = rom_data[0:2048]
        text_info = search_region.decode('ascii', errors='ignore')
        
        # Look for common patterns
        title = ""
        version = ""
        year = ""
        
        # Extract version info (VERSION, VER, V.)
        import re
        version_match = re.search(r'VERSION\s*[\d.]+|VER\s*[\d.]+|V\.[\d.]+', text_info, re.IGNORECASE)
        if version_match:
            version = version_match.group().strip()
        
        # Extract year
        year_match = re.search(r'19\d{2}|20\d{2}', text_info)
        if year_match:
            year = year_match.group()
        
        # Extract potential title (uppercase words)
        title_matches = re.findall(r'[A-Z][A-Z\s]{4,20}[A-Z]', text_info)
        if title_matches:
            # Pick the most reasonable looking title
            for match in title_matches:
                if 'COPYRIGHT' not in match and 'VERSION' not in match:
                    title = match.strip()
                    break
        
        result = {}
        if title:
            result['rom_title'] = title
        if version:
            result['version_info'] = version
        if year:
            result['copyright_year'] = year
        
        return result
    except:
        return {}

def analyze_msx_header(rom_data):
    """Extract MSX ROM type and mapper information"""
    if len(rom_data) < 16:
        return {}
    
    try:
        rom_size = len(rom_data)
        
        # Determine mapper type based on size and first bytes
        mapper_type = "Unknown"
        rom_signature = ""
        
        if rom_data[0:2] == b'AB':
            rom_signature = "AB"
            if rom_size <= 0x8000:  # 32KB
                mapper_type = "ROM"
            else:
                mapper_type = "ASCII8/16"
        elif rom_data[0:2] == b'CD':
            rom_signature = "CD"
            mapper_type = "Konami"
        
        start_address = struct.unpack('<H', rom_data[2:4])[0] if len(rom_data) >= 4 else 0
        
        result = {
            'mapper_type': mapper_type,
            'rom_size_kb': str(rom_size // 1024)
        }
        
        if rom_signature:
            result['rom_signature'] = rom_signature
        if start_address:
            result['start_address'] = f"0x{start_address:04x}"
        
        return result
    except:
        return {}

def analyze_atari_lynx_header(rom_data):
    """Extract Atari Lynx LNX header metadata"""
    if len(rom_data) < 64:
        return {}
    
    header = rom_data[:64]
    magic = header[0:4]
    if magic != b'LYNX':
        return {}
    
    try:
        page_size_bank0 = struct.unpack('<H', header[4:6])[0]
        page_size_bank1 = struct.unpack('<H', header[6:8])[0]
        version = struct.unpack('<H', header[8:10])[0]
        cartname = header[10:42].decode('ascii', errors='ignore').rstrip('\x00 ')
        manufname = header[42:58].decode('ascii', errors='ignore').rstrip('\x00 ')
        rotation = header[58]
        
        return {
            'page_size_bank0': str(page_size_bank0),
            'page_size_bank1': str(page_size_bank1),
            'header_version': str(version),
            'cartridge_name': cartname,
            'manufacturer': manufname,
            'rotation': str(rotation)
        }
    except:
        return {}

def analyze_genesis_header(rom_data):
    """Extract Genesis header metadata"""
    if len(rom_data) < 0x200:
        return {}
    
    header = rom_data[0x100:0x200]
    
    # Look for SEGA magic with improved detection
    magic_found = False
    for offset in [0x00, 0x80]:
        if offset + 4 <= len(header) and header[offset:offset+4] in [b'SEGA']:
            magic_found = True
            break
    
    if not magic_found:
        return {}
    
    try:
        system_type = header[0x00:0x10].decode('ascii', errors='ignore').rstrip('\x00 ')
        publisher = header[0x10:0x20].decode('ascii', errors='ignore').rstrip('\x00 ')
        domestic_title = header[0x20:0x50].decode('ascii', errors='ignore').rstrip('\x00 ')
        overseas_title = header[0x50:0x80].decode('ascii', errors='ignore').rstrip('\x00 ')
        software_type = header[0x80:0x82].decode('ascii', errors='ignore')
        product_id = header[0x83:0x8B].decode('ascii', errors='ignore').rstrip('\x00 ')
        checksum = struct.unpack('>H', header[0x8E:0x90])[0]
        device_support = header[0x90:0xA0].decode('ascii', errors='ignore').rstrip('\x00 ')
        
        return {
            'system_type': system_type,
            'publisher': publisher,
            'domestic_title': domestic_title,
            'overseas_title': overseas_title,
            'software_type': software_type,
            'product_id': product_id,
            'rom_checksum': f"{checksum:04x}",
            'device_support': device_support
        }
    except:
        return {}

def analyze_game_gear_header(rom_data):
    """Extract Game Gear TMR SEGA header metadata"""
    tmr_locations = [0x7FF0, 0x3FF0, 0x1FF0]
    
    for location in tmr_locations:
        if location + 16 <= len(rom_data):
            signature = rom_data[location:location+8]
            if signature == b'TMR SEGA':
                try:
                    checksum_bytes = rom_data[location+10:location+12]
                    checksum = struct.unpack('>H', checksum_bytes)[0]
                    product_code = rom_data[location+12:location+15].decode('ascii', errors='ignore')
                    version = rom_data[location+15]
                    
                    return {
                        'signature_location': f"0x{location:04x}",
                        'rom_checksum': f"{checksum:04x}",
                        'product_code': product_code,
                        'version': str(version)
                    }
                except:
                    continue
    
    return {}

def analyze_wonderswan_header(rom_data):
    """Extract WonderSwan header metadata"""
    if len(rom_data) < 10:
        return {}
    
    try:
        header = rom_data[-10:]
        publisher = header[0]
        color_flag = header[1]
        cart_id = header[2]
        rom_size = header[3]
        eeprom_size = header[4]
        rtc_flag = header[5]
        checksum = struct.unpack('<H', header[8:10])[0]
        
        return {
            'publisher_code': f"0x{publisher:02x}",
            'color_support': 'Color' if color_flag else 'Monochrome',
            'cartridge_id': f"0x{cart_id:02x}",
            'rom_size_code': f"0x{rom_size:02x}",
            'eeprom_size_code': f"0x{eeprom_size:02x}",
            'rtc_present': str(bool(rtc_flag)),
            'header_checksum': f"{checksum:04x}"
        }
    except:
        return {}

def analyze_neo_geo_pocket_header(rom_data):
    """Extract Neo Geo Pocket header metadata"""
    if len(rom_data) < 0x30:
        return {}
    
    try:
        header = rom_data[:0x40]
        license_str = header[0x00:0x1C]
        if b'LICENSED BY SNK CORPORATION' not in license_str:
            return {}
        
        system_type = header[0x22]
        game_title = header[0x24:0x30].decode('ascii', errors='ignore').rstrip('\x00 ')
        
        return {
            'license': 'LICENSED BY SNK CORPORATION',
            'system_type': 'NGP' if system_type == 0x00 else 'NGPC',
            'internal_title': game_title
        }
    except:
        return {}

def analyze_atari2600_header(rom_data):
    """Extract Atari 2600 metadata based on ROM patterns"""
    file_size = len(rom_data)
    
    # ROM size patterns from GameID.py
    rom_sizes = {
        2048: {'rom_type': '2K', 'banking_scheme': 'Standard 2K'},
        4096: {'rom_type': '4K', 'banking_scheme': 'Standard 4K'},
        8192: {'rom_type': '8K', 'banking_scheme': 'F8 (Atari)'},
        12288: {'rom_type': '12K', 'banking_scheme': 'FA (CBS)'},
        16384: {'rom_type': '16K', 'banking_scheme': 'F6 (Atari)'},
        32768: {'rom_type': '32K', 'banking_scheme': 'F4 (Atari)'},
        65536: {'rom_type': '64K', 'banking_scheme': 'F0 (Megaboy)'},
        131072: {'rom_type': '128K', 'banking_scheme': 'MC (Megacart)'},
        262144: {'rom_type': '256K', 'banking_scheme': 'EPC (Pesco)'},
        524288: {'rom_type': '512K', 'banking_scheme': 'EPC (Pesco)'}
    }
    
    result = {}
    
    # Determine ROM type and banking scheme
    if file_size in rom_sizes:
        info = rom_sizes[file_size]
        result['rom_type'] = info['rom_type']
        result['banking_scheme'] = info['banking_scheme']
    else:
        result['rom_type'] = f'{file_size} bytes'
        result['banking_scheme'] = 'Unknown'
    
    # Check for SuperChip RAM (8K, 16K, 32K ROMs)
    if file_size in [8192, 16384, 32768] and len(rom_data) >= 256:
        first_256_bytes = rom_data[:256]
        if all(b == 0x00 for b in first_256_bytes) or all(b == 0xFF for b in first_256_bytes):
            result['superchip_ram'] = 'Detected'
        else:
            result['superchip_ram'] = 'None'
    
    return result

def get_header_analyzer(system_name):
    """Return appropriate header analyzer function for system"""
    analyzers = {
        'Atari2600': analyze_atari2600_header,
        'Atari7800': analyze_atari7800_header,
        'Atari5200': analyze_atari5200_header,
        'AtariLynx': analyze_atari_lynx_header,
        'Genesis': analyze_genesis_header,
        'Sega32X': analyze_sega32x_header,
        'GameGear': analyze_game_gear_header,
        'MasterSystem': analyze_game_gear_header,
        'WonderSwan': analyze_wonderswan_header,
        'WonderSwanColor': analyze_wonderswan_header,
        'NGP': analyze_neo_geo_pocket_header,
        'NGPC': analyze_neo_geo_pocket_header,
        'ColecoVision': analyze_colevision_header,
        'NintendoFDS': analyze_nintendo_fds_header,
        'Vectrex': analyze_vectrex_header,
        'PCEngine': analyze_pcengine_header,
        'PCEngineSuperGrafx': analyze_pcengine_header,
        'SegaSG1000': analyze_sg1000_header,
        'MSX': analyze_msx_header,
        'MSX2': analyze_msx_header,
    }
    return analyzers.get(system_name, None)

def build_gamedb(system_name, directory_name, extensions, no_intro_path):
    """Build GameDB for a specific system with header analysis"""
    
    # Output TSV file
    output_file = f"{system_name}.data.tsv"
    
    # Check if database already exists
    if os.path.exists(output_file):
        print(f"Skipping {system_name} - database already exists: {output_file}")
        return True
    
    system_dir = os.path.join(no_intro_path, directory_name)
    
    if not os.path.exists(system_dir):
        print(f"Warning: {system_name} directory not found: {system_dir}")
        return False
    
    print(f"Processing {system_name} ROMs from: {system_dir}")
    
    # Get header analyzer for this system
    header_analyzer = get_header_analyzer(system_name)
    
    # Determine header fields by analyzing first ROM (if analyzer exists)
    header_fields = set()
    if header_analyzer:
        for filename in sorted(os.listdir(system_dir)):
            if any(filename.lower().endswith(ext) for ext in extensions):
                sample_path = os.path.join(system_dir, filename)
                try:
                    with open(sample_path, 'rb') as f:
                        sample_data = f.read()
                    sample_metadata = header_analyzer(sample_data)
                    header_fields.update(sample_metadata.keys())
                    if header_fields:  # Found some fields, use this as template
                        break
                except:
                    continue
    
    # Create header with base fields + system-specific fields
    base_fields = ["ID", "title", "region", "release_name"]
    sorted_header_fields = sorted(header_fields)
    header = base_fields + sorted_header_fields
    
    entries = []
    entries.append(header)
    
    if header_analyzer and sorted_header_fields:
        print(f"  Enhanced with metadata: {', '.join(sorted_header_fields)}")
    
    rom_count = 0
    
    # Process all ROM files
    for filename in sorted(os.listdir(system_dir)):
        if any(filename.lower().endswith(ext) for ext in extensions):
            rom_path = os.path.join(system_dir, filename)
            
            try:
                # Read ROM file and calculate CRC32
                with open(rom_path, 'rb') as f:
                    rom_data = f.read()
                
                crc32_checksum = crc32(rom_data) & 0xffffffff
                crc32_hex = f"{crc32_checksum:08x}"
                
                # Clean up title and determine region
                title_clean = clean_title(filename)
                region = determine_region(filename)
                
                # Extract header metadata
                metadata = header_analyzer(rom_data) if header_analyzer else {}
                
                # Create entry with base fields
                entry = [crc32_hex, title_clean, region, filename]
                
                # Add system-specific fields in same order as header
                for field in sorted_header_fields:
                    entry.append(metadata.get(field, ''))
                
                entries.append(entry)
                rom_count += 1
                
                if rom_count % 50 == 0:
                    print(f"  Processed {rom_count} ROMs...")
                
            except Exception as e:
                print(f"  Error processing {filename}: {e}")
                continue
    
    if rom_count == 0:
        print(f"  No ROMs found for {system_name}")
        return False
    
    # Write TSV file
    print(f"  Writing {len(entries)-1} entries to {output_file}")
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        for entry in entries:
            f.write('\t'.join(entry) + '\n')
    
    print(f"  ✓ {system_name}: {rom_count} games")
    return True

def main():
    """Main function to build all GameDBs"""
    
    # Path to No-Intro collection
    no_intro_path = "/mnt/z/Downloads/_JDownloader_/No-Intro"
    
    if not os.path.exists(no_intro_path):
        print(f"Error: No-Intro path not found: {no_intro_path}")
        sys.exit(1)
    
    # Define systems to process
    systems = [
        # High priority systems
        ("Atari2600", "Atari - 2600", ['.a26', '.bin']),
        ("Atari5200", "Atari - 5200", ['.a52', '.bin']),
        ("Atari7800", "Atari - 7800 (A78)", ['.a78']),
        ("AtariJaguar", "Atari - Jaguar (J64)", ['.j64', '.jag', '.rom', '.abs', '.cof']),
        ("AtariLynx", "Atari - Lynx (LNX)", ['.lnx', '.lyx']),
        ("WonderSwan", "Bandai - WonderSwan", ['.ws']),
        ("WonderSwanColor", "Bandai - WonderSwan Color", ['.wsc']),
        ("ColecoVision", "Coleco - ColecoVision", ['.col']),
        ("PCEngine", "NEC - PC Engine - TurboGrafx-16", ['.pce']),
        ("PCEngineSuperGrafx", "NEC - PC Engine SuperGrafx", ['.sgx']),
        ("GameGear", "Sega - Game Gear", ['.gg']),
        ("MasterSystem", "Sega - Master System - Mark III", ['.sms']),
        ("Sega32X", "Sega - 32X", ['.32x']),
        
        # Medium priority systems
        ("NintendoFDS", "Nintendo - Family Computer Disk System (FDS)", ['.fds']),
        ("SegaSG1000", "Sega - SG-1000", ['.sg']),
        ("Vectrex", "GCE - Vectrex", ['.vec']),
        ("NGP", "SNK - NeoGeo Pocket", ['.ngp']),
        ("NGPC", "SNK - NeoGeo Pocket Color", ['.ngc']),
        ("GameWatch", "Nintendo - Game & Watch", ['.bin']),
        ("C64", "Commodore - Commodore 64", ['.crt', '.prg', '.d64', '.bin']),
        ("AtariST", "Atari - ST", ['.st', '.stx', '.msa', '.ipf']),
        ("Satellaview", "Nintendo - Satellaview", ['.bs']),
        ("N64DD", "Nintendo - Nintendo 64DD", ['.ndd']),
        ("SufamiTurbo", "Nintendo - Sufami Turbo", ['.st']),
        ("SegaPico", "Sega - PICO", ['.md']),
        ("Amiga", "Commodore - Amiga", ['.adf', '.adz', '.dms', '.ipf']),
        ("MSX", "Microsoft - MSX", ['.rom']),
        ("MSX2", "Microsoft - MSX2", ['.rom']),
        
        # Low priority systems
        ("CasioLoopy", "Casio - Loopy (BigEndian)", ['.bin']),
        ("GameCom", "Tiger - Game.com", ['.tgc']),
        ("Supervision", "Watara - Supervision", ['.sv']),
        ("MegaDuck", "Welback - Mega Duck", ['.bin']),
        ("FMTowns", "Fujitsu - FM Towns (HDM)", ['.hdm']),
        ("PC98", "NEC - PC-98", ['.hdm']),
    ]
    
    success_count = 0
    total_count = len(systems)
    
    print(f"Building GameDBs for {total_count} systems...\n")
    
    for i, (system_name, directory_name, extensions) in enumerate(systems, 1):
        print(f"[{i}/{total_count}] Building {system_name}...")
        if build_gamedb(system_name, directory_name, extensions, no_intro_path):
            success_count += 1
        print()
    
    print(f"Completed: {success_count}/{total_count} systems processed successfully")

if __name__ == "__main__":
    main()