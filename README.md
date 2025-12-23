# GXD Compression Utility

![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)
![Version](https://img.shields.io/badge/version-0.0.0a2-orange.svg)
![Status](https://img.shields.io/badge/status-alpha-yellow.svg)

A high-performance block-based compression utility with parallel processing, integrity verification, random-access capabilities, and smart algorithm selection.

**Note:** This is an alpha version (v0.0.0a2). APIs and file formats may change in future releases.

---

## What's New in This Version

### Auto Algorithm Selection
GXD now features an intelligent **auto mode** that automatically selects the best compression algorithm for each block based on data characteristics:
- Analyzes Shannon Entropy (0.0-8.0 scale) to measure data randomness
- Calculates zero-byte density and unique byte ratios
- Dynamically chooses between `lz4`, `zstd`, `brotli`, or `none` per block
- Per-block algorithm metadata stored in archive for accurate decompression

### Enhanced Metadata Tracking
Each compressed block now includes detailed metrics:
- **Entropy value**: Measures data randomness (0.0 = perfectly uniform, 8.0 = maximum randomness)
- **Compression time**: Per-block timing for performance analysis
- **Timestamp**: When each block was compressed
- **Algorithm used**: Actual algorithm applied (important for auto mode)

### File Attribute Preservation
GXD now preserves and restores original file attributes:
- File permissions (mode)
- Modification time (mtime)
- Access time (atime)
- User ID (uid) and Group ID (gid) on Unix systems
- Automatic restoration on decompression

### Archive Information Command
New `info` command provides comprehensive archive inspection:
- View global archive metadata (version, algorithm, total blocks)
- Display preserved file attributes
- List block overview with compression details
- Inspect specific block metadata by index

---

## Smart Algorithm Analysis (`algo.py`)

`algo.py` is a predictive utility designed to analyze your data before compression. It uses Shannon Entropy and data density metrics to recommend the most efficient algorithm for your specific files, helping you avoid "data expansion" where compression actually increases file size.

### Features

* **Predictive Modeling**: Automatically suggests `lz4`, `zstd`, `brotli`, or `none` based on data heuristics.
* **Entropy Analysis**: Calculates Shannon Entropy (0.0 to 8.0) to determine data randomness.
* **Efficiency Metrics**: Tracks zero-byte density and unique byte ratios.
* **Real-time Benchmarking**: Performs a test compression on blocks to report expected ratios and speeds (MB/s).

### Usage

```bash
python3 algo.py input_file.bin --block-size 1mb --zstd-ratio 3
```

### Analysis Metrics Reference

| Metric | Logic / Threshold | Recommended Action |
|--------|-------------------|-------------------|
| High Entropy | Entropy > 7.9 | Use `--algo none` (Data is likely already compressed/encrypted) |
| Sparse Data | Zeros > 40% or Entropy < 3.0 | Use `--algo lz4` for maximum speed |
| General Data | Entropy < 6.8 | Use `--algo zstd` (Default) |
| High Redundancy | High Unique Density | Use `--algo brotli` for best ratio |

### Understanding the Output

The utility provides a block-by-block summary:

* **Ratio**: The percentage of the original size (e.g., 70% means 30% savings).
* **Speed**: Estimated throughput in MB/s for the selected algorithm.
* **Status**: Displays `EXPANDED` if the compressed output is larger than the source.

---

## Community Project

GXD is a community-driven project, built for the community and by the community. Community contributions are highly valued and essential to the growth and improvement of this project. Whether you're reporting bugs, suggesting features, improving documentation, or submitting code, your input matters and helps make GXD better for everyone.

## Features

| Feature | Description |
|---------|-------------|
| Multiple Algorithms | Zstandard, LZ4, Brotli, and uncompressed modes |
| Auto Algorithm Selection | Intelligent per-block algorithm selection based on entropy analysis |
| Parallel Processing | Multi-threaded compression/decompression using all CPU cores |
| Block-Level Integrity | SHA-256 checksums for each data block |
| Random Access | Seek and extract specific byte ranges without full decompression |
| Flexible Verification | Optional integrity checking for performance optimization |
| Text Mode | Direct UTF-8 text output to stdout |
| File Attribute Preservation | Maintains permissions, timestamps, and ownership |
| Archive Inspection | View metadata and block details without extraction |
| Progress Tracking | Visual progress bars with tqdm (fallback to simple indicators) |
| Entropy Tracking | Per-block entropy metrics for compression analysis |

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

### Compress with Auto Algorithm Selection
```bash
python gxd.py compress input.bin output.gxd --algo auto
```

### Decompress a File
```bash
python gxd.py decompress input.gxd -o output.bin
```

### View Archive Information
```bash
python gxd.py info input.gxd
```

### Extract Specific Range
```bash
python gxd.py seek input.gxd --offset 1mb --length 512kb -o chunk.bin
```

## Command Reference

### Compression Options

| Option | Values | Default | Description |
|--------|--------|---------|-------------|
| `--algo` | `auto`, `zstd`, `lz4`, `brotli`, `none` | `zstd` | Compression algorithm to use |
| `--block-size` | `512kb`, `1mb`, `2mb`, etc. | `1024kb` | Size of data blocks |
| `--zstd-ratio` | `1-22` | `3` | Zstandard compression level (only applies when using zstd) |
| `--threads` | `1-128` | All CPU cores | Number of parallel threads |
| `--block-verify` | - | Enabled | Enable SHA-256 per-block integrity checks |
| `--no-verify` | - | - | Disable all integrity checks for faster performance |

**Important CLI Behavior Notes:**

1. **Auto Algorithm Mode**: When using `--algo auto`, GXD analyzes each block's entropy and data characteristics to select the optimal algorithm (lz4, zstd, brotli, or none). The chosen algorithm is stored per-block in the archive metadata.

2. **Algorithm-Specific Parameters**: The `--zstd-ratio` parameter only affects compression when using the `zstd` algorithm. If you specify a different algorithm with `--zstd-ratio`, the tool will display a warning and ignore the ratio parameter. 

   Example:
   ```bash
   # This will show a warning that --zstd-ratio is being ignored
   python gxd.py compress input.txt output.gxd --algo lz4 --zstd-ratio 10
   ```
   
   Output: `[!] Warning: --zstd-ratio (10) is ignored when using algorithm 'lz4'. it only applies to 'zstd'.`

3. **Size Parsing**: Invalid size formats will cause the program to exit with an error message. Valid formats include: `1024` (bytes), `512kb`, `1mb`, `2gb`.

4. **Block Size Validation**: Block size must be greater than 0, otherwise the program will exit with an error.

### Decompression Options

| Option | Description |
|--------|-------------|
| `-o`, `--output` | Path for the restored file (default: same as input minus .gxd) |
| `--text` | Print decompressed data as UTF-8 text to stdout |
| `--threads` | Number of parallel threads (default: all CPU cores) |
| `--block-verify` | Verify integrity using SHA-256 block hashes (enabled by default) |
| `--no-verify` | Disable integrity checks for maximum speed |

**Note:** Decompression automatically detects per-block algorithms when using auto mode archives.

### Info Options

| Option | Description |
|--------|-------------|
| `--block` | Display detailed metadata for a specific block (1-based index) |
| `--threads` | Number of threads (default: all CPU cores) |

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
  "algo": "auto",
  "global_hash": "sha256_hash_of_original_file",
  "file_attr": {
    "mode": 33188,
    "mtime": 1703347200.0,
    "atime": 1703347200.0,
    "uid": 1000,
    "gid": 1000
  },
  "blocks": [
    {
      "id": 0,
      "start": 6,
      "size": 12345,
      "orig_size": 1048576,
      "hash": "block_sha256_hash",
      "algo": "zstd",
      "entropy": 5.8234,
      "time": 0.023456,
      "timestamp": 1703347200.123
    }
  ]
}
```

### Metadata Fields Explained

| Field | Description |
|-------|-------------|
| `version` | GXD format version |
| `algo` | Global algorithm setting (can be "auto") |
| `global_hash` | SHA-256 hash of the complete original file |
| `file_attr` | Preserved file system attributes |
| `blocks[].algo` | Actual algorithm used for each block |
| `blocks[].entropy` | Shannon entropy value (0.0-8.0) |
| `blocks[].time` | Compression time in seconds |
| `blocks[].timestamp` | Unix timestamp when block was compressed |

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
| `auto` | Adaptive | Optimized | Mixed data types (recommended for varied content) |
| `zstd` | Balanced | Good | General purpose (default) |
| `lz4` | Fastest | Lower | Maximum speed |
| `brotli` | Slower | Best | Maximum compression |
| `none` | N/A | None | Integrity verification only |

### Auto Mode Behavior

The `auto` algorithm selection follows these rules per block:
- **Entropy > 7.9**: Uses `none` (data is already compressed/encrypted)
- **Zero ratio > 40% OR Entropy < 3.0**: Uses `lz4` (sparse data, prioritize speed)
- **Entropy < 6.8**: Uses `zstd` (compressible data, good balance)
- **Otherwise**: Uses `brotli` (high redundancy, maximize compression)

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

### Compress with Auto Algorithm Selection
```bash
python gxd.py compress mixed_data.bin output.gxd \
  --algo auto \
  --block-size 1mb \
  --threads 8
```

### Compress a Large Dataset
```bash
python gxd.py compress dataset.bin dataset.gxd \
  --algo zstd \
  --block-size 2mb \
  --zstd-ratio 10 \
  --threads 16
```

### View Archive Metadata
```bash
# View general archive info
python gxd.py info data.gxd

# View specific block details
python gxd.py info data.gxd --block 5
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

### Decompress with Attribute Restoration
```bash
# Original file attributes will be automatically restored
python gxd.py decompress archive.gxd -o restored.bin
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
| Features | New compression algorithms, improved performance optimizations, enhanced auto-selection logic |
| Documentation | Tutorials, use case examples, translations |
| Testing | Additional test cases, platform-specific testing, auto mode validation |
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
- Smart algorithm selection using Shannon Entropy analysis

---

## Development Status & Updates

**Important Notice**: This project is maintained as a personal/community effort. The author is not committed to regular updates, and future releases may or may not come depending on time, interest, and community needs. This is an alpha release (v0.0.0a2) provided as-is.

- **Update Schedule**: No guaranteed timeline for new features or bug fixes
- **Stability**: Current version is functional but APIs and file formats may change
- **Community Contributions**: Highly encouraged and may be the primary driver of future development
- **Support**: Best-effort basis only

If you need guaranteed maintenance or specific features, consider forking the project or contributing directly. Community feedback and contributions are welcome and may help shape future development.

