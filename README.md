# :satellite: xrit-rx - LRIT Downlink Processor

**xrit-rx** is a LRIT packet demultiplexer and xRIT file processor for geostationary meteorological satellite [GK-2A (GEO-KOMPSAT-2A)](https://www.wmo-sat.info/oscar/satellites/view/34). It takes input in the form of VCDUs (Virtual Channel Data Units) from software such as [goesrecv](https://github.com/pietern/goestools) by [Pieter Noordhuis](https://twitter.com/pnoordhuis) or [xritdecoder](https://github.com/opensatelliteproject/xritdemod/releases/tag/1.0.3) by [Lucas Teske](https://twitter.com/lucasteske).

Data is output in the form of ``.lrit`` files and/or processed images (``.jpg`` / ``.png`` / ``.gif``) such as the ones below.

![GK-2A Wavelengths](https://vksdr.com/bl-content/uploads/pages/ee5e126f5e958391589fea17a681d7f7/GK-2AWavelengths.png)
