#!/usr/bin/env python3
"""
Convert a 16-bit RAW image (little-endian, LSB first; 2 bytes per pixel) to a FITS image.

Usage:
  # Single file
  python raw2fits.py INPUT.raw --width W --height H [--output OUTPUT.fits] [--byteorder little|big]

  # Directory (recursively convert all .raw)
  python raw2fits.py DIR --width W --height H [--byteorder little|big]

Notes:
- Default byte order is little (LSB first) as specified.
- The script validates the input file size (must equal width*height*2 bytes).
"""

import argparse
import os
import sys
from typing import Tuple

import numpy as np

try:
    from astropy.io import fits
except Exception as exc:
    print("Error: astropy is required. Install with: pip install astropy numpy", file=sys.stderr)
    raise


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert 16-bit RAW (2 bytes/pixel) to FITS (16-bit).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input", help="Path to input RAW file or directory")
    parser.add_argument("--width", type=int, required=True, help="Image width in pixels")
    # Avoid -h short option to not collide with help
    parser.add_argument("--height", type=int, required=True, help="Image height in pixels")
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to output FITS file (defaults to INPUT with .fits extension)",
    )
    parser.add_argument(
        "--byteorder",
        type=str,
        choices=["little", "big"],
        default="little",
        help="Byte order of RAW data (LSB-first == little).",
    )
    return parser.parse_args(argv)


def validate_file_size(file_path: str, width: int, height: int) -> None:
    expected_bytes = width * height * 2
    try:
        actual_bytes = os.path.getsize(file_path)
    except OSError as err:
        raise FileNotFoundError(f"Cannot access '{file_path}': {err}") from err

    if actual_bytes != expected_bytes:
        raise ValueError(
            (
                f"File size mismatch: expected {expected_bytes} bytes for {width}x{height}x16b, "
                f"but got {actual_bytes} bytes."
            )
        )


def load_raw_image(file_path: str, width: int, height: int, byteorder: str) -> np.ndarray:
    dtype = np.dtype("<u2" if byteorder == "little" else ">u2")
    # Use fromfile for efficiency; count ensures exact number of pixels read
    num_pixels = width * height
    try:
        image_1d = np.fromfile(file_path, dtype=dtype, count=num_pixels)
    except Exception as err:
        raise RuntimeError(f"Failed to read RAW data: {err}") from err

    if image_1d.size != num_pixels:
        raise ValueError(
            f"Read {image_1d.size} pixels, expected {num_pixels}. The file may be truncated or parameters are incorrect."
        )

    try:
        image_2d = image_1d.reshape((height, width))
    except Exception as err:
        raise ValueError(f"Failed to reshape to ({height}, {width}): {err}") from err

    return image_2d


def write_fits(image: np.ndarray, output_path: str, raw_path: str, width: int, height: int, byteorder: str) -> None:
    hdu = fits.PrimaryHDU(image)
    hdr = hdu.header
    hdr["COMMENT"] = "Converted from 16-bit RAW (2 bytes/pixel)."
    hdr["HISTORY"] = f"Source: {os.path.basename(raw_path)}; {width}x{height}; byteorder={byteorder}"
    hdr["CREATOR"] = "raw2fits.py"
    # astropy will handle uint16 properly using BZERO/BSCALE if needed
    try:
        hdu.writeto(output_path, overwrite=True, output_verify="fix")
    except Exception as err:
        raise RuntimeError(f"Failed to write FITS file '{output_path}': {err}") from err


def derive_output_path(input_path: str) -> str:
    base, _ = os.path.splitext(input_path)
    return base + ".fits"


def convert_raw_directory_to_fits(root_dir: str, width: int, height: int, byteorder: str = "little") -> dict[str, list[str]]:
    """
    Recursively convert all .raw files under root_dir to same-name .fits files in place.

    Parameters
    ----------
    root_dir : str
        Root directory to traverse.
    width : int
        Image width in pixels for all RAW files.
    height : int
        Image height in pixels for all RAW files.
    byteorder : str
        'little' (default) or 'big' according to RAW byte order.

    Returns
    -------
    dict[str, list[str]]
        A dictionary with keys:
        - 'written': list of written FITS paths
        - 'failed' : list of error strings formatted as "<input_path>: <error>"
    """
    written: list[str] = []
    failed: list[str] = []

    for dirpath, _dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if not filename.lower().endswith('.raw'):
                continue
            input_path = os.path.join(dirpath, filename)
            print(f"Processing: {input_path}", flush=True)
            output_path = derive_output_path(input_path)
            try:
                validate_file_size(input_path, width, height)
                image = load_raw_image(input_path, width, height, byteorder)
                write_fits(image, output_path, input_path, width, height, byteorder)
                written.append(output_path)
            except Exception as err:
                failed.append(f"{input_path}: {err}")

    return {"written": written, "failed": failed}


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    input_path = args.input

    if args.width <= 0 or args.height <= 0:
        print("Error: width and height must be positive integers.", file=sys.stderr)
        return 2

    # Directory mode
    if os.path.isdir(input_path):
        if args.output:
            print("Warning: --output is ignored when input is a directory.", file=sys.stderr)
        result = convert_raw_directory_to_fits(input_path, args.width, args.height, args.byteorder)
        print(f"Converted {len(result['written'])} files. Failures: {len(result['failed'])}.")
        if result["failed"]:
            for msg in result["failed"]:
                print(f"Failed: {msg}", file=sys.stderr)
        # Return 0 if at least one success and no failures; otherwise 1 if any failure
        return 0 if len(result["failed"]) == 0 else 1

    # Single-file mode
    output_path = args.output or derive_output_path(input_path)
    try:
        validate_file_size(input_path, args.width, args.height)
        image = load_raw_image(input_path, args.width, args.height, args.byteorder)
        write_fits(image, output_path, input_path, args.width, args.height, args.byteorder)
    except Exception as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1

    print(f"Wrote FITS: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


