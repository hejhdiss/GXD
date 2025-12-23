#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
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

Author: @hejhdiss (Muhammed Shafin p)
"""

import os
import sys
import json
import argparse
import hashlib
import time
import struct
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Dict, Any, Optional
import collections
import math 

# Optional imports with dependency handling
try:
    import zstd
except ImportError:
    zstd = None
try:
    import lz4.frame as lz4
except ImportError:
    lz4 = None
try:
    import brotli
except ImportError:
    brotli = None
try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

MAGIC = b"GXDINC"
VERSION = "0.0.0a2"

def calculate_entropy(data: bytes) -> float:
    if not data: return 0.0
    counter = collections.Counter(data)
    entropy = 0.0
    for count in counter.values():
        p_x = count / len(data)
        entropy -= p_x * math.log2(p_x)
    return entropy

def calculate_metrics(data: bytes):
    size = len(data)
    if size == 0: return {"zero_ratio": 0, "unique_ratio": 0}
    zero_ratio = data.count(0) / size
    unique_ratio = len(set(data)) / 256
    return {"zero_ratio": zero_ratio, "unique_ratio": unique_ratio}

class GXDSmartSelector:
    """Predicts the best algorithm for a block of data."""
    @staticmethod
    def predict(data: bytes) -> str:
        entropy = calculate_entropy(data)
        metrics = calculate_metrics(data)
        zeros = metrics['zero_ratio']
        
        if entropy > 7.9: return "none"
        if zeros > 0.4 or entropy < 3.0: return "lz4"
        if entropy < 6.8: return "zstd"
        return "brotli"
    
def render_bar(current, total, width=40):
    """Fallback visual progress bar string if tqdm is unavailable."""
    if total <= 0: return ""
    percent = (current / total)
    filled = int(width * percent)
    bar = "█" * filled + "-" * (width - filled)
    return f"[{bar}] {int(percent*100)}% ({current}/{total})"

def parse_size(size_str: str) -> int:
    """Helper to parse sizes. Exits on invalid input."""
    if not size_str:
        return 0
    s = str(size_str).lower()
    
    if s == "no":
        return 0
        
    units = {"kb": 1024, "mb": 1024*1024, "gb": 1024*1024*1024}
    for unit, val in units.items():
        if s.endswith(unit):
            try:
                return int(float(s[:-len(unit)]) * val)
            except ValueError:
                print(f"[-] Error: Invalid size format '{size_str}'", file=sys.stderr)
                sys.exit(1)
    try:
        return int(float(s))
    except ValueError:
        print(f"[-] Error: Could not parse '{size_str}' as a size or number.", file=sys.stderr)
        sys.exit(1)

class GXDCompressor:
    def __init__(self, algo='zstd', block_size=1024*1024, verify='block', zstd_ratio=3, threads=None):
        self.algo = algo
        self.block_size = block_size
        self.verify = verify
        self.zstd_ratio = zstd_ratio
        self.threads = threads or os.cpu_count() or 2

    def _compress_block(self, chunk: bytes, block_id: int):
        try:
            b_start_time = time.time()
            actual_algo = self.algo
            if self.algo == 'auto':
                if not (zstd and lz4 and brotli):
                    raise ImportError("necessary compression libraries not available for 'auto' mode.")
                actual_algo = GXDSmartSelector.predict(chunk)
            if actual_algo == 'zstd' and zstd:
                if not zstd: raise ImportError("zstd module not found")
                c_data = zstd.compress(chunk, self.zstd_ratio)
            elif actual_algo == 'lz4' and lz4:
                if not lz4: raise ImportError("lz4 module not found")
                c_data = lz4.compress(chunk)
            elif actual_algo == 'brotli' and brotli:
                if not brotli: raise ImportError("brotli module not found")
                c_data = brotli.compress(chunk)
            else:
                c_data = chunk
                actual_algo = 'none'
            
            b_hash = hashlib.sha256(chunk).hexdigest() if self.verify == 'block' else "no"
            entropy = calculate_entropy(chunk)
            duration = time.time() - b_start_time
            return {
                "id": block_id,
                "size": len(c_data),
                "orig_size": len(chunk),
                "hash": b_hash,
                "data": c_data,
                "algo": actual_algo ,
                "entropy": round(entropy, 4),     
                "comp_time": round(duration, 6),
                "timestamp": b_start_time
            }
        except Exception as e:
            return {"error": str(e), "id": block_id}

    def compress(self, input_path, output_path):
        if not os.path.exists(input_path):
            print(f"[-] Error: Input file '{input_path}' not found.", file=sys.stderr)
            sys.exit(1)
        file_stat = os.stat(input_path)
        file_meta = {
            "mode": file_stat.st_mode,        # Permissions (e.g. 755)
            "mtime": file_stat.st_mtime,      # Modification time
            "atime": file_stat.st_atime,      # Access time
            "uid": file_stat.st_uid,          # User ID (Unix)
            "gid": file_stat.st_gid           # Group ID (Unix)
        }

        print(f"[*] Compressing {input_path} -> {output_path} ({self.algo}) using {self.threads} workers\n", file=sys.stderr)

        blocks_meta = []
        global_hasher = hashlib.sha256() if self.verify in ['global', 'block'] else None
        start_time = time.time()
        
        with open(input_path, "rb") as f_in, open(output_path, "wb") as f_out:
            f_out.write(MAGIC)
            
            with ProcessPoolExecutor(max_workers=self.threads) as executor:
                futures = []
                block_id = 0
                while True:
                    chunk = f_in.read(self.block_size)
                    if not chunk: break
                    if global_hasher: global_hasher.update(chunk)
                    futures.append(executor.submit(self._compress_block, chunk, block_id))
                    block_id += 1

                if tqdm:
                    pbar = tqdm(total=len(futures), desc="Compressing", unit="blk", file=sys.stderr)
                
                results = [None] * len(futures)
                completed = 0
                for f in as_completed(futures):
                    res = f.result()
                    if "error" in res:
                        print(f"\n[-] Fatal error in worker: {res['error']}", file=sys.stderr)
                        sys.exit(1)
                    results[res['id']] = res
                    completed += 1
                    if tqdm: pbar.update(1)
                    else:
                        sys.stderr.write(f"\rCompressing: {render_bar(completed, len(futures))}")

                if tqdm: pbar.close()

                current_offset = len(MAGIC)
                for res in results:
                    f_out.write(res['data'])
                    blocks_meta.append({
                        "id": res['id'],
                        "start": current_offset,
                        "size": res['size'],
                        "orig_size": res['orig_size'],
                        "hash": res['hash'],
                        "algo": res['algo'],
                        "entropy": res['entropy'],     
                        "time": res['comp_time']  ,
                        "timestamp": res['timestamp']
                           
                    })
                    current_offset += res['size']

            footer_data = {
                "version": VERSION,
                "algo": self.algo,
                "global_hash": global_hasher.hexdigest() if global_hasher else "no",
                "file_attr": file_meta,
                "blocks": blocks_meta
            }
            footer_json = json.dumps(footer_data).encode('utf-8')
            f_out.write(footer_json)
            f_out.write(struct.pack("<Q", len(footer_json)))
            f_out.write(MAGIC)

        duration = time.time() - start_time
        print(f"\n[+] Compression Complete. (Time: {duration:.2f}s)", file=sys.stderr)

class GXDDecompressor:
    def __init__(self, verify_request='block', output_text=False, threads=None):
        self.verify_request = verify_request
        self.output_text = output_text
        self.threads = threads or os.cpu_count() or 2
    def show_info(self, input_path, block_index=None):
        if not os.path.exists(input_path):
            print(f"[-] Error: File not found: '{input_path}'", file=sys.stderr)
            sys.exit(1)

        with open(input_path, "rb") as f_in:
            f_in.seek(0, os.SEEK_END)
            actual_file_size = f_in.tell()
            
            f_in.seek(-(8 + len(MAGIC)), os.SEEK_END)
            footer_len = struct.unpack("<Q", f_in.read(8))[0]
            
            f_in.seek(-(footer_len + 8 + len(MAGIC)), os.SEEK_END)
            metadata = json.loads(f_in.read(footer_len).decode('utf-8'))
            
            blocks = metadata.get('blocks', [])
            attr = metadata.get('file_attr', {})

            print(f"\n{'='*50}")
            print(f" GXD ARCHIVE INFORMATION")
            print(f"{'='*50}")
            print(f"File Name      : {os.path.basename(input_path)}")
            print(f"GXD Version    : {metadata.get('version', 'Unknown')}")
            print(f"Global Algo    : {metadata.get('algo', 'Unknown')}")
            print(f"Total Blocks   : {len(blocks)}")
            
            if attr:
                print(f"\n--- Preserved File Attributes ---")
                print(f"Original Mode  : {oct(attr.get('mode', 0))}")
                print(f"Modify Time    : {time.ctime(attr.get('mtime', 0))}")
                print(f"Access Time    : {time.ctime(attr.get('atime', 0))}")

            if block_index is not None:
                idx = block_index - 1
                if 0 <= idx < len(blocks):
                    b = blocks[idx]
                    print(f"\n--- Metadata for Block {block_index} ---")
                    for key, value in b.items():
                        print(f"{key.capitalize():<15}: {value}")
                else:
                    print(f"\n[!] Error: Block index {block_index} is out of range (1-{len(blocks)}).")
            else:
                print(f"\n--- Block Overview (First 5) ---")
                print(f"{'ID':<5} | {'Algo':<8} | {'Size':<10} | {'Orig Size':<10}")
                print("-" * 45)
                for b in blocks[:5]:
                    print(f"{b['id']+1:<5} | {b['algo']:<8} | {b['size']:<10} | {b['orig_size']:<10}")
                if len(blocks) > 5:
                    print(f"... and {len(blocks)-5} more blocks.")
            print(f"{'='*50}\n")

    def _decompress_block(self, c_data: bytes, algo: str):
        if algo == "zstd" and not zstd:
            return None, "Error: 'zstd' module required."
        if algo == "lz4" and not lz4:
            return None, "Error: 'lz4' module required."
        if algo == "brotli" and not brotli:
            return None, "Error: 'brotli' module required."
        if algo == "none":
            if (not zstd) and (not lz4) and (not brotli):
                return None, "Error: No decompression modules available."

        try:
            if algo == "zstd":
                return zstd.decompress(c_data), None
            elif algo == "lz4":
                return lz4.decompress(c_data), None
            elif algo == "brotli":
                return brotli.decompress(c_data), None
            elif algo == "none":
                return c_data, None
            else:
                return None, f"Unsupported algorithm '{algo}'"
        except Exception as e:
            return None, f"Decompression engine error: {e}"

    def _decompress_worker(self, c_data, algo, b_meta, b_logic_start):
        decompressed, error = self._decompress_block(c_data, algo)
        return b_meta, b_logic_start, decompressed, error

    def process(self, input_path, output_path=None, offset=0, length=None, is_seek=False):
        if not os.path.exists(input_path):
            print(f"[-] Error: File not found: '{input_path}'", file=sys.stderr)
            sys.exit(1)

        out_stream = None
        try:
            if output_path:
                mode = "w" if self.output_text else "wb"
                out_stream = open(output_path, mode, encoding='utf-8' if self.output_text else None)
                show_progress = True
            elif self.output_text:
                out_stream = sys.stdout
                show_progress = False
            else:
                out_stream = sys.stdout.buffer
                show_progress = False

            with open(input_path, "rb") as f_in:
                f_in.seek(0, os.SEEK_END)
                actual_file_size = f_in.tell()
                
                f_in.seek(-(8 + len(MAGIC)), os.SEEK_END)
                footer_len = struct.unpack("<Q", f_in.read(8))[0]
                
                if footer_len + 8 + len(MAGIC) > actual_file_size:
                    sys.stderr.write("[-] Error: Corrupt metadata (invalid footer length).\n")
                    sys.exit(1)
                
                f_in.seek(-(footer_len + 8 + len(MAGIC)), os.SEEK_END)
                metadata = json.loads(f_in.read(footer_len).decode('utf-8'))
                
                f_in.seek(-len(MAGIC), os.SEEK_END)
                if f_in.read(len(MAGIC)) != MAGIC:
                    sys.stderr.write("[-] Error: Magic mismatch at end of file. Archive is corrupt.\n")
                    sys.exit(1)
                
                algo = metadata['algo']
                blocks = metadata['blocks']
                total_raw_size = sum(b['orig_size'] for b in blocks)
                
                requested_start = offset
                requested_end = (offset + length) if length is not None else None
                
                if is_seek and requested_start >= total_raw_size:
                    sys.stderr.write(f"[-] Error: Offset {requested_start} exceeds available data.\n")
                    sys.exit(1)

                target_blocks = []
                curr_logical_pos = 0
                for b in blocks:
                    b_start = curr_logical_pos
                    b_end = curr_logical_pos + b['orig_size']
                    if (b_start < (requested_end or float('inf'))) and (b_end > requested_start):
                        target_blocks.append((b, b_start))
                    curr_logical_pos = b_end

                results_unordered = []
                with ProcessPoolExecutor(max_workers=self.threads) as executor:
                    futures = []
                    for b, b_logic_start in target_blocks:
                        f_in.seek(b['start'])
                        compressed_chunk = f_in.read(b['size'])
                        if algo == 'auto':
                            target_algo = b.get('algo', metadata.get('algo', 'none'))
                            futures.append(executor.submit(self._decompress_worker, compressed_chunk, target_algo, b, b_logic_start))
                        else:
                            futures.append(executor.submit(self._decompress_worker, compressed_chunk, algo, b, b_logic_start))

                    if show_progress and tqdm:
                        pbar = tqdm(total=len(target_blocks), desc="Decompressing", unit="blk", file=sys.stderr)
                        for f in as_completed(futures):
                            results_unordered.append(f.result())
                            pbar.update(1)
                        pbar.close()
                    else:
                        for idx, f in enumerate(as_completed(futures)):
                            results_unordered.append(f.result())
                            if show_progress:
                                sys.stderr.write(f"\rDecompressing: {render_bar(idx+1, len(target_blocks))}")

                results = sorted(results_unordered, key=lambda x: x[0]['id'])

                for b, b_logic_start, decompressed_chunk, error in results:
                    if error:
                        sys.stderr.write(f"[-] FATAL: Decompression failed for block {b['id']}. {error}\n")
                        sys.exit(1)
                    
                    if self.verify_request != 'none' and b['hash'] != "no":
                        if hashlib.sha256(decompressed_chunk).hexdigest() != b['hash']:
                            sys.stderr.write(f"[-] FATAL: Integrity check failed for block {b['id']}.\n")
                            sys.exit(1)
                    
                    s_start = max(0, requested_start - b_logic_start)
                    s_end = min(len(decompressed_chunk), (requested_end - b_logic_start) if requested_end else len(decompressed_chunk))
                    chunk = decompressed_chunk[s_start:s_end]
                    
                    if self.output_text:
                        try:
                            out_stream.write(chunk.decode('utf-8'))
                        except UnicodeDecodeError:
                            sys.stderr.write(f"[-] Error: Block {b['id']} contains invalid UTF-8 data.\n")
                            sys.exit(1)
                    else:
                        out_stream.write(chunk)
                        out_stream.flush()

            if output_path:
                print(f"\n[+] Operation Complete.", file=sys.stderr)

        finally:
            if output_path and out_stream:
                out_stream.close()
            if not is_seek and not self.output_text and 'file_attr' in metadata:
                    attr = metadata['file_attr']
                    try:
                        os.utime(output_path, (attr['atime'], attr['mtime']))
                        os.chmod(output_path, attr['mode'])
                    except Exception as e:
                        sys.stderr.write(f"[!] Warning: Could not restore all file attributes: {e}\n")

def main():
    threads_help = "Number of parallel threads. Supported: 1 to 128 (default: all CPU cores)"
    supported_algos = ['none']
    if zstd: supported_algos.append('zstd')
    if lz4: supported_algos.append('lz4')
    if brotli: supported_algos.append('brotli')
    algo_help = f"Compression algorithm. Supported on this system: {', '.join(supported_algos)} (default: zstd)"
    parser = argparse.ArgumentParser(
        description="GXD Block-based Compression CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Copyright (C) 2025 @hejhdiss (Muhammed Shafin p)
License: GPL-3.0
Author's GitHub: https://github.com/hejhdiss
"""
    )
    progress_status = "Uses tqdm." if tqdm else "Not installed tqdm.(fallback to simple log)"
    parser.epilog = f"Progress Bar: {progress_status}\n" + parser.epilog
    parser.add_argument("--version", action="version", version=f"GXD {VERSION}")
    subparsers = parser.add_subparsers(dest="command")

    # --- Compress Command ---
    c_parser = subparsers.add_parser(
        "compress", 
        help="Compress a file into GXD format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=f"GXD Compression Utility v{VERSION}\nAuthor: @hejhdiss\n\nCompresses input files using block-based parallel processing."
    )
    
    c_parser.add_argument("input", help="Path to the source file to be compressed")
    c_parser.add_argument("output", help="Path where the resulting .gxd file will be saved")
    c_parser.add_argument("--algo", choices=['auto','zstd', 'lz4', 'brotli', 'none'], default='zstd', 
                          help=algo_help)
    c_parser.add_argument("--block-size", default="1024kb", 
                          help="Size of data blocks (e.g., 512kb, 1mb, 2mb. default: 1024kb)")
    c_parser.add_argument("--zstd-ratio", type=int, default=3, 
                          help="Zstd compression level 1-22 (default: 3)")
    c_parser.add_argument("--threads", "-j", type=int, help=threads_help)
    cv_group = c_parser.add_mutually_exclusive_group()
    cv_group.add_argument("--block-verify", action="store_const", const="block", dest="verify",
                          help="Enable SHA-256 integrity check per block (default: enabled)")
    cv_group.add_argument("--no-verify", action="store_const", const="none", dest="verify",
                          help="Disable all integrity checks for faster performance")
    c_parser.set_defaults(verify="block")

    # --- Decompress Command ---
    d_parser = subparsers.add_parser(
        "decompress", 
        help="Decompress a GXD file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=f"GXD Decompression Utility v{VERSION}\nAuthor: @hejhdiss\n\nRestores the original file from a GXD archive."
    )
    d_parser.add_argument("input", help="Path to the .gxd archive to decompress")
    d_parser.add_argument("--output", "-o", help="Path for the restored file (default: same as input minus .gxd)")
    d_parser.add_argument("--text", action="store_true", help="Print decompressed data as UTF-8 text to stdout")
    d_parser.add_argument("--threads", "-j", type=int, help=threads_help)
    
    dv_group = d_parser.add_mutually_exclusive_group()
    dv_group.add_argument("--block-verify", action="store_const", const="block", dest="verify", 
                          help="Verify integrity using SHA-256 block hashes (default: enabled)")
    dv_group.add_argument("--no-verify", action="store_const", const="none", dest="verify",
                          help="Disable integrity checks for maximum speed")
    d_parser.set_defaults(verify="block")

    # --- Seek Command ---
    s_parser = subparsers.add_parser(
        "seek", 
        help="Extract a specific range from a GXD file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=f"GXD Seek Utility v{VERSION}\nAuthor: @hejhdiss\n\nRandom-access extraction. Retrieves specific bytes without decompressing the whole file."
    )
    s_parser.add_argument("input", help="Path to the .gxd archive")
    s_parser.add_argument("--output", "-o", help="Path to save the extracted chunk (default: stdout)")
    s_parser.add_argument("--offset", default="0", help="Byte offset to start reading (e.g., 0, 1mb, 512kb. default: 0)")
    s_parser.add_argument("--length", help="Number of bytes to extract (e.g., 100, 2mb. default: until EOF)")
    s_parser.add_argument("--text", action="store_true", help="Print extracted chunk as UTF-8 text to stdout")
    s_parser.add_argument("--threads", "-j", type=int, help=threads_help)
    
    sv_group = s_parser.add_mutually_exclusive_group()
    sv_group.add_argument("--block-verify", action="store_const", const="block", dest="verify",
                          help="Verify hashes of the blocks being accessed (default: enabled)")
    sv_group.add_argument("--no-verify", action="store_const", const="none", dest="verify",
                          help="Disable integrity checks")
    s_parser.set_defaults(verify="block")

    # --- Info Command ---
    i_parser = subparsers.add_parser(
        "info", 
        help="View GXD archive metadata",
        description="Displays global file attributes and detailed block metadata."
    )
    i_parser.add_argument("input", help="Path to the .gxd archive")
    i_parser.add_argument("--block", type=int, help="Get metadata for a specific block (1-based index)")
    i_parser.add_argument("--threads", type=int, default=os.cpu_count(), help="Number of threads")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    try:
        if args.command == "compress":
            if args.algo != 'zstd' and args.zstd_ratio != 3:
                print(f"[!] Warning: --zstd-ratio ({args.zstd_ratio}) is ignored when using "
                      f"algorithm '{args.algo}'. it only applies to 'zstd'.", file=sys.stderr)
            b_size = parse_size(args.block_size)
            if b_size <= 0:
                print("[-] Error: Block size must be greater than 0.", file=sys.stderr)
                sys.exit(1)
            comp = GXDCompressor(
                algo=args.algo, 
                block_size=parse_size(args.block_size), 
                verify=args.verify, 
                zstd_ratio=args.zstd_ratio,
                threads=args.threads
            )
            comp.compress(args.input, args.output)
        elif args.command == "decompress":
            dec = GXDDecompressor(verify_request=args.verify, output_text=args.text, threads=args.threads)
            dec.process(args.input, args.output)
        elif args.command == "seek":
            dec = GXDDecompressor(verify_request=args.verify, output_text=args.text, threads=args.threads)
            dec.process(
                args.input, args.output, 
                offset=parse_size(args.offset), 
                length=parse_size(args.length) if args.length else None, 
                is_seek=True
            )
        elif args.command == "info":
            dec = GXDDecompressor(threads=args.threads)
            dec.show_info(args.input, block_index=args.block)
    except Exception as e:
        sys.stderr.write(f"[-] An unexpected error occurred: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
