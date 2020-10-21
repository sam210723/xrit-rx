# Change Log
All notable changes to this project will be documented in this file.

<details>
<summary>Unreleased changes</summary>

### Added
  - 

### Changed
  - 

### Fixed
  - 
</details>


## [v1.3](https://github.com/sam210723/xrit-rx/releases/tag/v1.3) - 2020-07-12
Added support for multi-channel HRIT imagery using [libjpeg](https://github.com/thorfdbg/libjpeg) for JPEG2000 conversion.

<details>
<summary>Details</summary>

### Added
  - Support for HRIT full disk imagery (see [HRIT Decoding - J2K and missing CPPDUs](https://github.com/sam210723/xrit-rx/issues/15))
  - HRIT image processing tool ([tools\hrit-img.py](https://github.com/sam210723/xrit-rx/blob/master/src/tools/hrit-img.py))
  - JP2 (JPEG2000) to PPM converstion using [libjpeg](https://github.com/thorfdbg/libjpeg) (licensed under [GPLv3](https://github.com/thorfdbg/libjpeg/blob/master/README.license.gpl))
  - UDP socket for receiving VCDUs from hardware modems such as the ETRA D8L
  - to_hex() debugging utility method
  - Link to GitHub release page on dashboard

### Changed
  - Indicate multi-segment progress per-wavelength rather than for the entire product
  - Using `pathlib` over `os` module for some file operations
  - Include spacecraft and downlink in dashboard schedule title
  - Renamed "Last Image" dashboard block to "Latest Image"
  - Renamed `last/image` and `last/xrit` API endpoints to `latest/image` and `latest/xrit`

### Fixed
  - TP_File triggering with M_PDU header offset ([relevant issue comment](https://github.com/sam210723/xrit-rx/issues/15#issuecomment-643079493))
  - Output directory checking
  - Handling of safe exit cases
  - Handling of `PIL.UnidentifiedImageError`
  - Handling of missing configuration sections and options
</details>


## [v1.2](https://github.com/sam210723/xrit-rx/releases/tag/v1.2) - Monitoring Dashboard <span style="font-size: 17px; float: right;">2020-05-14</span>
Added a monitoring dashboard and JSON API running from a built in web server.

<details>
<summary>Details</summary>

### Added
  - Web-based monitoring dashboard
  - JSON API for updating dashboard
  - Access of received data over HTTP
</details>


## [v1.1](https://github.com/sam210723/xrit-rx/releases/tag/v1.1) - Automatic Product Generation <span style="font-size: 17px; float: right;">2020-02-14</span>
Products (images/text) are now output directly from xrit-rx rather than relying on ``lrit-img.py`` and ``lrit-add.py``.
Progress bar for multi-segment images and colour-coded success/failure messages were also added.

<details>
<summary>Details</summary>

### Added
  - Output products (images/text) directly from demuxer
  - Transparent enhanced image output option
  - Added check for encrypted LRIT files in ``lrit-img.py`` and ``lrit-add.py``
  - Output file type options (Image or xRIT files)
  - Demuxer configuration tuple
  - Channel handler configuration tuple
  - Detect GK-2A LRIT Daily Operation Plan
  - Console output colours
  - Progress bar for multi-segment images

### Changed
  - Default key file name **(check when upgrading from an old version)**
  - ``keymsg-decrypt.py`` output file name
  - Disable product output if no keys loaded
  - Write single fill VCDU to packet file on VCID change
  - Rename FILL packets to IDLE packets

### Fixed
  - Missing TrueType font exception
</details>


## [v1.0.3](https://github.com/sam210723/xrit-rx/releases/tag/v1.0.3) - Infrared Enhancement Tool <span style="font-size: 17px; float: right;">2019-12-09</span>
Added work-around for ``COMSFOG`` and ``COMSIR1`` transmission issue, an infrared imagery enhancement tool, and fixed some demuxer bugs.

<details>
<summary>Details</summary>

### Added
  - IR enhancement tool ([tools\enhance-ir.py](https://github.com/sam210723/xrit-rx/blob/master/src/tools/enhance-ir.py))
  - Extra demuxer info in verbose mode

### Changed
  - Write incomplete TP_Files to disk on VCID change ([COMSFOG / COMSIR1 issue](https://github.com/sam210723/xrit-rx/issues/5))
  - Clear xRIT key header after file is decrypted (avoids double-decryption)

### Fixed
  - Free-running loop while demuxing a file
  - Exception caused by key index 0 in xrit-decrypt
  - Final file from VCDU dump not being processed
</details>


## [v1.0.2](https://github.com/sam210723/xrit-rx/releases/tag/v1.0.2) - Decryption Tools <span style="font-size: 17px; float: right;">2019-08-31</span>
Added decryption tools, an option to blacklist individual virtual channels, and fixed some demuxer bugs.

<details>
<summary>Details</summary>

### Added
  - Virtual channel (VCID) blacklist
  - xRIT file decryption tool ([tools\xrit-decrypt.py](https://github.com/sam210723/xrit-rx/blob/master/src/tools/xrit-decrypt.py))
  - Key file decryption tool ([tools\keymsg-decrypt.py](https://github.com/sam210723/xrit-rx/blob/master/src/tools/keymsg-decrypt.py))

### Fixed
  - VCDU continuity counter
  - Handle CP_PDU headers spanning multiple M_PDUs
</details>


## [v1.0.1](https://github.com/sam210723/xrit-rx/releases/tag/v1.0.1) - Data Processing Tools <span style="font-size: 17px; float: right;">2019-07-29</span>
Added tools for bulk processing LRIT IMG and ADD files, plus some minor code refactoring.

<details>
<summary>Details</summary>

### Added
  - GK-2A virtual channel names
  - GK-2A file type names
  - LRIT image file processor ([tools\lrit-img.py](https://github.com/sam210723/xrit-rx/blob/master/src/tools/lrit-img.py))
  - LRIT additional data processor ([tools\lrit-add.py](https://github.com/sam210723/xrit-rx/blob/master/src/tools/lrit-add.py))

### Changed
  - Enum for CP_PDU sequence
  - CCITT LUT function location
  - Tool class location

### Fixed
  - Socket connection reset exception
</details>


## [v1.0](https://github.com/sam210723/xrit-rx/releases/tag/v1.0) - Initial Release <span style="font-size: 17px; float: right;">2019-07-23</span>
Initial release based on the [COMS-1 project](https://github.com/sam210723/COMS-1).
