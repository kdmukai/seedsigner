# Build an offline, airgapped Bitcoin signing device for less than $50!

![Image of SeedSigner in an Orange Pill enclosure](docs/img/Orange_Pill.JPG)

---------------

## Contributors Welcome!

* Now that the overall code structure has been largely established, we welcome potential feature additions/improvements
* We are also actively seeking contributors to create walkthroughs/tutorials on building and using SeedSigner
* We are seeking a smaller group of more technical users to test new features and upcoming releases

Please contact @SeedSigner on Twitter/Telegram to inquire with any questions about contributing!

---------------

## Shopping List

To build a SeedSigner, you will need:

* Raspberry Pi Zero (version 1.3 with no wireless capability)
* Waveshare 1.3" 240x240 pxl LCD (more info at https://www.waveshare.com/wiki/1.3inch_LCD_HAT)
* Pi Zero-conpatible camera (tested to work with the Aokin / AuviPal 5MP 1080p with OV5647 Sensor)

Notes:
* Other cameras with the above sensor module should work, but may not fit in the Orange Pill enclosure
* Choose the Waveshare screen carefully; make sure to purchase the model that has a resolution of 240x240 pixels

The easiest way to install the software is to download the "seedsigner_X_X_X.zip" file in the current release, extract the seedsigner .img file, and write it to a MicroSD card (at least 4GB in size or larger). Then install the MicroSD in the assembled hardware and off you go.

---------------

## Now make your own "Orange Pill" enclosure too!

The Orange Pill enclosure design has been open-sourced! Check out the "Orange_Pill" folder in this repo. You'll need the following additional hardware to assemble it:

* 4 x F-F M2.5 spacers, 10mm length
* 4 x M2.5 pan head screws, 6mm length
* 4 x M2.5 pan head screws, 12mm length

The upper and lower portions of the enclosure can be printed with a conventional FDM 3D printer, 0.2mm layer height is fine, no supports necessary. The buttons and joystick nub should be produced with a SLA/resin printer (orient the square hole on the joystick nub away from the build plate). An overview of the entire assembly process can be found here:

https://youtu.be/aIIc2DiZYcI

---------------

### Feature Highlights:
* Calculate word 12/24 of a BIP39 seed phrase
* Create 24-word BIP39 seed phrase with 99 dice rolls
* Temporarily store up to 3 seed phrases while device is powered
* Native Segwit Multisig XPUB generation w/ QR display
* Scan and parse transaction data from animated QR codes
* Sign transactions & transfer XPUB data using animated QR codes
* Support for Bitcoin Mainnet & Testnet
* Responsive, event-driven user interface
* Only valid input letters appear during seed word entry (time-saver!)

