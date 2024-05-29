# Arch Linux Kernel Manager

A GTK4 Python application which installs and removes Linux Kernels on Arch Linux based systems.

Installation and removal of Kernels is carried out using Pacman.

Kernel packages are sourced from the [Arch Linux Archive](https://wiki.archlinux.org/title/Arch_Linux_Archive) (ALA)

Both official and un-official community based Kernels are supported.

# Official Kernels

- linux
- linux-lts
- linux-zen
- linux-hardened
- linux-rt
- linux-rt-lts

Since the ALA has a lot of kernel packages any versions found older than 2 years or more are ignored.
These kernels are considerably out of date and have shown to fail to install properly with issues related to missing modules.

![Official kernels](https://github.com/arcolinux/archlinux-kernel-manager-dev/assets/121581829/2e30c26f-a06d-4ab9-91a7-14e1ced99389)

## What happens if a kernel installation fails

The application will show a message that it has encountered an issue, and the log inside the progress window, should have the information required to understand why.
In the event of a failure, the application will try to reinstall the kernel using the version previously installed.

# Community based kernels

As long as the necessary Pacman repositories are configured these are supported.

- linux-xanmod
- linux-xanmod-lts
- linux-cachyos
- linux-lqx
- linux-clear
- linux-amd
- linux-nitrous

Most of these are sourced from the [Chaotic AUR](https://aur.chaotic.cx)

See updating the [configuration file](#Adding-new-community-based-kernels) for adding new kernels.

![Community kernels](https://github.com/arcolinux/archlinux-kernel-manager-dev/assets/121581829/8e28de8d-35eb-45b2-b799-cd691c092852)

# Installed kernels

![Installed kernels](https://github.com/arcolinux/archlinux-kernel-manager-dev/assets/121581829/75e98bd6-dd46-4c91-807c-a042cb3a3f04)

# Progress window

![Progress window](https://github.com/DeltaCopy/archlinux-kernel-manager/assets/121581829/2b7e97db-06f6-4152-bf13-b81fbc42b63c)

# Bootloader

Only Grub and systemd-boot bootloaders are supported.

After a successful install/removal of a kernel the relevant bootloader entries are updated.
By default, the application will use `bootctl` to distinguish which bootloader (Grub/systemd-boot) is currently being used.

## Grub

`grub-mkconfig` is run to update the grub.cfg file.

## systemd-boot

`bootctl --no-variables ---graceful update` is run to update systemd-boot entries

# Advanced settings

## Bootloader settings

The bootloader settings can be overridden using the Advanced settings window.
Or you can manually update the configuration file (see the custom bootloader example).

![Advanced settings](https://github.com/arcolinux/archlinux-kernel-manager-dev/assets/121581829/0a5cd26d-7991-4cea-ab43-26c36e57b135)

## Latest kernel versions

Based on the latest information taken from the configured pacman mirrors.

![Kernel versions](https://github.com/arcolinux/archlinux-kernel-manager-dev/assets/121581829/a4dccbf9-969a-4ef0-bd8c-b212f31ea2cb)

# Default configuration file

This file can be found inside `$HOME/.config/archlinux-kernel-manager`

```toml

title = "ArchLinux Kernel Manager Settings"

[kernels]

# Kernels which are sourced from the ALA (Arch Linux Archive) https://archive.archlinux.org
official = [
    { name = "linux", description = "The Linux kernel and modules (Stable)", headers = "linux-headers" },
    { name = "linux-lts", description = "The LTS Linux kernel and modules (Longterm)", headers = "linux-lts-headers" },
    { name = "linux-zen", description = "The Linux ZEN kernel and modules (Zen)", headers = "linux-zen-headers" },
    { name = "linux-hardened", description = "The Security-Hardened Linux kernel and modules (Hardened)", headers = "linux-hardened-headers" },
    { name = "linux-rt", description = "The Linux RT kernel and modules (Realtime)", headers = "linux-rt-headers" },
    { name = "linux-rt-lts", description = "The Linux RT LTS kernel and modules (Realtime Longterm)", headers = "linux-rt-lts-headers" },
]

# Kernels which are sourced from unofficial repositories, these won't work if you haven't updated your pacman configuration
# https://wiki.archlinux.org/title/Unofficial_user_repositories
community = [
    { name = "linux-xanmod", description = "The Linux kernel and modules with Xanmod patches", headers = "linux-xanmod-headers", repository = "chaotic-aur" },
    { name = "linux-xanmod-lts", description = "The Linux kernel and modules with Xanmod patches", headers = "linux-xanmod-lts-headers", repository = "chaotic-aur" },
    { name = "linux-amd", description = "Linux kernel aimed at the ZNVER4/MZEN4 AMD Ryzen CPU based hardware", headers = "linux-amd-headers", repository = "chaotic-aur" },
    { name = "linux-cachyos", description = "The Linux EEVDF-BORE scheduler Kernel by CachyOS with other patches and improvements kernel and modules", headers = "linux-cachyos-headers", repository = "chaotic-aur" },
    { name = "linux-ck", description = "The Linux kernel and modules with ck's hrtimer patches", headers = "linux-ck-headers", repository = "repo-ck" },
    { name = "linux-clear", description = "The Clear Linux kernel and modules", headers = "linux-clear-headers", repository = "chaotic-aur" },
    { name = "linux-lts-tkg-bmq", description = "The Linux-tkg kernel and modules", headers = "linux-lts-tkg-bmq-headers", repository = "chaotic-aur" },
    { name = "linux-tkg-pds", description = "The Linux-tkg kernel and modules", headers = "linux-tkg-pds-headers", repository = "chaotic-aur" },
    { name = "linux-lqx", description = "The Linux Liquorix kernel and modules", headers = "linux-lqx-headers", repository = "chaotic-aur" },
    { name = "linux-nitrous", description = "Modified Linux kernel optimized for Skylake and newer, compiled using clang", headers = "linux-nitrous-headers", repository = "chaotic-aur" },
]

# custom bootloader example
#[bootloader]
#name = "grub"
#grub_config = "/boot/grub/grub.cfg"

```
## Adding new community based kernels

Further Kernels can be added using the same format.

When adding new community based un-official kernels, the repository name should match the one defined inside the pacman `/etc/pacman.conf` file under `[repo-name]`.
Further details on un-official kernels can be found on https://wiki.archlinux.org/title/Kernel#Unofficial_kernels

# Cache

Kernel data retrieved from the ALA is stored inside a toml based file inside `$HOME/.cache/archlinux-kernel-manager/kernels.toml`

This cached file is updated automatically every 5 days to ensure the application is kept up to date with the latest kernels.
Using the Update switch inside Advanced Settings, will force the application to update the cache.

This cache file may take a little while to generate since archived Arch kernel package data is being retrieved from the ALA.

# Logs

Logs can be found inside `/var/log/archlinux-kernel-manager`

# Required Python modules

- python-tomlkit

- python-gobject

- python-requests

- python-distro

- python-psutil

# Running the application

Run `akm` or `archlinux-kernel-manager` to launch the application.
