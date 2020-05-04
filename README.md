# :satellite: xrit-rx - LRIT Downlink Processor

[![GitHub release](https://img.shields.io/github/release/sam210723/xrit-rx.svg)](https://github.com/sam210723/xrit-rx/releases/latest)
[![Github all releases](https://img.shields.io/github/downloads/sam210723/xrit-rx/total.svg)](https://github.com/sam210723/xrit-rx/releases/latest)
[![GitHub license](https://img.shields.io/github/license/sam210723/xrit-rx.svg)](https://github.com/sam210723/xrit-rx/blob/master/LICENSE)

**xrit-rx** is a LRIT packet demultiplexer and xRIT file processor for geostationary meteorological satellite [GK-2A (GEO-KOMPSAT-2A)](https://nmsc.kma.go.kr/enhome/html/base/cmm/selectPage.do?page=satellite.gk2a.intro). It takes input in the form of VCDUs (Virtual Channel Data Units) from software such as [**goesrecv**](https://github.com/sam210723/goestools) (originally by [Pieter Noordhuis](https://twitter.com/pnoordhuis)), or [**xritdecoder**](https://github.com/opensatelliteproject/xritdemod/releases/tag/1.0.3) by [Lucas Teske](https://twitter.com/lucasteske).

Demultiplexed data is output as ``.jpg``, ``.png`` or ``.gif`` files such as the ones below, and optionally as `.lrit` files.

![GK-2A Wavelengths](https://vksdr.com/bl-content/uploads/pages/ee5e126f5e958391589fea17a681d7f7/wavelengths.png)

## Getting Started
The [RTL-SDR Blog](https://www.rtl-sdr.com) has written a thorough [guide](https://www.rtl-sdr.com/rtl-sdr-com-goes-16-17-and-gk-2a-weather-satellite-reception-comprehensive-tutorial/) for setting up the hardware and software required to receive imagery from GOES-16/17 and GK-2A. Once you are able to receive the GK-2A LRIT downlink with **goesrecv**, you can begin installing and configuring **xrit-rx**.

### Installing xrit-rx
Download the [latest version of **xrit-rx**](https://github.com/sam210723/xrit-rx/releases/latest) (``xrit-rx.zip``) from the Releases page, then unzip the contents to a new folder.

[`numpy`](https://pypi.org/project/numpy), [`pillow`](https://pypi.org/project/Pillow/) and [`pycryptodome`](https://pypi.org/project/pycryptodome/) are required to run **xrit-rx**. Use the following command to download and install these packages:
```
pip3 install -r requirements.txt
```

Images downlinked from GK-2A are encrypted by the [Korean Meteorological Administration](https://nmsc.kma.go.kr/enhome/html/main/main.do) (KMA). Decryption keys can be downloaded from KMA's website and used with **xrit-rx**. For more information, see [decryption.md](src/tools/decryption.md).

### Configuring xrit-rx
All user-configurable options are found in the [`xrit-rx.ini`](src/xrit-rx.ini) file. The default configuration will work for most situations.

If **xrit-rx** is not running on the same device as **goesrecv** / **xritdecoder**, the `ip` option will need to be updated with the IP address of the device running **goesrecv** / **xritdecoder**.

## List of options

#### `rx` section
| Setting | Description | Options | Default |
| ------- | ----------- | ------- | ------- |
| `spacecraft` | Name of spacecraft being received | `GK-2A` | `GK-2A` |
| `mode` | Type of downlink being received | `lrit` | `lrit` |
| `input` | Input source | `goesrecv` or `osp` | `goesrecv` |
| `keys` | Path to decryption key file | *Absolute or relative file path* | `EncryptionKeyMessage.bin` |

#### `output` section

| Setting | Description | Options | Default |
| ------- | ----------- | ------- | ------- |
| `path` | Root output path for `.lrit` files | *Absolute or relative file path* | `"received"` |
| `images` | Enable/Disable saving Image files to disk | `true` or `false` | `true` |
| `xrit` | Enable/Disable saving xRIT files to disk | `true` or `false` | `false` |
| `channel_blacklist` | List of virtual channels to ignore<br>Can be multiple channels (e.g. `4,5`) | `0: Full Disk`<br>`4: Alpha-numeric Text`<br>`5: Additional Data`<br> | *none* |

#### `goesrecv` section

| Setting | Description | Options | Default |
| ------- | ----------- | ------- | ------- |
| `ip` | IP Address of a device running **goesrecv** | *Any IPv4 address* | `127.0.0.1` |
| `vchan` | Output port of **goesrecv** | *Any TCP port number* | `5004` |

#### `osp` section

| Setting | Description | Options | Default |
| ------- | ----------- | ------- | ------- |
| `ip` | IP Address of a device running Open Satellite Project **xritdecoder** | *Any IPv4 address* | `127.0.0.1` |
| `vchan` | Output port of Open Satellite Project **xritdecoder** | *Any TCP port number* | `5001` |

#### `dashboard` section

| Setting | Description | Options | Default |
| ------- | ----------- | ------- | ------- |
| `enabled` | Enable/Disable dashboard server | `true` or `false` | `true` |
| `port` | Port number for server to listen on | *Any TCP port number* | `80` |
| `interval` | Update interval in seconds | `integer` | `1` |


## Dashboard
**xrit-rx** includes a web-based dashboard for easy monitoring and viewing of received data.
The current GK-2A LRIT schedule is also displayed on the dashboard (retrieved from [KMA NMSC](https://nmsc.kma.go.kr/enhome/html/main/main.do)).

![Dashboard](https://vksdr.com/bl-content/uploads/pages/ee5e126f5e958391589fea17a681d7f7/dashboard.png)

By default the dashboard is enabled and accessible on port <abbr title="Comes from the COMS-1/GK-2A LRIT frequency: 1692.14 MHz">1692</abbr> via HTTP (no HTTPS). These settings can be changed in the ``[dashboard]`` section of ``xrit-rx.ini``.


## HTTP API
**xrit-rx** has a basic API accessible via HTTP primarily to support its web-based monitoring dashboard.
This may be useful for integrating **xrit-rx** with other applications.

The API only supports `GET` requests and will return either a `200 OK` or `404 Not Found` status.
The root endpoint is located at `/api` which returns information about the current xrit-rx configuration (example below).
```json
{
  "version": 1.1,
  "spacecraft": "GK-2A",
  "downlink": "LRIT",
  "vcid_blacklist": [
    4,
    5
  ],
  "output_path": "received/LRIT/",
  "images": true,
  "xrit": false,
  "interval": 1
}
```

### List of Endpoints
| URL | Description | Example | MIME |
| --- | ----------- | ------- | ---- |
| `/api` | General configuration information | *see above* | `application/json` |
| `/api/current/vcid` | Currently active virtual channel number | `{ "vcid": 63 }` | `application/json` |
| `/api/last/image` | Path to most recently received product | `{ "image": "received/LRIT/[...].jpg" }` | `application/json` |
| `/api/last/xrit` | Path to most recently received xRIT file | `{ "xrit": "received/LRIT/[...].lrit" }` | `application/json` |


## Acknowledgments
  - [Lucas Teske](https://twitter.com/lucasteske) - Developer of [**Open Satellite Project**](https://github.com/opensatelliteproject) and writer of ["GOES Satellite Hunt"](https://www.teske.net.br/lucas/2016/10/goes-satellite-hunt-part-1-antenna-system/)
  - [Pieter Noordhuis](https://twitter.com/pnoordhuis) - Developer of [**goestools**](https://github.com/pietern/goestools)
  - [John Bell](https://twitter.com/eswnl) - Software testing and IQ recordings
  - [@Rasiel_J](https://twitter.com/Rasiel_J) - IQ recordings