### Considerations:
* Built for compatibility with Specter-desktop, Sparrow and BlueWallet Vaults
* Current release takes ~50 seconds to boot before menu appears (be patient!)
* Always test your setup before transfering larger amounts of bitcoin (try testnet first!)
* Currently ONLY generating Native Segwit Multisig Xpubs
* (Holding the screen upside-down or at a slight angle can significantly reduce glare)
* Check out our "seedsigner" telegram group for community help / feedback: (https://t.me/joinchat/GHNuc_nhNQjLPWsS)
* If you think SeedSigner adds value to the Bitcoin ecosystem, please help me spread the word! (tweets, pics, videos, etc.)

### Planned Upcoming Improvements / Functionality:
* Support for single-signature XPUB generation / signing
* Support for BIP39 passphrases
* User-guided manual QR transcription to quickly input seed phrases
* Low/Med/High customizable QR density
* Other optimizations based on user feedback!

---------------

## MANUAL BUILD INSTRUCTIONS:
Begin by preparing a copy of the Raspberry Pi Lite operating system (https://www.raspberrypi.org/software/operating-systems/) on a MicroSD card. Their [Raspberry Pi Imager](https://www.raspberrypi.org/software/) tool makes this easy.

#### Update SD card
After flashing the SD card, re-insert it into your computer and navigate to the drive named boot:

```
# Mac/Linux
cd /Volumes/boot

# Windows (alter with correct drive letter):
cd e:
```

Then create a blank file there called `ssh`. This will allow us to remotely access the device from the command line.
```
# Mac/Linux:
touch ssh

# Windows:
type nul > ssh
```

We also need to enable the support for the second SPI channel (screen uses one channel, touch support uses another). Edit the config.txt:

```
# mac/Linux:
nano config.txt

# windows
notepad.exe config.txt  # ??
```

Find the lines that look like this:

```
# Uncomment some or all of these to enable the optional hardware interfaces
#dtparam=i2c_arm=on
#dtparam=i2s=on
#dtparam=spi=on
```

Then uncomment the `spi=on` line and add support for the second SPI channel:

```
# Uncomment some or all of these to enable the optional hardware interfaces
#dtparam=i2c_arm=on
#dtparam=i2s=on
dtparam=spi=on
dtoverlay=spi1-1cs
```

Then `CTRL-X` to exit and `y` to save changes.


## Installing dependencies

SeedSigner installation and configuration requires an internet connection on the device to download the necessary libraries and code. But because the Pi Zero 1.3 does not have onboard wifi, you have two options:

1. Run these steps on a separate Raspberry Pi 2/3/4 or Zero W which can connect to the internet and then transfer the SD card to the Pi Zero 1.3 when complete.
2. OR configure the Pi Zero 1.3 directly by relaying through your computer's internet connection over USB. See instructions [here](docs/usb_relay.md).

The next steps will assume that you have connected a keyboard & monitor to the device or SSHed directly into the Pi (`ssh pi@raspberrypi.local`; default password is `raspberry`).


### Configure the Pi
First change the default password for the pi user:

```
passwd
# (when prompted, the default password is "raspberry")
```

Now change the device's default name from raspberrypi:

```
sudo nano /etc/hostname
```

Change the entry to any name you like (typically seedsigner). Hit `CTRL-X` to exit and then `y` to save your changes. Then:

```
sudo nano /etc/hosts
```

You should see an entry like:

```
127.0.0.1   raspberrypi
```

Update `raspberrypi` to match whatever you set in /etc/hostname. `CTRL-X` and `y`.

Restart the pi: `sudo reboot`

The next time you SSH in, instead of `ssh pi@raspberrypi.local` you'll now use the new hostname:

```
ssh pi@seedsigner.local
```

Ensure the pi user can access SPI

```
sudo usermod -a -G spi,gpio pi
```

On the Pi bring up its system config:
```
sudo raspi-config
```

Set the following:
* `Interface Options`:
    * `Camera`: enable
    * `SPI`: enable
* `Localisation Options`:
    * `Locale`: arrow up and down through the list and select or deselect languages with the spacebar.
        * `en_US.UTF-8 UTF-8` for US English
* WiFi settings (only necessary for the option #1 setup above)

Exit and reboot when prompted within the raspi-config interface.

When it's back up you should now confirm that you have two SPI channels enabled:

```
ls -l /dev/spidev*
```

Should see something like:

```
crw-rw---- 1 root spi 153, 0 Jul 25 05:52 /dev/spidev0.0
crw-rw---- 1 root spi 153, 1 Jul 25 05:52 /dev/spidev0.1
crw-rw---- 1 root spi 153, 2 Jul 25 05:52 /dev/spidev1.0
```

Install these dependencies:
```
sudo apt-get update && sudo apt-get install -y wiringpi python3-pip python3-numpy python-pil libopenjp2-7 ttf-mscorefonts-installer git python3-opencv libzbar0 python3-picamera
```

Install the [C library for Broadcom BCM 2835](http://www.airspayce.com/mikem/bcm2835/):
```
wget http://www.airspayce.com/mikem/bcm2835/bcm2835-1.60.tar.gz
tar zxvf bcm2835-1.60.tar.gz
cd bcm2835-1.60/
sudo ./configure
sudo make && sudo make check && sudo make install
cd ..
rm bcm2835-1.60.tar.gz
```

Download SeedSigner
```
git clone https://github.com/SeedSigner/seedsigner
```

Install python dependencies:
```
cd seedsigner
pip3 install -r requirements.txt
```

Modify the systemd to run SeedSigner at boot:
```
sudo nano /etc/systemd/system/seedsigner.service
```

Add the following contents to the file:
```
[Unit]
Description=Seedsigner

[Service]
User=pi
WorkingDirectory=/home/pi/seedsigner/src/
ExecStart=/usr/bin/python3 main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Use Control + O, then [enter], to write the file.
Then use Control + X, to exit the program.

Run `sudo systemctl enable seedsigner.service` to enable service on boot. (This will restart the seedsigner code automatically at startup and if it crashes.)

(Optional) Modify the system swap configuration to disable virtual memory:
```sudo nano /etc/dphys-swapfile```
Change `CONF_SWAPSIZE=100` to `CONF_SWAPSIZE=0`

Use Control + O, then [enter], to write the file.
Then use Control + X, to exit the program.

If you completed these steps on a separate Pi (option #1), shut down the pi with `sudo shutdown --poweroff now` and then transfer the SD card to the Pi Zero 1.3 (_note: the LCD Hat will also run fine on a Raspberry Pi 2/3/4 or Zero W; just remember to disable networking if you want to run the software in isolation)_.

OR if you're working directly on the Pi Zero 1.3 (option #2), just reboot it:
```
sudo reboot
```

It will take about a minute after the Pi is powered on for the GUI to launch -- be patient!

_Reminder: If you used option #2, [return the guide](docs/usb_relay.md) to remove the internet access over USB configuration._


## Run the tests
see: [tests/README.md](tests/README.md)


# Advanced developer notes

## Backup an SD card

You can back up and restore any size SD card but the process is a little inefficient so the bigger the source SD card, the bigger the backup will be and the longer it'll take to create (and even longer to image back to a new SD card), even if most of the card is blank.

You can restore a backup image to an SD card of the same or larger size. So it's strongly recommended to do repetitive development work on a smaller card that's easier to backup and restore. Once the image is stabilized, then write it to a bigger card, if necessary (that being said, there's really no reason to use a large SD card for SeedSigner. An 8GB SD card is more than big enough).

Insert the SD card into a Mac/Linux machine and create a compressed img file.

First verify the name of your SD card:

```
# Mac:
diskutil list

# Linux:
sudo fdisk -l
```

It will most likely be `/dev/disk1` on most systems.

Now we use `dd` to clone and `gzip` to compress it. Note that we reference the SD card by adding an `r` in front of the disk name. This speeds up the cloning considerably.

```
sudo dd if=/dev/rdisk1 conv=sparse bs=4m | gzip -9 > seedsigner.img.gz
```

The process should take about 15 minutes and will typically generate a roughly 1.1GB image.

To restore from your backup image, just use the Raspberry Pi Imager. Remember that you can only write it to an SD card of equal or greater size than the original SD card.
