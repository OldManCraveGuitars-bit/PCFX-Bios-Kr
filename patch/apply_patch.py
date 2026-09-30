#!/usr/bin/env python3
"""Apply PCFX-Bios-Kr 1.0 to the supported original BIOS, without overwriting files."""
import argparse
import hashlib
from pathlib import Path

SOURCE_SHA256 = '4b44ccf5d84cc83daa2e6a2bee00fdafa14eb58bdf5859e96d8861a891675417'
PATCH_SHA256 = '04c949c0793cb4893c89bed53e0c8d455deddd532d187328eda58a5f9fc98402'
TARGET_SHA256 = 'd77362761c22ebb62ab3d8ba8d684a9469b863ba8d1ef9a8658b26d8ce41063b'
ROM_SIZE = 1048576
FONT_REGIONS = [(0x95950,229186),(0xCD894,129086),(0xED0D4,4096),
                (0xEE0D4,3072),(0xEECD4,2048),(0xEF4D4,3072)]

def sha256(data):
    return hashlib.sha256(data).hexdigest()

def apply_ips(source, patch):
    if not patch.startswith(b'PATCH'):
        raise ValueError('Invalid IPS header.')
    result = bytearray(source)
    pos = 5
    while patch[pos:pos+3] != b'EOF':
        if pos + 5 > len(patch):
            raise ValueError('Truncated IPS record.')
        offset = int.from_bytes(patch[pos:pos+3], 'big')
        size = int.from_bytes(patch[pos+3:pos+5], 'big')
        pos += 5
        if size:
            if pos + size > len(patch):
                raise ValueError('Truncated IPS payload.')
            payload = patch[pos:pos+size]
            pos += size
        else:
            if pos + 3 > len(patch):
                raise ValueError('Truncated IPS RLE record.')
            size = int.from_bytes(patch[pos:pos+2], 'big')
            payload = patch[pos+2:pos+3] * size
            pos += 3
        if not size or offset + size > len(result):
            raise ValueError('IPS write is outside the supported BIOS.')
        result[offset:offset+size] = payload
    if pos + 3 != len(patch):
        raise ValueError('Unexpected bytes after IPS EOF.')
    return bytes(result)

def main():
    parser = argparse.ArgumentParser(description='PCFX-Bios-Kr 1.0 verified IPS applier')
    parser.add_argument('source', type=Path, help='Supported original pcfx.rom')
    parser.add_argument('output', type=Path, help='New output file; must not exist')
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise ValueError('Output already exists. Choose a new filename.')
        source = args.source.read_bytes()
        if len(source) != ROM_SIZE or sha256(source) != SOURCE_SHA256:
            raise ValueError('Unsupported BIOS. Use the original BIOS listed in INSTALL.txt.')
        patch = Path(__file__).with_name('PCFX-Bios-Kr-v1.0.ips').read_bytes()
        if sha256(patch) != PATCH_SHA256:
            raise ValueError('Patch checksum mismatch. Download the 1.0 package again.')
        result = apply_ips(source, patch)
        if len(result) != ROM_SIZE or sha256(result) != TARGET_SHA256:
            raise ValueError('Patched BIOS verification failed.')
        for start, size in FONT_REGIONS:
            if source[start:start+size] != result[start:start+size]:
                raise ValueError('Original font preservation check failed.')
        with args.output.open('xb') as stream:
            stream.write(result)
    except (OSError, ValueError) as error:
        parser.exit(1, f'Error: {error}\n')
    print(f'Created: {args.output}')
    print(f'SHA-256: {TARGET_SHA256}')
    print('All six original font regions are unchanged. Cold-boot your emulator.')

if __name__ == '__main__':
    main()
