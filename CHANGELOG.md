# Change Log
All notable changes to this project will be documented in this file.

<details>
<summary>Unreleased changes</summary>

### Added
  - to_hex() utility method

### Changed
  - 

### Fixed
  - Handling of safe exit cases
</details>


## [v1.2](https://github.com/sam210723/xrit-rx/releases/tag/v1.2) - 2020-05-14
Added a monitoring dashboard and JSON API running from a built in web server.

<details>
<summary>Details</summary>

### Added
  - Web-based monitoring dashboard
  - JSON API for updating dashboard
  - Access of received data over HTTP
</details>


## [v1.1](https://github.com/sam210723/xrit-rx/releases/tag/v1.1) - 2020-02-14
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


## [v1.0.3](https://github.com/sam210723/xrit-rx/releases/tag/v1.0.3) - 2019-12-09
Added work-around for ``COMSFOG`` and ``COMSIR1`` transmission issue, an infrared imagery enhancement tool, and fixed some demuxer bugs.

<details>
<summary>Details</summary>

### Added
  - IR enhancement tool ([tools\enhance-ir.py](https://github.com/sam210723/xrit-rx/tree/master/tools/enhance-ir.py))
  - Extra demuxer info in verbose mode

### Changed
  - Write incomplete TP_Files to disk on VCID change ([COMSFOG / COMSIR1 issue](https://github.com/sam210723/xrit-rx/issues/5))
  - Clear xRIT key header after file is decrypted (avoids double-decryption)

### Fixed
  - Free-running loop while demuxing a file
  - Exception caused by key index 0 in xrit-decrypt
  - Final file from VCDU dump not being processed
</details>


## [v1.0.2](https://github.com/sam210723/xrit-rx/releases/tag/v1.0.2) - 2019-08-31
Added decryption tools, an option to blacklist individual virtual channels, and fixed some demuxer bugs.

<details>
<summary>Details</summary>

### Added
  - Virtual channel (VCID) blacklist
  - xRIT file decryption tool ([tools\xrit-decrypt.py](https://github.com/sam210723/xrit-rx/tree/master/tools/xrit-decrypt.py))
  - Key file decryption tool ([tools\keymsg-decrypt.py](https://github.com/sam210723/xrit-rx/tree/master/tools/keymsg-decrypt.py))

### Fixed
  - VCDU continuity counter
  - Handle CP_PDU headers spanning multiple M_PDUs
</details>


## [v1.0.1](https://github.com/sam210723/xrit-rx/releases/tag/v1.0.1) - 2019-07-29
Added tools for bulk processing LRIT IMG and ADD files, plus some minor code refactoring.

<details>
<summary>Details</summary>

### Added
  - GK-2A virtual channel names
  - GK-2A file type names
  - LRIT image file processor ([tools\lrit-img.py](https://github.com/sam210723/xrit-rx/tree/master/tools/lrit-img.py))
  - LRIT additional data processor ([tools\lrit-add.py](https://github.com/sam210723/xrit-rx/tree/master/tools/lrit-add.py))

### Changed
  - Enum for CP_PDU sequence
  - CCITT LUT function location
  - Tool class location

### Fixed
  - Socket connection reset exception
</details>


## [v1.0](https://github.com/sam210723/xrit-rx/releases/tag/v1.0) - 2019-07-23
Initial release based on the [COMS-1 project](https://github.com/sam210723/COMS-1).
