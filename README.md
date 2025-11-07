# raw2fits

Convert 16‑bit RAW images (2 bytes per pixel) to FITS. Supports single file and recursive directory conversion via CLI, and a simple Python API.

## Features
- 16‑bit RAW to 16‑bit FITS using `astropy`.
- Default byte order is little‑endian (LSB first). Big‑endian optional.
- Validates file size: must equal `width * height * 2` bytes.
- CLI supports:
  - Single RAW file → FITS
  - Directory (recursive) conversion of all `.raw` files

## Requirements
- Python 3.8+
- Dependencies: `numpy`, `astropy`

Install:
```bash
pip install -r requirements.txt
```

On Windows (PowerShell) you can also run:
```powershell
python -m pip install -r requirements.txt
```

## CLI Usage

Single file:
```bash
python raw2fits.py INPUT.raw --width 1920 --height 1080 --output OUTPUT.fits
```

Directory (recursively convert all `.raw` files; `--output` is ignored):
```bash
python raw2fits.py E:\path\to\folder --width 1920 --height 1080
```

Specify byte order (if your RAW is big‑endian):
```bash
python raw2fits.py INPUT.raw --width 1920 --height 1080 --byteorder big
```

Exit codes:
- `0`: success (no failures)
- `1`: error (in directory mode, any failed file yields exit code 1)
- `2`: invalid arguments (e.g., non‑positive width/height)

Notes:
- RAW is assumed to be a binary stream of `uint16` samples (2 bytes/pixel). Default is little‑endian (LSB first).
- FITS is written with appropriate header keywords; `astropy` handles `uint16` scaling as needed.

## Python API
```python
from raw2fits import convert_raw_directory_to_fits

result = convert_raw_directory_to_fits(
    r"E:\\data\\raw_images",
    width=1920,
    height=1080,
    byteorder="little",  # or "big"
)
print("written:", len(result["written"]))
print("failed:", result["failed"])  # list of "<input_path>: <error>"
```

## Troubleshooting
- Size mismatch error: ensure `width * height * 2` equals the RAW file size.
- Endianness: if the image looks wrong (banding/values off), try `--byteorder big`.
- Memory: very large images require enough RAM to load; this tool reads the full frame into memory.

## License
MIT (or your preferred license).

