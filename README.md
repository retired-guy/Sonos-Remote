# Sonos-Remote
Small touchscreen display for a Sonos zone

Tested on RPi Zero WH with Hyperpixel 4" touchscreen display

In order to run as the pi user to access the framebuffer, you'll need to add it to the video group:

usermod -a -G video pi

To start this at boot, create a service file and launch the bash script with it: https://www.raspberrypi.org/documentation/linux/usage/systemd.md

![photo](https://1.bp.blogspot.com/-jDm0RF67ovk/YPIYBy5tLhI/AAAAAAAAulo/qTaQYNSF8Q4pAKGwj8CGEMkK-G04xG_hwCLcBGAsYHQ/s2048/4F80C9C8-EEB6-4BDA-9274-17A5EF7EC377.jpeg)
