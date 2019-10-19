# :satellite: xrit-rx - LRIT Downlink Processor

**xrit-rx** is a LRIT packet demultiplexer and xRIT file processor for geostationary meteorological satellite [GK-2A (GEO-KOMPSAT-2A)](https://www.wmo-sat.info/oscar/satellites/view/34). It takes input in the form of VCDUs (Virtual Channel Data Units) from software such as [**goesrecv**](https://github.com/sam210723/goestools) ([original](https://github.com/pietern/goestools)) by [Pieter Noordhuis](https://twitter.com/pnoordhuis), or [**xritdecoder**](https://github.com/opensatelliteproject/xritdemod/releases/tag/1.0.3) by [Lucas Teske](https://twitter.com/lucasteske).

Demultiplexed data is output as `.lrit` files which can be processed into images such as the ones below.

![GK-2A Wavelengths](https://vksdr.com/bl-content/uploads/pages/ee5e126f5e958391589fea17a681d7f7/wavelengths.png)

## Getting Started
The [RTL-SDR Blog](https://www.rtl-sdr.com) has written a thorough [guide](https://www.rtl-sdr.com/rtl-sdr-com-goes-16-17-and-gk-2a-weather-satellite-reception-comprehensive-tutorial/) for setting up the hardware and software required to receive imagery from GOES-16/17 and GK-2A. Once you are able to receive the GK-2A LRIT downlink with **goesrecv**, you can begin installing and configuring **xrit-rx**.

### Installing xrit-rx
**xrit-rx** requires Python packages [`pycryptodome`](https://pypi.org/project/pycryptodome/) and [`pillow`](https://pypi.org/project/Pillow/) to be installed using the following command:
```
pip3 install pycryptodome pillow
```

Once these packages are installed, download the [latest version of **xrit-rx**](https://github.com/sam210723/xrit-rx/releases/latest) ([direct](https://github.com/sam210723/xrit-rx/releases/latest/download/xrit-rx.zip)) from the Releases page.

### Configuring xrit-rx
All user-configurable options are found in the [`xrit-rx.ini`](xrit-rx.ini) file. The default configuration will work for most situations.

If **xrit-rx** is not running on the same device as **goesrecv**, the `ip` option will need to be updated with the IP address of the device running **goesrecv**.

### List of options

#### `rx` section
| Setting | Description | Options | Default |
| ------- | ----------- | ------- | ------- |
| `spacecraft` | Name of spacecraft being received | `GK-2A` | `GK-2A` |
| `mode` | Type of downlink being received | `lrit` | `lrit` |
| `input` | Input source | `goesrecv` or `osp` | `goesrecv` |
| `keys` | Path to decryption key file | *Absolute or relative file path* | `EncryptionKeyMessage.bin.dec` |

#### `output` section

| Setting | Description | Options | Default |
| ------- | ----------- | ------- | ------- |
| `path` | Root output path for `.lrit` files | *Absolute or relative file path* | `"received"` |
| `channel_blacklist` | List of virtual channels to ignore<br>Can be multiple channels (e.g. `4,5`) | `0: Full Disk`<br>`4: Alpha-numeric Text`<br>`5: Additional Data`<br> | *none* |

#### `goesrecv` section

| Setting | Description | Options | Default |
| ------- | ----------- | ------- | ------- |
| `ip` | IP Address of a Raspberry Pi running **goesrecv** | *Any IPv4 address* | `127.0.0.1` |
| `vchan` | Output port of **goesrecv** | *Any TCP port number* | `5004` |

#### `osp` section

| Setting | Description | Options | Default |
| ------- | ----------- | ------- | ------- |
| `ip` | IP Address of a PC running Open Satellite Project **xritdecoder** | *Any IPv4 address* | `127.0.0.1` |
| `vchan` | Output port of Open Satellite Project **xritdecoder** | *Any TCP port number* | `5001` |


## Acknowledgments
  - [Lucas Teske](https://twitter.com/lucasteske) - Developer of [**Open Satellite Project**](https://github.com/opensatelliteproject) and writer of ["GOES Satellite Hunt"](https://www.teske.net.br/lucas/2016/10/goes-satellite-hunt-part-1-antenna-system/)
  - [Pieter Noordhuis](https://twitter.com/pnoordhuis) - Developer of [**goestools**](https://github.com/pietern/goestools)
  - [John Bell](https://twitter.com/eswnl) - Software testing and IQ recordings
  - [@Rasiel_J](https://twitter.com/Rasiel_J) - IQ recordings
