#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GXD Algorithm Selection Finder
Copyright (C) 2025 @hejhdiss (Muhammed Shafin p)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Author: @hejhdiss (Muhammed Shafin p)
"""

import os
import sys
import math
import argparse
import collections
import time


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

VERSION = "0.0.0a2"

def calculate_entropy(data: bytes) -> float:
    """Calculates Shannon Entropy (0.0 to 8.0)."""
    if not data:
        return 0.0
    counter = collections.Counter(data)
    entropy = 0.0
    for count in counter.values():
        p_x = count / len(data)
        entropy -= p_x * math.log2(p_x)
    return entropy

def calculate_metrics(data: bytes):
    """Calculates zero density and unique byte ratio for better prediction."""
    size = len(data)
    if size == 0:
        return {"zero_ratio": 0, "unique_ratio": 0}
    
    zero_count = data.count(0)
    zero_ratio = zero_count / size
    
    unique_count = len(set(data))
    unique_ratio = unique_count / 256
    
    return {
        "zero_ratio": zero_ratio,
        "unique_ratio": unique_ratio
    }

def parse_size(size_str: str) -> int:
    """Helper to parse sizes (e.g., 1mb, 512kb). Exits on error like gxd.py."""
    if not size_str:
        return 0
    s = str(size_str).lower()
    units = {"kb": 1024, "mb": 1024*1024, "gb": 1024*1024*1024, "k": 1024, "m": 1024*1024}
    
    for unit, val in units.items():
        if s.endswith(unit):
            try:
                clean_val = s[:-len(unit)]
                return int(float(clean_val) * val)
            except ValueError:
                print(f"[-] Error: Invalid size format '{size_str}'", file=sys.stderr)
                sys.exit(1)
    try:
        return int(float(s))
    except ValueError:
        print(f"[-] Error: Could not parse '{size_str}' as a size.", file=sys.stderr)
        sys.exit(1)

class GXDSmartSelector:
    """Predictive algorithm selector based on data heuristics."""
    def __init__(self, zstd_ratio=3):
        self.zstd_ratio = zstd_ratio

    def predict_algo(self, entropy, zeros, unique):
        """Decision Matrix for algorithm prediction."""
        if entropy > 7.9:
            return "none"
        if zeros > 0.4 or entropy < 3.0:
            return "lz4"
        if entropy < 6.8:
            return "zstd"
        return "brotli"

    def analyze_block(self, block: bytes, block_idx: int):
        entropy = calculate_entropy(block)
        metrics = calculate_metrics(block)
        size = len(block)
        
        selected_name = self.predict_algo(entropy, metrics['zero_ratio'], metrics['unique_ratio'])
        

        print(f"\n[Block {block_idx}] Analysis:")
        print(f"  Entropy: {entropy:.2f} | Zeros: {metrics['zero_ratio']:.1%} | Unique: {metrics['unique_ratio']:.1%}")
        print(f"  Testing Predicted -> {selected_name.upper()}")

        test_res = {"name": "none", "size": size, "time": 0.000001}
        start = time.perf_counter()
        
        try:
            if selected_name == "lz4" and lz4:
                c_data = lz4.compress(block)
                test_res = {"name": "lz4", "size": len(c_data), "time": time.perf_counter() - start}
            elif selected_name == "zstd" and zstd:
                c_data = zstd.compress(block, self.zstd_ratio)
                test_res = {"name": "zstd", "size": len(c_data), "time": time.perf_counter() - start}
            elif selected_name == "brotli" and brotli:
                c_data = brotli.compress(block)
                test_res = {"name": "brotli", "size": len(c_data), "time": time.perf_counter() - start}
            else:
                selected_name = "none"
        except Exception as e:
            print(f"  [!] Test failed for {selected_name}: {e}")
            selected_name = "none"

        expansion_warn = " [!] EXPANDED" if test_res['size'] > size else ""
        print(f"  Result -> Size: {test_res['size']} bytes ({ (test_res['size']/size)*100 :.1f}%){expansion_warn}")

        return {
            "best_algo": selected_name,
            "entropy": entropy,
            "zero_density": metrics['zero_ratio'],
            "unique_density": metrics['unique_ratio'],
            "ratio": (test_res['size'] / size) if size > 0 else 1.0,
            "speed_mbs": (size / (1024*1024)) / test_res['time'] if test_res['time'] > 0 else 0,
            "expanded": test_res['size'] > size
        }

def process_file(file_path, block_size, zstd_ratio):
    selector = GXDSmartSelector(zstd_ratio=zstd_ratio)
    
    if not os.path.exists(file_path):
        print(f"[-] Error: File {file_path} not found.", file=sys.stderr)
        return

    print(f"[*] GXD Finder v{VERSION}")
    print(f"[*] Analyzing: {os.path.basename(file_path)}")
    print("-" * 105)
    print(f"{'Blk':<5} | {'Ent':<5} | {'Zeros':<6} | {'Uniq':<5} | {'Selected':<10} | {'Ratio':<7} | {'Speed (MB/s)':<12} | {'Status'}")
    print("-" * 105)

    with open(file_path, 'rb') as f:
        block_idx = 0
        while True:
            chunk = f.read(block_size)
            if not chunk: break
            res = selector.analyze_block(chunk, block_idx)
            status = "EXPANDED" if res['expanded'] else "OK"
            print(f"[Summary] {block_idx:<2} | {res['entropy']:5.2f} | {res['zero_density']:6.1%} | {res['unique_density']:5.1%} | {res['best_algo'].upper():<10} | {res['ratio']:7.1%} | {res['speed_mbs']:12.2f} | {status}")
            print("-" * 105)
            block_idx += 1
            
    print(f"\n[*] Analysis Complete.")
    print(f"[*] Author: @hejhdiss (Muhammed Shafin p)")
    print(f"[*] Library Status: Zstd: {'OK' if zstd else 'MISSING'} | LZ4: {'OK' if lz4 else 'MISSING'} | Brotli: {'OK' if brotli else 'MISSING'}")

def main():
    parser = argparse.ArgumentParser(
        description="GXD Algorithm Selection Finder Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Analyzes files to determine the most efficient compression algorithm for GXD."
    )
    parser.add_argument("input", help="Path to the file to analyze")
    parser.add_argument("--block-size", default="1024kb", help="Data block size (e.g., 512kb, 1mb)")
    parser.add_argument("--zstd-ratio", type=int, default=3, help="Zstd compression level (1-22)")
    parser.add_argument("--version", action="version", version=f"GXD Finder {VERSION}")

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()
    try:
        process_file(args.input, parse_size(args.block_size), args.zstd_ratio)
    except Exception as e:
        print(f"[-] An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()