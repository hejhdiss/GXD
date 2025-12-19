# GXD Compression Utility

![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)
![Version](https://img.shields.io/badge/version-0.0.0a2-orange.svg)
![Status](https://img.shields.io/badge/status-alpha-yellow.svg)

A high-performance block-based compression utility with parallel processing, integrity verification, and random-access capabilities.

**Note:** This is an alpha version (v0.0.0a2). APIs and file formats may change in future releases.

## Community Project

GXD is a community-driven project, built for the community and by the community. Community contributions are highly valued and essential to the growth and improvement of this project. Whether you're reporting bugs, suggesting features, improving documentation, or submitting code, your input matters and helps make GXD better for everyone.

## Features

| Feature | Description |
|---------|-------------|
| Multiple Algorithms | Zstandard, LZ4, Brotli, and uncompressed modes |
| Parallel Processing | Multi-threaded compression/decompression using all CPU cores |
| Block-Level Integrity | SHA-256 checksums for each data block |
| Random Access | Seek and extract specific byte ranges without full decompression |
| Flexible Verification | Optional integrity checking for performance optimization |
| Text Mode | Direct UTF-8 text output to stdout |
| Progress Tracking | Visual progress bars with tqdm (fallback to simple indicators) |

## Requirements

| Category | Dependencies |
|----------|-------------|
| Core | Python 3.6+ |
| Optional | `zstd` (Zstandard compression), `lz4` (LZ4 compression), `brotli` (Brotli compression), `tqdm` (progress bars) |

### Installation

```bash
# Install all optional dependencies
pip install zstandard lz4 brotli tqdm

# Or install selectively
pip install zstandard tqdm  # Minimal recommended setup
```

## Basic Usage

### Compress a File
```bash
python gxd.py compress input.bin output.gxd
```

### Decompress a File
```bash
python gxd.py decompress input.gxd -o output.bin
```

### Extract Specific Range
```bash
python gxd.py seek input.gxd --offset 1mb --length 512kb -o chunk.bin
```

## Command Reference

### Compression Options

| Option | Values | Default | Description |
|--------|--------|---------|-------------|
| `--algo` | `zstd`, `lz4`, `brotli`, `none` | `zstd` | Compression algorithm to use |
| `--block-size` | `512kb`, `1mb`, `2mb`, etc. | `1024kb` | Size of data blocks |
| `--zstd-ratio` | `1-22` | `3` | Zstandard compression level (only applies when using zstd) |
| `--threads` | `1-128` | All CPU cores | Number of parallel threads |
| `--block-verify` | - | Enabled | Enable SHA-256 per-block integrity checks |
| `--no-verify` | - | - | Disable all integrity checks for faster performance |

**Important CLI Behavior Notes:**

1. **Algorithm-Specific Parameters**: The `--zstd-ratio` parameter only affects compression when using the `zstd` algorithm. If you specify a different algorithm with `--zstd-ratio`, the tool will display a warning and ignore the ratio parameter. 

   Example:
   ```bash
   # This will show a warning that --zstd-ratio is being ignored
   python gxd.py compress input.txt output.gxd --algo lz4 --zstd-ratio 10
   ```
   
   Output: `[!] Warning: --zstd-ratio (10) is ignored when using algorithm 'lz4'. it only applies to 'zstd'.`

2. **Size Parsing**: Invalid size formats will cause the program to exit with an error message. Valid formats include: `1024` (bytes), `512kb`, `1mb`, `2gb`.

3. **Block Size Validation**: Block size must be greater than 0, otherwise the program will exit with an error.

### Decompression Options

| Option | Description |
|--------|-------------|
| `-o`, `--output` | Path for the restored file (default: same as input minus .gxd) |
| `--text` | Print decompressed data as UTF-8 text to stdout |
| `--threads` | Number of parallel threads (default: all CPU cores) |
| `--block-verify` | Verify integrity using SHA-256 block hashes (enabled by default) |
| `--no-verify` | Disable integrity checks for maximum speed |

### Seek Options

| Option | Description |
|--------|-------------|
| `-o`, `--output` | Path to save the extracted chunk (default: stdout) |
| `--offset` | Byte offset to start reading (e.g., `0`, `1mb`, `512kb`) |
| `--length` | Number of bytes to extract (e.g., `100`, `2mb`, default: until EOF) |
| `--text` | Print extracted chunk as UTF-8 text to stdout |
| `--threads` | Number of parallel threads (default: all CPU cores) |
| `--block-verify` | Verify hashes of accessed blocks (enabled by default) |
| `--no-verify` | Disable integrity checks |

## Size Notation

| Format | Description |
|--------|-------------|
| `1024` | Bytes |
| `512kb` | Kilobytes |
| `10mb` | Megabytes |
| `1gb` | Gigabytes |

## File Format

GXD uses a custom archive format:

```
[MAGIC: "GXDINC"]
[Compressed Block 1]
[Compressed Block 2]
...
[Compressed Block N]
[JSON Metadata]
[Metadata Length: 8 bytes]
[MAGIC: "GXDINC"]
```

### Metadata Structure

```json
{
  "version": "0.0.0a2",
  "algo": "zstd",
  "global_hash": "sha256_hash_of_original_file",
  "blocks": [
    {
      "id": 0,
      "start": 6,
      "size": 12345,
      "orig_size": 1048576,
      "hash": "block_sha256_hash"
    }
  ]
}
```

## Code Signing and Verification

The project includes a digital signature tool for verifying script integrity.

| Command | Description |
|---------|-------------|
| `python signer.py sign gxd.py` | Sign a Python file with default author |
| `python signer.py sign gxd.py --author "Your Name"` | Sign with custom author |
| `python signer.py verify gxd.py` | Verify a signed file's integrity |

## Testing

Run the comprehensive test suite:

```bash
python test.py
```

### Test Coverage

| Test | Description |
|------|-------------|
| Full cycle permutations | Compression/decompression for all algorithms |
| Corrupt footer magic | Detection of tampered magic bytes |
| File truncation | Handling of incomplete files |
| Checksum mismatch | Detection of corrupted data blocks |
| Unsupported algorithm | Handling of invalid metadata |
| Text mode verification | UTF-8 output functionality |
| Seek with corruption | Random access error handling |

## Performance Guidelines

### Algorithm Selection

| Algorithm | Speed | Compression Ratio | Best For |
|-----------|-------|-------------------|----------|
| `zstd` | Balanced | Good | General purpose (default) |
| `lz4` | Fastest | Lower | Maximum speed |
| `brotli` | Slower | Best | Maximum compression |
| `none` | N/A | None | Integrity verification only |

### Block Size Recommendations

| Block Size | Compression Ratio | Random Access | Use Case |
|------------|-------------------|---------------|----------|
| 512KB-1MB | Lower | Excellent | Frequent random access |
| 1MB (default) | Balanced | Good | General purpose |
| 2-4MB | Better | Lower | Large sequential files |

### Threading

| Setting | Description |
|---------|-------------|
| Default | Uses all available CPU cores |
| Custom | Use `--threads N` to limit resource usage |

### Verification Options

| Option | Performance | Security |
|--------|-------------|----------|
| `--block-verify` | Slower | High integrity checking |
| `--no-verify` | Fastest | No integrity verification |

## Security Features

| Feature | Description |
|---------|-------------|
| SHA-256 Integrity Checks | Per-block and global file hashing |
| Tamper Detection | Automatic detection of corrupted or modified archives |
| Metadata Validation | Structural integrity verification |
| Digital Signatures | Optional source code signing with signer.py |

## Examples

### Compress a Large Dataset
```bash
python gxd.py compress dataset.bin dataset.gxd \
  --algo zstd \
  --block-size 2mb \
  --zstd-ratio 10 \
  --threads 16
```

### Extract Log File Range
```bash
# Get last 100KB of a compressed log file
python gxd.py seek app.log.gxd \
  --offset 9.9mb \
  --length 100kb \
  --text
```

### Quick Archive Verification
```bash
# Verify integrity without full extraction
python gxd.py decompress data.gxd --no-verify > /dev/null
```

## Contributing

GXD is a community-driven project - your contributions are what make it thrive! Whether you're fixing bugs, adding features, improving documentation, or sharing ideas, every contribution matters and is greatly appreciated.

### How to Contribute

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Install dependencies: `pip install zstandard lz4 brotli tqdm`
4. Make your changes and test them: `python test.py`
5. Sign your code (optional): `python signer.py sign your_file.py`
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Contribution Ideas

| Area | Ideas |
|------|-------|
| Features | New compression algorithms, improved performance optimizations |
| Documentation | Tutorials, use case examples, translations |
| Testing | Additional test cases, platform-specific testing |
| Bug Reports | Issue identification, reproduction steps |
| Code Quality | Refactoring, type hints, performance profiling |

All contributions, no matter how small, help improve GXD for the entire community.

## License

```
GXD Compression Utility
Copyright (C) 2025 @hejhdiss (Muhammed Shafin p)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
```

See [LICENSE.txt](LICENSE.txt) for the full license text.

## Author

**@hejhdiss (Muhammed Shafin p)**

- GitHub: [@hejhdiss](https://github.com/hejhdiss)

## Acknowledgments

- Built with Python's `ProcessPoolExecutor` for parallel processing
- Compression powered by Zstandard, LZ4, and Brotli libraries
- Progress visualization by tqdm

---

**Note**: This is an alpha release (v0.0.0a2). APIs and file formats may change in future versions. Community feedback and contributions are essential to making GXD stable and feature-complete.
