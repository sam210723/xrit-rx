# :satellite: xrit-rx - LRIT/HRIT Downlink Processor

[![GitHub release](https://img.shields.io/github/release/sam210723/xrit-rx.svg)](https://github.com/sam210723/xrit-rx/releases/latest)
[![Python versions](https://img.shields.io/badge/python-3.6%20%7C%203.7%20%7C%203.8%20%7C%203.9-blue)](https://www.python.org/)
[![Github all releases](https://img.shields.io/github/downloads/sam210723/xrit-rx/total.svg)](https://github.com/sam210723/xrit-rx/releases/latest)
[![GitHub license](https://img.shields.io/github/license/sam210723/xrit-rx.svg)](https://github.com/sam210723/xrit-rx/blob/master/LICENSE)

**xrit-rx** is a packet demultiplexer and file processor for receiving images from geostationary weather satellite [GEO-KOMPSAT-2A (GK-2A)](https://nmsc.kma.go.kr/enhome/html/base/cmm/selectPage.do?page=satellite.gk2a.intro). It is designed for use with [**SatDump**](https://github.com/altillimity/SatDump) by [Aang254](https://twitter.com/aang254), [**goesrecv**](https://github.com/sam210723/goestools) (originally by [Pieter Noordhuis](https://twitter.com/pnoordhuis)), or [**xritdecoder**](https://github.com/opensatelliteproject/xritdemod/releases/tag/1.0.3) by [Lucas Teske](https://twitter.com/lucasteske).

**xrit-rx** receives [Virtual Channel Data Units (VCDUs)](https://nmsc.kma.go.kr/resources/homepage/pdf/GK2A_LRIT_Mission_Specification_Document_v1.0.pdf#page=27) over a local network connection from either **SatDump**, **goesrecv** or **xritdecoder** and demultiplexes them into separate virtual channels, each containing a different type of image data.
The demultiplexed packets are assembled into complete files which are output as images such as the ones below.

![GK-2A Wavelengths](https://vksdr.com/bl-content/uploads/pages/ee5e126f5e958391589fea17a681d7f7/wavelengths.png)

## Getting Started
A guide for setting up the hardware and software components of a GK-2A LRIT receiver is [available on my site](https://vksdr.com/xrit-rx). It also covers the types of images that can be received, image post-processing techniques and data decryption.

<a href="https://vksdr.com/xrit-rx" target="_blank"><p align="center"><img src="https://vksdr.com/bl-content/uploads/pages/ee5e126f5e958391589fea17a681d7f7/guide-thumb-light.png" title="Receiving Images from Geostationary Weather Satellite GEO-KOMPSAT-2A"></p></a>

The [RTL-SDR Blog](https://www.rtl-sdr.com) has also [written a guide](https://www.rtl-sdr.com/rtl-sdr-com-goes-16-17-and-gk-2a-weather-satellite-reception-comprehensive-tutorial/) for setting up the hardware and software required to receive imagery from GOES-16/17 and GK-2A. Once you are able to receive the GK-2A LRIT downlink with **SatDump**, **goesrecv** or **xritdecoder**, you can begin installing and configuring **xrit-rx**.

### Installing xrit-rx
Download the [latest version of **xrit-rx**](https://github.com/sam210723/xrit-rx/releases/latest) (``xrit-rx.zip``) from the Releases page, then unzip the contents to a new folder.

Some extra Python packages are required to run **xrit-rx**. Use the following command to download and install these packages:
```
pip3 install -r requirements.txt
```

Images downlinked from GK-2A are encrypted by the [Korean Meteorological Administration](https://nmsc.kma.go.kr/enhome/html/main/main.do) (KMA). Decryption keys can be downloaded from KMA's website and used with **xrit-rx**.
More information is [available in the setup guide](https://vksdr.com/xrit-rx#keys).

### Configuring xrit-rx
All user-configurable options are found in [`xrit-rx.ini`](src/xrit-rx.ini). The default configuration will work for most situations.

If **xrit-rx** is not running on the same device as **SatDump** / **goesrecv** / **xritdecoder**, the `ip` option will need to be updated with the IP address of the device running **SatDump** / **goesrecv** / **xritdecoder**.

[Click here for a full list of configuration options](#configuration-options)


## Dashboard
**xrit-rx** includes a web-based dashboard for easy monitoring and viewing of received data.
The current GK-2A LRIT schedule is also displayed on the dashboard (retrieved from [KMA NMSC](https://nmsc.kma.go.kr/enhome/html/main/main.do)).

![Dashboard](https://vksdr.com/bl-content/uploads/pages/ee5e126f5e958391589fea17a681d7f7/dashboard.png)

By default the dashboard is enabled and accessible on port <abbr title="Comes from the COMS-1/GK-2A LRIT frequency: 1692.14 MHz">1692</abbr> via HTTP (no HTTPS). These settings can be changed in the ``[dashboard]`` section of ``xrit-rx.ini``.


## Configuration Options

#### `rx` section
| Setting      | Description | Options | Default |
| ------------ | ----------- | ------- | ------- |
| `spacecraft` | Name of spacecraft being received | `GK-2A` | `GK-2A` |
| `mode`       | Type of downlink being received | `lrit` or `hrit` | `lrit` |
| `input`      | Input source | `nng`, `tcp` or `udp` | `nng` |
| `keys`       | Path to decryption key file | *Absolute or relative file path* | `EncryptionKeyMessage.bin` |

#### `output` section

| Setting   | Description | Options | Default |
| --------- | ----------- | ------- | ------- |
| `path`    | Root output path for received files | *Absolute or relative file path* | `"received"` |
| `images`  | Enable/Disable saving Image files to disk | `true` or `false` | `true` |
| `xrit`    | Enable/Disable saving xRIT files to disk | `true` or `false` | `false` |
| `enhance` | Automatically enhance LRIT IR105 images | `true` or `false` | `true` |
| `ignored` | List of virtual channels to ignore<br>Can be multiple channels (e.g. `4,5`) | `0: Full Disk`<br>`4: Alpha-numeric Text`<br>`5: Additional Data`<br> | *none* |

#### `nng` section

| Setting | Description | Options | Default |
| ------- | ----------- | ------- | ------- |
| `ip`    | IP address of a **nanomsg** data source (e.g. **SatDump** or **goesrecv**) | *Any IPv4 address* | `127.0.0.1` |
| `port`  | Server port of a **nanomsg** data source | *Any TCP port number* | `5004` |

#### `tcp` section

| Setting | Description | Options | Default |
| ------- | ----------- | ------- | ------- |
| `ip`    | IP address of a TCP data source (e.g. **xritdecoder**) | *Any IPv4 address* | `127.0.0.1` |
| `port`  | Server port of a TCP data source | *Any TCP port number* | `5001` |

#### `udp` section

| Setting | Description | Options | Default |
| ------- | ----------- | ------- | ------- |
| `ip`    | IP address to bind UDP socket to | *Any IPv4 address* | `127.0.0.1` |
| `port`  | Port number to bind UDP socket to | *Any UDP port number* | `5002` |

#### `dashboard` section

| Setting    | Description | Options | Default |
| ---------- | ----------- | ------- | ------- |
| `enabled`  | Enable/Disable dashboard server | `true` or `false` | `true` |
| `port`     | Port number for server to listen on | *Any TCP port number* | `1692` |
| `interval` | Update interval in seconds | `integer` | `1` |



## Command Line Arguments
Most of the **xrit-rx** command line arguments are only useful for development and debugging purposes. All configuration required for decoding images is done through `xrit-rx.ini` as outlined above.

```
usage: xrit-rx.py [-h] [-v] [--config CONFIG] [--file FILE] [--dump DUMP] [--no-exit]

optional arguments:
  -h, --help       Show this help message and exit
  -v, --verbose    Enable verbose console output
  --config CONFIG  Path to configuration file (*.ini)
  --file FILE      Path to VCDU packet file
  --dump DUMP      Write VCDU packets to file
  --no-exit        Pause main thread before exiting
```



## HTTP API
**xrit-rx** has a basic API accessible via HTTP primarily to support its web-based monitoring dashboard.
This may be useful for integrating **xrit-rx** with other applications.

The API only supports `GET` requests and will return either a `200 OK` or `404 Not Found` status.
The root endpoint is located at `/api` which returns information about the current xrit-rx configuration (example below).
```json
{
  "version": 1.4,
  "spacecraft": "GK-2A",
  "downlink": "LRIT",
  "ignored_vcids": [4, 5],
  "images": true,
  "xrit": false,
  "interval": 1
}
```

### List of Endpoints
| URL                       | Description                                  | Example                                    | MIME               |
| ------------------------- | -------------------------------------------- | ------------------------------------------ | ------------------ |
| `/api`                    | General configuration information            | *see above*                                | `application/json` |
| `/api/received/[...]`     | Received data access                         | *binary data*                              | `image/...`        |
| `/api/current/vcid`       | Currently active virtual channel number      | `{ "vcid": 63 }`                           | `application/json` |
| `/api/current/progress`   | Progress percentage for multi-segment images | `{ "progress": 50 }`                       | `application/json` |
| `/api/latest/image`       | Path to most recently received product       | `{ "image": "20190722/FD/IMG_[...].jpg" }` | `application/json` |
| `/api/latest/xrit`        | Path to most recently received xRIT file     | `{ "xrit": "20190722/FD/IMG_[...].lrit" }` | `application/json` |


## Acknowledgments
  - [Lucas Teske](https://twitter.com/lucasteske) - Developer of [**Open Satellite Project**](https://github.com/opensatelliteproject) and writer of ["GOES Satellite Hunt"](https://www.teske.net.br/lucas/2016/10/goes-satellite-hunt-part-1-antenna-system/)
  - [Aang254](https://twitter.com/aang254) - Developer of [**SatDump**](https://github.com/altillimity/SatDump)
  - [Pieter Noordhuis](https://twitter.com/pnoordhuis) - Developer of [**goestools**](https://github.com/pietern/goestools)
  - [John Bell](https://twitter.com/eswnl) - Software testing and IQ recordings
  - ["kisaa"](https://github.com/kisaa) - GK-2A HRIT debugging and packet recordings
  - [@Rasiel_J](https://twitter.com/Rasiel_J) - IQ recordings
