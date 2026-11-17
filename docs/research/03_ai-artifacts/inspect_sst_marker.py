"""Read LevelDB table blocks and locate exact experiment markers.

Not a complete IndexedDB parser: no key semantics or sequence resolution.
Masked CRC32C is checked before decoding each block.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct


def crc32c(data):
    crc = 0xffffffff
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (0x82f63b78 if crc & 1 else 0)
    return crc ^ 0xffffffff


def varint(data, pos=0):
    value = 0
    for shift in range(0, 70, 7):
        byte = data[pos]
        pos += 1
        value |= (byte & 127) << shift
        if byte < 128:
            return value, pos
    raise ValueError('invalid varint')


def snappy(data):
    size, pos = varint(data)
    out = bytearray()
    while pos < len(data):
        tag = data[pos]; pos += 1
        kind = tag & 3
        if kind == 0:
            length = tag >> 2
            if length < 60:
                length += 1
            else:
                n = length - 59
                length = int.from_bytes(data[pos:pos+n], 'little') + 1
                pos += n
            out.extend(data[pos:pos+length]); pos += length
        else:
            if kind == 1:
                length = 4 + ((tag >> 2) & 7)
                offset = ((tag & 224) << 3) | data[pos]; pos += 1
            elif kind == 2:
                length = 1 + (tag >> 2)
                offset = int.from_bytes(data[pos:pos+2], 'little'); pos += 2
            else:
                length = 1 + (tag >> 2)
                offset = int.from_bytes(data[pos:pos+4], 'little'); pos += 4
            if not 0 < offset <= len(out):
                raise ValueError('invalid Snappy offset')
            for _ in range(length):
                out.append(out[-offset])
        if len(out) > size:
            raise ValueError('Snappy length overflow')
    if len(out) != size:
        raise ValueError('Snappy size mismatch')
    return bytes(out)


def block(data, offset, size):
    raw = data[offset:offset+size]
    kind = data[offset+size]
    checksum = crc32c(raw + bytes([kind]))
    masked = (((checksum >> 15) | (checksum << 17)) + 0xa282ead8) & 0xffffffff
    if struct.unpack_from('<I', data, offset+size+1)[0] != masked:
        raise ValueError('LevelDB block CRC32C mismatch')
    if kind == 0:
        return raw, kind
    if kind == 1:
        return snappy(raw), kind
    raise ValueError('unsupported compression type')


def entries(data):
    restart_count = struct.unpack_from('<I', data, len(data)-4)[0]
    end = len(data) - 4 - restart_count * 4
    pos = 0
    key = b''
    while pos < end:
        shared, pos = varint(data, pos)
        new, pos = varint(data, pos)
        size, pos = varint(data, pos)
        key = key[:shared] + data[pos:pos+new]; pos += new
        value = data[pos:pos+size]; pos += size
        yield key, value


def inspect(path, marker):
    data = path.read_bytes()
    if data[-8:] != bytes.fromhex('57fb808b247547db'):
        raise ValueError('not a LevelDB table')
    footer = data[-48:-8]
    _, pos = varint(footer)
    _, pos = varint(footer, pos)
    index_off, pos = varint(footer, pos)
    index_size, _ = varint(footer, pos)
    index, _ = block(data, index_off, index_size)
    hits = []
    for _, handle in entries(index):
        off, pos = varint(handle)
        size, _ = varint(handle, pos)
        decoded, kind = block(data, off, size)
        for encoding in ('utf-8', 'utf-16-le'):
            needle = marker.encode(encoding)
            position = decoded.find(needle)
            if position < 0:
                continue
            hits.append({'file': path.name, 'source_sha256': hashlib.sha256(data).hexdigest(),
                         'source_length': len(data), 'block_file_offset': off,
                         'block_compressed_length': size, 'compression_type': kind,
                         'decoded_block_offset': position, 'decoded_block_sha256': hashlib.sha256(decoded).hexdigest(),
                         'marker': marker, 'encoding': encoding, 'count_in_block': decoded.count(needle),
                         'exact_marker_hex': decoded[position:position+len(needle)].hex(' '),
                         'block_crc32c': 'verified',
                         'limitation': 'Decoded block offset is not a source file offset. Key semantics not validated.'})
    return hits


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = {'method': 'LevelDB SST block decoding; not full logical record reconstruction', 'hits': [], 'errors': []}
    for path in args.directory.glob('*.ldb'):
        try:
            for marker in ('AIART-20261116-UNSENT-7D3F', 'AIART-20261116-SENT-9A2C'):
                result['hits'].extend(inspect(path, marker))
        except Exception as exc:
            result['errors'].append({'file': path.name, 'error': str(exc)})
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=True, indent=2))
