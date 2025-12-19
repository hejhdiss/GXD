#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GXD Unit Test Suite
Copyright (C) 2025 @hejhdiss (Muhammed Shafin p)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Author: @hejhdiss (Muhammed Shafin p)
License: GPL-3.0
"""

import os
import sys
import subprocess
import tempfile
import shutil
import hashlib
import unittest
import struct
import json

class TestGXDMaximum(unittest.TestCase):
    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.gxd_script = os.path.join(current_dir, "gxd.py")
        self.test_dir = tempfile.mkdtemp()
        self.source_file = os.path.join(self.test_dir, "source.bin")
        self.test_data = os.urandom(4 * 1024 * 1024)
        with open(self.source_file, "wb") as f:
            f.write(self.test_data)
            
        self.gxd_file = os.path.join(self.test_dir, "test.gxd")
        self.output_file = os.path.join(self.test_dir, "output.bin")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def log_test_info(self, name, description, objective):
        """Prints formatted information about the current test."""
        print(f"\n{'#'*80}")
        print(f" TEST: {name}")
        print(f" INFO: {description}")
        print(f" GOAL: {objective}")
        print(f"{'#'*80}")

    def run_cmd(self, args):
        """Runs gxd.py and captures all output. Handles alpha return codes."""
        cmd = [sys.executable, self.gxd_script] + args
        print(f"\n[EXEC] > python gxd.py {' '.join(args)}")
        
        res = subprocess.run(cmd, capture_output=True)
        
        stdout_text = res.stdout.decode(errors='replace').strip()
        stderr_text = res.stderr.decode(errors='replace').strip()

        if stdout_text:
            print(f"--- STDOUT ---\n{stdout_text}")
        if stderr_text:
            print(f"--- STDERR ---\n{stderr_text}")
        
        print(f"[EXIT CODE]: {res.returncode}")
        return res, stdout_text, stderr_text

    def fail_with_output(self, msg, stdout, stderr):
        """Helper to print GXD's actual output before raising an AssertionError."""
        diag = f"\n\n{'!'*20} DIAGNOSTIC SUMMARY {'!'*20}\n"
        diag += f"GXD STDOUT: {stdout if stdout else '[Empty]'}\n"
        diag += f"GXD STDERR: {stderr if stderr else '[Empty]'}\n"
        diag += f"{'!'*60}\n"
        self.fail(f"{msg}{diag}")

    # --- TESTS ---

    def test_full_cycle_permutations(self):
        self.log_test_info(
            "test_full_cycle_permutations", 
            "Matrix of algos and verify modes.",
            "Verify 1:1 data identity on success."
        )
        algos = ["zstd", "lz4", "none"]
        for algo in algos:
            with self.subTest(algo=algo):
                self.run_cmd(["compress", self.source_file, self.gxd_file, "--algo", algo])
                _, stdout, stderr = self.run_cmd(["decompress", self.gxd_file, "-o", self.output_file])
                
                with open(self.output_file, "rb") as f:
                    actual_data = f.read()
                    if self.test_data != actual_data:
                        self.fail_with_output(f"Data corruption in {algo}", stdout, stderr)

    def test_corrupt_footer_magic(self):
        self.log_test_info(
            "test_corrupt_footer_magic", 
            "Breaking trailing magic bytes.",
            "Expect 'error' or 'invalid' in logs, even if exit code is 0."
        )
        self.run_cmd(["compress", self.source_file, self.gxd_file])
        with open(self.gxd_file, "r+b") as f:
            f.seek(-6, os.SEEK_END)
            f.write(b"BADMAG")
            
        _, stdout, stderr = self.run_cmd(["decompress", self.gxd_file, "-o", self.output_file])
        
        error_logged = any(x in stderr.lower() for x in ["error", "invalid", "failed", "not a valid"])
        if not error_logged:
            self.fail_with_output("GXD finished without reporting an error for bad magic.", stdout, stderr)

    def test_file_truncation(self):
        self.log_test_info(
            "test_file_truncation", 
            "Cutting file short.",
            "Detect truncated metadata via printed logs."
        )
        self.run_cmd(["compress", self.source_file, self.gxd_file])
        size = os.path.getsize(self.gxd_file)
        with open(self.gxd_file, "r+b") as f:
            f.truncate(size - 10) 
            
        _, stdout, stderr = self.run_cmd(["decompress", self.gxd_file, "-o", self.output_file])
        if "invalid footer" not in stderr.lower() and "error" not in stderr.lower():
            self.fail_with_output("GXD failed to detect truncation in logs.", stdout, stderr)

    def test_checksum_mismatch(self):
        self.log_test_info(
            "test_checksum_mismatch", 
            "Tampering with data blocks.",
            "Verify the printed integrity failure message."
        )
        self.run_cmd(["compress", self.source_file, self.gxd_file, "--block-verify"])
        
        with open(self.gxd_file, "r+b") as f:
            f.seek(100)
            f.write(b"\xFF\xFF")
            
        _, stdout, stderr = self.run_cmd(["decompress", self.gxd_file, "-o", self.output_file, "--block-verify"])
        
        failed_msg = any(x in stderr.lower() for x in ["integrity", "failed", "mismatch"])
        if not failed_msg:
            self.fail_with_output("Integrity failure not found in GXD output.", stdout, stderr)

    def test_unsupported_algorithm_metadata(self):
        self.log_test_info(
            "test_unsupported_algorithm_metadata", 
            "Editing JSON to use 'ghost-algo'.",
            "Verify tool doesn't match source data if algo is wrong."
        )
 
        self.run_cmd(["compress", self.source_file, self.gxd_file])
        

        with open(self.gxd_file, "rb") as f:
            data = f.read()
        

        json_size = struct.unpack("<Q", data[-14:-6])[0]
        json_start_offset = -(14 + json_size)
        json_bytes = data[json_start_offset : -14]
        metadata = json.loads(json_bytes.decode())
        
        metadata['algo'] = 'ghost-algo'
        
        new_json = json.dumps(metadata).encode()
        new_size = len(new_json)
        
        header_and_blocks = data[:json_start_offset]
        corrupt_data = header_and_blocks + new_json + struct.pack("<Q", new_size) + b"GXDINC"
        

        with open(self.gxd_file, "wb") as f:
            f.write(corrupt_data)
            f.truncate()
            
        _, stdout, stderr = self.run_cmd(["decompress", self.gxd_file, "-o", self.output_file])
        
        if os.path.exists(self.output_file):
            with open(self.output_file, "rb") as f:
                output_data = f.read()
                if output_data == self.test_data:
                    self.fail_with_output("Tool claimed success and produced correct data despite broken algo name!", stdout, stderr)

    def test_seek_text_mode(self):
         self.log_test_info("test_seek_text_mode", "Testing --text output", "Verify clean string output")
         text_source = os.path.join(self.test_dir, "text.txt")
         with open(text_source, "w") as f:
             f.write("Hello GXD Text Mode")
        
         self.run_cmd(["compress", text_source, self.gxd_file])
         _, stdout, _ = self.run_cmd(["seek", self.gxd_file, "--offset", "0", "--length", "5", "--text"])
        
         self.assertEqual(stdout, "Hello")

    def test_text_mode_output(self):
        self.log_test_info(
            "test_text_mode_output", 
            "Testing --text flag for seek and decompress.",
            "Verify that binary data is correctly decoded to strings in the output."
        )
        
        text_content = "GXD_UNIT_TEST_TEXT_DATA_12345"
        text_source = os.path.join(self.test_dir, "text_source.txt")
        with open(text_source, "w", encoding="utf-8") as f:
            f.write(text_content)
            
        self.run_cmd(["compress", text_source, self.gxd_file])
        
        _, stdout_seek, _ = self.run_cmd([
            "seek", self.gxd_file, 
            "--offset", "4", 
            "--length", "9", 
            "--text"
        ])
        
        self.assertEqual(stdout_seek, "UNIT_TEST", f"Seek text mismatch: expected 'UNIT_TEST', got '{stdout_seek}'")

        _, stdout_dec, _ = self.run_cmd([
            "decompress", self.gxd_file, 
            "-o", self.output_file, 
            "--text"
        ])
        
        with open(self.output_file, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), text_content)
        
        print("\n[+] Text mode verification successful.")   
    def test_seek_unsupported_algorithm(self):
        self.log_test_info(
            "test_seek_unsupported_algorithm", 
            "Testing seek on a corrupted block.",
            "Verify seek also stops immediately on error."
        )
        self.run_cmd(["compress", self.source_file, self.gxd_file])
        
        with open(self.gxd_file, "rb") as f:
            data = f.read()
        json_size = struct.unpack("<Q", data[-14:-6])[0]
        metadata = json.loads(data[-(14 + json_size) : -14].decode())
        metadata['algo'] = 'ghost-algo'
        
        new_json = json.dumps(metadata).encode()
        corrupt_data = data[:-(14 + json_size)] + new_json + struct.pack("<Q", len(new_json)) + b"GXDINC"
        with open(self.gxd_file, "wb") as f:
            f.write(corrupt_data)

        _, stdout, stderr = self.run_cmd(["seek", self.gxd_file, "--offset", "0", "--length", "1024"])
        
        if "FATAL" not in stderr:
            self.fail_with_output("Seek did not report a FATAL error on corrupted block.", stdout, stderr)
   
if __name__ == "__main__":
    print(f"{'='*80}")
    print(f"GXD TEST SUITE")
    print(f"Author: @hejhdiss (Muhammed Shafin p)")
    print(f"License: GPL-3.0")
    print(f"{'='*80}")
    unittest.main(verbosity=1)
