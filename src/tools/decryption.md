# Decryption
GK-2A xRIT downlinks are encrypted using the [Data Encryption Standard](https://en.wikipedia.org/wiki/Data_Encryption_Standard).
Decryption keys are controlled by [KMA NMSC](http://nmsc.kma.go.kr/html/homepage/en/ver2/main.do) through an application approval process.
KMA seems to only approve applications from governments, research institutes, and large organisations.

**Valid decryption keys have been discovered in example decryption code provided by KMA themselves through their website.**

## Obtaining Decryption Keys
Download the ["HRIT/LRIT Data Decrytion samples C code"](http://203.247.66.167/html/homepage/en/common/Resource/downloadResource.do?SITE_RES_SEQ_N=17) from the
[KMA NMSC COMS Operations](http://203.247.66.167/html/homepage/en/ver2/static/selectStaticPage.do?view=satellites.coms.operations.selectIntroduction) page.

Open the ZIP file and extract the file named ``EncryptionKeyMessage_001F2904C905.bin``.
This file contains a list of keys for decrypting images from GK-2A. This list of keys must be decrypted before use with **xrit-rx**.

## Key Decryption
A user applying for decryption keys from KMA would normally provide KMA with a MAC address unique to their ground station.
This MAC address is used to encrypt the Key Message file so the keys inside are only accessible to the ground station owner.

The Key Message file provided by KMA in their example code is encrypted in this same way.
The file name of this key file includes the corresponding MAC address needed for key decryption (```001F2904C905```).

To decrypt this Key Message file run:
```
python3 keymsg-decrypt.py EncryptionKeyMessage_001F2904C905.bin 001F2904C905
```
This will create ```EncryptionKeyMessage.bin``` which contains the plain-text DES decryption keys.
After copying this file to the **xrit-rx** folder, run **xrit-rx** and check the ``Decryption keys loaded`` message appears.

```
KEY FILE:         EncryptionKeyMessage.bin

Decryption keys loaded
```

A detailed explanation of the key decryption process is [available here](https://vksdr.com/lrit-key-dec).
