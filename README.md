# PaedDeadSpace-Windows

[![Release](https://img.shields.io/badge/release-v1.0.0-blue)](https://github.com/taffache-hash/PaedDeadSpace-Windows/releases/tag/v1.0.0)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Platform](https://img.shields.io/badge/Windows-10%2F11%20x86--64-blue)
![Zenodo DOI](https://img.shields.io/badge/Zenodo%20DOI-pending-lightgrey)

**PaedDeadSpace: Pediatric Apparatus Dead-Space Explorer — Windows** contains the build source and release documentation for the portable Windows distribution of **PaedDeadSpace-Core v1.0.0 + PaedDeadSpace-UI v1.0.0**.

> For educational and research use only. Not intended for clinical decision-making or patient-specific treatment recommendations.

## Distribution model
The Windows application is a **portable one-folder distribution** for Windows 10/11 x86-64. The large portable ZIP is published as a **GitHub Release asset** and Zenodo file, not committed to normal Git history.

Target asset name: `PaedDeadSpace-Windows-v1.0.0-x86_64-portable.zip`.

## Rebuild manually
Place these three repositories side-by-side:

```text
PaedDeadSpace-Core/
PaedDeadSpace-UI/
PaedDeadSpace-Windows/
```

On Windows, install Python 3.13 (3.11–3.13 supported), then double-click `BUILD_FINAL_v1.0.0.cmd` or run:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_tools\build_windows_v1_0_0.ps1
```

The script creates an isolated environment, installs the local Core, runs **47 Core + 13 validation + 21 UI tests**, builds the executable with PyInstaller, adds README/LICENSE/checksums, and creates the correctly named portable ZIP. A manual Pearsall golden-case run is required before publication.

## Local runtime and privacy
The launcher binds Streamlit to `127.0.0.1`, disables Streamlit usage-statistics collection, and requires no OpenAI API key. PaedDeadSpace calculations do not intentionally send entered model data to external servers and do not require Internet access at runtime.

## Code signing
v1.0.0 is intentionally **not digitally signed**. Windows SmartScreen may display a warning. Official SHA-256 checksums must be published with the release asset so users can verify integrity.

## Scientific scope / limitations
The Windows package does not alter the scientific Core. All model assumptions and limitations are those documented in PaedDeadSpace-Core. The executable is an educational/research tool, not a medical device or clinical decision-support system.

## Citation
The PaedDeadSpace-Core Zenodo DOI is the preferred citation for the scientific project. Use the Windows DOI when specifically citing this packaged distribution.

## Author
**Paolo Taffache** — ORCID: 0009-0002-8806-9733  
General and Pediatric Anesthesia and Intensive Care Unit, IRCCS AOU Bologna – Policlinico Sant’Orsola-Malpighi, Bologna, Italy  
Contact: taffache@gmail.com

## Funding and AI disclosure
Funding: **None**.

AI-assisted tools were used during software development, code review, documentation, and packaging. Scientific assumptions, source selection, validation decisions, and final responsibility remained with the author.

## License
MIT License. Copyright (c) 2026 Paolo Taffache.
