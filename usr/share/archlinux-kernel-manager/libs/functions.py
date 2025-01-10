import logging
import shutil
import sys
import os
import distro
from os import makedirs
import requests
import threading
import re
import time
import subprocess
import gi
import datetime
import psutil
import queue
import pathlib
import locale
import tomlkit
from tomlkit import dumps, load
from datetime import timedelta
from logging.handlers import TimedRotatingFileHandler
from threading import Thread
from queue import Queue
from ui.MessageWindow import MessageWindow
from libs.Kernel import Kernel, InstalledKernel, CommunityKernel

gi.require_version("Gtk", "4.0")
from gi.repository import GLib

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

latest_archlinux_package_search_url = (
    "https://archlinux.org/packages/search/json?name=${PACKAGE_NAME}"
)
archlinux_mirror_archive_url = "https://archive.archlinux.org"
headers = {
    "Content-Type": "text/plain;charset=UTF-8",
    "User-Agent": "Mozilla/5.0 (Linux x86_64) Gecko Firefox",
}


cache_days = 5
fetched_kernels_dict = {}
cached_kernels_list = []
community_kernels_list = []
supported_kernels_dict = {}
community_kernels_dict = {}
pacman_repos_list = []
process_timeout = 200
sudo_username = os.getlogin()
home = "/home/" + str(sudo_username)

# pacman log file
pacman_logfile = "/var/log/pacman.log"

# pacman lock file
pacman_lockfile = "/var/lib/pacman/db.lck"

# pacman conf file
pacman_conf_file = "/etc/pacman.conf"

# pacman cach dir
pacman_cache = "/var/cache/pacman/pkg"

# thread names
thread_get_kernels = "thread_get_kernels"
thread_get_community_kernels = "thread_get_community_kernels"
thread_install_community_kernel = "thread_install_community_kernel"
thread_install_archive_kernel = "thread_install_archive_kernel"
thread_check_kernel_state = "thread_check_kernel_state"
thread_uninstall_kernel = "thread_uninstall_kernel"
thread_monitor_messages = "thread_monitor_messages"
thread_refresh_cache = "thread_refresh_cache"
thread_refresh_ui = "thread_refresh_ui"

cache_dir = "%s/.cache/archlinux-kernel-manager" % home
cache_file = "%s/kernels.toml" % cache_dir
cache_update = "%s/update" % cache_dir

log_dir = "/var/log/archlinux-kernel-manager"
event_log_file = "%s/event.log" % log_dir


config_file_default = "%s/defaults/config.toml" % base_dir
config_dir = "%s/.config/archlinux-kernel-manager" % home
config_file = "%s/.config/archlinux-kernel-manager/config.toml" % home
config_file_backup = "%s/.config/archlinux-kernel-manager/config.toml_backup" % home


logger = logging.getLogger("logger")

# create console handler and set level to debug
ch = logging.StreamHandler()

# create formatter
formatter = logging.Formatter(
    "%(asctime)s:%(levelname)s > %(message)s", "%Y-%m-%d %H:%M:%S"
)
# add formatter to ch
ch.setFormatter(formatter)


# add ch to logger
logger.addHandler(ch)

# set locale
locale.setlocale(locale.LC_ALL, "C.utf8")
locale_env = os.environ
locale_env["LC_ALL"] = "C.utf8"


# =====================================================
#              CHECK FOR KERNEL UPDATES
# =====================================================
def get_latest_kernel_updates(self):
    logger.info("Getting latest kernel versions")
    try:
        last_update_check = None
        fetch_update = False
        cache_timestamp = None

        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                # data = tomlkit.load(f)

                data = f.readlines()[2]

                if len(data) == 0:
                    logger.error(
                        "%s is empty, delete it and open the app again" % cache_file
                    )

                if len(data) > 0 and "timestamp" in data.strip():
                    # cache_timestamp = data["timestamp"]
                    cache_timestamp = (
                        data.split("timestamp = ")[1].replace('"', "").strip()
                    )

            if not os.path.exists(cache_update):
                last_update_check = datetime.datetime.now().strftime("%Y-%m-%d")
                with open(cache_update, mode="w", encoding="utf-8") as f:
                    f.write("%s\n" % last_update_check)

                permissions(cache_dir)

            else:
                with open(cache_update, mode="r", encoding="utf-8") as f:
                    last_update_check = f.read().strip()

                with open(cache_update, mode="w", encoding="utf-8") as f:
                    f.write("%s\n" % datetime.datetime.now().strftime("%Y-%m-%d"))

                permissions(cache_dir)

            logger.info(
                "Linux package update last fetched on %s"
                % datetime.datetime.strptime(last_update_check, "%Y-%m-%d").date()
            )

            if (
                datetime.datetime.strptime(last_update_check, "%Y-%m-%d").date()
                < datetime.datetime.now().date()
            ):

                logger.info("Fetching Linux package update data")

                response = requests.get(
                    latest_archlinux_package_search_url.replace(
                        "${PACKAGE_NAME}", "linux"
                    ),
                    headers=headers,
                    allow_redirects=True,
                    timeout=60,
                    stream=True,
                )

                if response.status_code == 200:
                    if response.json() is not None:
                        if len(response.json()["results"]) > 0:
                            if response.json()["results"][0]["last_update"]:
                                logger.info(
                                    "Linux kernel package last update = %s"
                                    % datetime.datetime.strptime(
                                        response.json()["results"][0]["last_update"],
                                        "%Y-%m-%dT%H:%M:%S.%f%z",
                                    ).date()
                                )
                                if (
                                    datetime.datetime.strptime(
                                        response.json()["results"][0]["last_update"],
                                        "%Y-%m-%dT%H:%M:%S.%f%z",
                                    ).date()
                                ) >= (
                                    datetime.datetime.strptime(
                                        cache_timestamp, "%Y-%m-%d %H-%M-%S"
                                    ).date()
                                ):
                                    logger.info("Linux kernel package updated")

                                    refresh_cache(self)

                                    return True

                                else:
                                    logger.info("Linux kernel package not updated")

                                    return False
                else:
                    logger.error("Failed to get valid response to check kernel update")
                    logger.error(response.text)

                    return False
            else:
                logger.info("Kernel update check not required")

                return False

        else:
            logger.info("No cache file present, refresh required")
            if not os.path.exists(cache_update):
                last_update_check = datetime.datetime.now().strftime("%Y-%m-%d")
                with open(cache_update, mode="w", encoding="utf-8") as f:
                    f.write("%s\n" % last_update_check)

                permissions(cache_dir)

            return False

    except Exception as e:
        logger.error("Exception in get_latest_kernel_updates(): %s" % e)
        return True


# =====================================================
#              CACHE LAST MODIFIED
# =====================================================
def get_cache_last_modified():
    try:
        if os.path.exists(cache_file):
            timestamp = datetime.datetime.fromtimestamp(
                pathlib.Path(cache_file).stat().st_mtime, tz=datetime.timezone.utc
            )

            return "%s %s" % (
                timestamp.date(),
                str(timestamp.time()).split(".")[0],
            )

        else:
            return "Cache file does not exist"
    except Exception as e:
        logger.error("Exception in get_cache_last_modified(): %s" % e)


# =====================================================
#               LOG DIRECTORY
# =====================================================

try:
    if not os.path.exists(log_dir):
        makedirs(log_dir)
except Exception as e:
    logger.error("Exception in make log directory(): %s" % e)


# rotate the events log every Friday
tfh = TimedRotatingFileHandler(event_log_file, encoding="utf-8", delay=False, when="W4")
tfh.setFormatter(formatter)
logger.addHandler(tfh)

# =====================================================
#               PERMISSIONS
# =====================================================

# Change permissions
def permissions(dst):
    try:
        groups = subprocess.run(
            ["sh", "-c", "id " + sudo_username],
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=locale_env,
        )
        for x in groups.stdout.decode().split(" "):
            if "gid" in x:
                g = x.split("(")[1]
                group = g.replace(")", "").strip()
        subprocess.call(
            ["chown", "-R", sudo_username + ":" + group, dst],
            shell=False,
            env=locale_env,
        )

    except Exception as e:
        logger.error("Exception in permissions(): %s" % e)


def setup_config(self):
    try:
        if not os.path.exists(config_dir):
            makedirs(config_dir)

        if not os.path.exists(config_file):
            shutil.copy(config_file_default, config_dir)
            permissions(config_dir)

        return read_config(self)

    except Exception as e:
        logger.error("Exception in setup_config(): %s" % e)

def overwrite_setup_config(self):
    try:
        if not os.path.exists(config_dir):
            makedirs(config_dir)
            permissions(config_dir)

        if os.path.exists(config_file):
            shutil.copy(config_file_default, config_dir)
            permissions(config_dir)

        return read_config(self)

    except Exception as e:
        logger.error("Exception in setup_config(): %s" % e)

def backup_config(self):
    try:
        if not os.path.exists(config_dir):
            makedirs(config_dir)
            permissions(config_dir)

        if not os.path.exists(config_file_backup):
            shutil.copy(config_file, config_file_backup)
            permissions(config_dir)

        return read_config(self)

    except Exception as e:
        logger.error("Exception in setup_config(): %s" % e)

def update_config(config_data, bootloader):
    try:
        logger.info("Updating config data")

        with open(config_file, "w") as f:
            tomlkit.dump(config_data, f)

        return True

    except Exception as e:
        logger.error("Exception in update_config(): %s" % e)
        return False


def read_config(self):
    try:
        logger.info("Reading in config file %s" % config_file)
        config_data = None
        with open(config_file, "rb") as f:
            config_data = tomlkit.load(f)

            if (
                config_data.get("kernels")
                and "official" in config_data["kernels"] is not None
            ):
                for official_kernel in config_data["kernels"]["official"]:
                    supported_kernels_dict[official_kernel["name"]] = (
                        official_kernel["description"],
                        official_kernel["headers"],
                    )

            if (
                config_data.get("kernels")
                and "community" in config_data["kernels"] is not None
            ):
                for community_kernel in config_data["kernels"]["community"]:
                    community_kernels_dict[community_kernel["name"]] = (
                        community_kernel["description"],
                        community_kernel["headers"],
                        community_kernel["repository"],
                    )

            if (
                config_data.get("logging") is not None
                and "loglevel" in config_data["logging"] is not None
            ):

                loglevel = config_data["logging"]["loglevel"].lower()
                logger.info("Setting loglevel to %s" % loglevel)
                if loglevel == "debug":
                    logger.setLevel(logging.DEBUG)
                elif loglevel == "info":
                    logger.setLevel(logging.INFO)
                else:
                    logger.warning("Invalid logging level set, use info / debug")
                    logger.setLevel(logging.INFO)
            else:
                logger.setLevel(logging.INFO)

        return config_data
    except Exception as e:
        logger.error("Exception in read_config(): %s" % e)
        sys.exit(1)


def create_cache_dir():
    try:
        if not os.path.exists(cache_dir):
            makedirs(cache_dir)

        logger.info("Cache directory = %s" % cache_dir)

        permissions(cache_dir)
    except Exception as e:
        logger.error("Exception in create_cache_dir(): %s" % e)


def create_log_dir():
    try:
        if not os.path.exists(log_dir):
            makedirs(log_dir)

        logger.info("Log directory = %s" % log_dir)
    except Exception as e:
        logger.error("Exception in create_log_dir(): %s" % e)


def write_cache():
    try:
        if len(fetched_kernels_dict) > 0:
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write('title = "Arch Linux Kernels"\n\n')
                f.write(
                    'timestamp = "%s"\n'
                    % datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
                )
                f.write('source = "%s"\n\n' % archlinux_mirror_archive_url)

                for kernel in fetched_kernels_dict.values():
                    f.write("[[kernel]]\n")
                    f.write(
                        'name = "%s"\nheaders = "%s"\nversion = "%s"\nsize = "%s"\nfile_format = "%s"\nlast_modified = "%s"\n\n'
                        % (
                            kernel.name,
                            kernel.headers,
                            kernel.version,
                            kernel.size,
                            kernel.file_format,
                            kernel.last_modified,
                        )
                    )
            permissions(cache_file)
    except Exception as e:
        logger.error("Exception in write_cache(): %s" % e)


# install from the ALA
def install_archive_kernel(self):
    try:
        # package cache
        logger.debug("Cleaning pacman cache, removing official packages")
        if os.path.exists(pacman_cache):
            for root, dirs, files in os.walk(pacman_cache):
                for name in files:
                    for official_kernel in supported_kernels_dict.keys():
                        if name.startswith(official_kernel):
                            if os.path.exists(os.path.join(root, name)):
                                os.remove(os.path.join(root, name))

        install_cmd_str = [
            "pacman",
            "-U",
            self.official_kernels[0],
            self.official_kernels[1],
            "--noconfirm",
            "--needed",
        ]

        wait_for_pacman_process()

        if logger.getEffectiveLevel() == 10:
            logger.debug("Running %s" % install_cmd_str)

        event = "%s [INFO]: Running %s\n" % (
            datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
            " ".join(install_cmd_str),
        )

        error = False

        self.messages_queue.put(event)

        with subprocess.Popen(
            install_cmd_str,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            env=locale_env,
        ) as process:
            while True:
                if process.poll() is not None:
                    break
                for line in process.stdout:
                    if logger.getEffectiveLevel() == 10:
                        print(line.strip())
                    self.messages_queue.put(line)
                    if "no space left on device" in line.lower().strip():
                        self.restore_kernel = None
                        error = True
                        break
                    if "initcpio" in line.lower().strip():
                        if "image generation successful" in line.lower().strip():
                            error = False
                            break
                    if (
                        "installation finished. no error reported"
                        in line.lower().strip()
                    ):
                        error = False
                        break
                    if (
                        "error" in line.lower().strip()
                        or "errors" in line.lower().strip()
                    ):
                        error = True
                        break

                # time.sleep(0.1)

        if error is True:

            self.errors_found = True

            error = True

            GLib.idle_add(
                show_mw,
                self,
                "System changes",
                f"Kernel {self.action} failed\n"
                f"<b>There have been errors, please review the logs</b>",
                priority=GLib.PRIORITY_DEFAULT,
            )

        # query to check if kernel installed

        if check_kernel_installed(self.kernel.name + "-headers") and error is False:
            self.kernel_state_queue.put((0, "install"))
        else:
            self.kernel_state_queue.put((1, "install"))

            self.errors_found = True
            self.messages_queue.put(event)

        if check_kernel_installed(self.kernel.name) and error is False:
            self.kernel_state_queue.put((0, "install"))
        else:
            self.kernel_state_queue.put((1, "install"))
            self.errors_found = True

        # signal to say end reached
        self.kernel_state_queue.put(None)

    except Exception as e:
        logger.error("Exception in install_archive_kernel(): %s" % e)

        # GLib.idle_add(
        #     show_mw,
        #     self,
        #     "System changes",
        #     f"<b>Kernel {self.action} failed</b>\n"
        #     f"There have been errors, please review the logs\n",
        #     "images/48x48/akm-warning.png",
        #     priority=GLib.PRIORITY_DEFAULT,
        # )
    finally:
        if os.path.exists(self.lockfile):
            os.unlink(self.lockfile)


def refresh_cache(self):

    cached_kernels_list.clear()
    if os.path.exists(cache_file):
        os.remove(cache_file)
    config_file_backup()

    get_official_kernels(self)
    write_cache()


def read_cache(self):
    try:
        self.timestamp = None

        with open(cache_file, "rb") as f:
            data = tomlkit.load(f)

            if len(data) == 0:
                logger.error(
                    "%s is empty, delete it and open the app again" % cache_file
                )

            name = None
            headers = None
            version = None
            size = None
            last_modified = None
            file_format = None

            if len(data) > 0:
                self.timestamp = data["timestamp"]

                self.cache_timestamp = data["timestamp"]

                # check date of cache, if it's older than 5 days - refresh

                if self.timestamp:
                    self.timestamp = datetime.datetime.strptime(
                        self.timestamp, "%Y-%m-%d %H-%M-%S"
                    )

                    delta = datetime.datetime.now() - self.timestamp

                    if delta.days >= cache_days:
                        logger.info("Cache is older than 5 days, refreshing ..")
                        refresh_cache(self)
                    else:

                        if delta.days > 0:
                            logger.debug("Cache is %s days old" % delta.days)
                        else:
                            logger.debug("Cache is newer than 5 days")

                        kernels = data["kernel"]

                        if len(kernels) > 1:
                            for k in kernels:

                                # any kernels older than 2 years
                                # (currently linux v4.x or earlier) are deemed eol so ignore them

                                if (
                                    datetime.datetime.now().year
                                    - datetime.datetime.strptime(
                                        k["last_modified"], "%d-%b-%Y %H:%M"
                                    ).year
                                    <= 2
                                ):
                                    cached_kernels_list.append(
                                        Kernel(
                                            k["name"],
                                            k["headers"],
                                            k["version"],
                                            k["size"],
                                            k["last_modified"],
                                            k["file_format"],
                                        )
                                    )

                            name = None
                            headers = None
                            version = None
                            size = None
                            last_modified = None
                            file_format = None

                            if len(cached_kernels_list) > 0:
                                sorted(cached_kernels_list)
                                logger.info("Kernels cache data processed")
                        else:
                            logger.error(
                                "Cached file is invalid, remove it and try again"
                            )

            else:
                logger.error("Failed to read cache file")

    except Exception as e:
        logger.error("Exception in read_cache(): %s" % e)


# get latest versions of the official kernels
def get_latest_versions(self):
    logger.info("Getting latest kernel information")
    kernel_versions = {}
    try:

        for kernel in supported_kernels_dict:
            check_cmd_str = ["pacman", "-Si", kernel]

            with subprocess.Popen(
                check_cmd_str,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                universal_newlines=True,
                env=locale_env,
            ) as process:
                while True:
                    if process.poll() is not None:
                        break
                    for line in process.stdout:
                        if line.strip().replace(" ", "").startswith("Version:"):
                            kernel_versions[kernel] = (
                                line.strip().replace(" ", "").split("Version:")[1]
                            )
                            break

        self.kernel_versions_queue.put(kernel_versions)

    except Exception as e:
        logger.error("Exception in get_latest_versions(): %s" % e)


def parse_archive_html(response, linux_kernel):
    for line in response.splitlines():
        if "<a href=" in line.strip():
            files = re.findall('<a href="([^"]*)', line.strip())
            if len(files) > 0:
                if "-x86_64" in files[0]:
                    version = files[0].split("-x86_64")[0]
                    file_format = files[0].split("-x86_64")[1]

                    url = (
                        "/packages/l/%s" % archlinux_mirror_archive_url
                        + "/%s" % linux_kernel
                        + "/%s" % files[0]
                    )

                    if ".sig" not in file_format:
                        if len(line.rstrip().split("    ")) > 0:
                            size = line.strip().split("    ").pop().strip()

                        last_modified = line.strip().split("</a>").pop()
                        for x in last_modified.split("    "):
                            if len(x.strip()) > 0 and ":" in x.strip():
                                # 02-Mar-2023 21:12
                                # %d-%b-Y %H:%M
                                last_modified = x.strip()

                        headers = "%s%s" % (
                            supported_kernels_dict[linux_kernel][1],
                            version.replace(linux_kernel, ""),
                        )

                        if (
                            version is not None
                            and url is not None
                            and headers is not None
                            and file_format == ".pkg.tar.zst"
                            and datetime.datetime.now().year
                            - datetime.datetime.strptime(
                                last_modified, "%d-%b-%Y %H:%M"
                            ).year
                            <= 2  # ignore kernels <=2 years old
                        ):
                            ke = Kernel(
                                linux_kernel,
                                headers,
                                version,
                                size,
                                last_modified,
                                file_format,
                            )

                            fetched_kernels_dict[version] = ke

                version = None
                file_format = None
                url = None
                size = None
                last_modified = None


def wait_for_response(response_queue):
    while True:
        items = response_queue.get()

        # error break from loop
        if items is None:
            break

        # we have all kernel data break
        if len(supported_kernels_dict) == len(items):
            break


def get_response(session, linux_kernel, response_queue, response_content):
    response = session.get(
        "%s/packages/l/%s" % (archlinux_mirror_archive_url, linux_kernel),
        headers=headers,
        allow_redirects=True,
        timeout=60,
        stream=True,
    )

    if response.status_code == 200:
        if logger.getEffectiveLevel() == 10:
            logger.debug(
                "Response code for %s/packages/l/%s = 200 (OK)"
                % (archlinux_mirror_archive_url, linux_kernel)
            )
        if response.text is not None:
            response_content[linux_kernel] = response.text
            response_queue.put(response_content)
    else:
        logger.error("Something went wrong with the request")
        logger.error(response.text)
        response_queue.put(None)


def get_official_kernels(self):
    try:
        if not os.path.exists(cache_file) or self.refresh_cache is True:
            session = requests.session()
            response_queue = Queue()
            response_content = {}
            # loop through linux kernels
            for linux_kernel in supported_kernels_dict:
                logger.info(
                    "Fetching data from %s/packages/l/%s"
                    % (archlinux_mirror_archive_url, linux_kernel)
                )
                Thread(
                    target=get_response,
                    args=(
                        session,
                        linux_kernel,
                        response_queue,
                        response_content,
                    ),
                    daemon=True,
                ).start()

            wait_for_response(response_queue)
            session.close()

            for kernel in response_content:
                parse_archive_html(response_content[kernel], kernel)

            if len(fetched_kernels_dict) > 0:
                write_cache()
                read_cache(self)

                # self.queue_kernels = Queue()

                self.queue_kernels.put(cached_kernels_list)

            else:
                logger.error("Failed to retrieve Linux Kernel list")
                self.queue_kernels.put(None)
        else:
            logger.debug("Reading cache file = %s" % cache_file)
            # read cache file
            read_cache(self)
            self.queue_kernels.put(cached_kernels_list)

    except Exception as e:
        logger.error("Exception in get_official_kernels(): %s" % e)


def wait_for_cache(self):
    while True:
        if not os.path.exists(cache_file):
            time.sleep(0.2)
        else:
            read_cache(self)
            break


# =====================================================
#               THREADING
# =====================================================


# check if the named thread is running
def is_thread_alive(thread_name):
    for thread in threading.enumerate():
        if thread.name == thread_name and thread.is_alive():
            return True

    return False


# print all threads
def print_all_threads():
    for thread in threading.enumerate():
        if logger.getEffectiveLevel() == 10:
            logger.debug(
                "Thread = %s and state is %s" % (thread.name, thread.is_alive())
            )


# =====================================================
#               UPDATE TEXTVIEW IN PROGRESS WINDOW
# =====================================================


def update_progress_textview(self, line):
    try:
        if len(line) > 0:
            self.textbuffer.insert_markup(
                self.textbuffer.get_end_iter(), " %s" % line, len(" %s" % line)
            )
    except Exception as e:
        logger.error("Exception in update_progress_textview(): %s" % e)
    finally:
        self.messages_queue.task_done()
        text_mark_end = self.textbuffer.create_mark(
            "end", self.textbuffer.get_end_iter(), False
        )
        # scroll to the end of the textview
        self.textview.scroll_mark_onscreen(text_mark_end)


# =====================================================
#               MESSAGES QUEUE: MONITOR THEN UPDATE TEXTVIEW
# =====================================================


def monitor_messages_queue(self):
    try:
        while True:
            message = self.messages_queue.get()

            GLib.idle_add(
                update_progress_textview,
                self,
                message,
                priority=GLib.PRIORITY_DEFAULT,
            )
    except Exception as e:
        logger.error("Exception in monitor_messages_queue(): %s" % e)


# =====================================================
#               CHECK IF KERNEL INSTALLED
# =====================================================


def check_kernel_installed(name):
    try:
        logger.info("Checking kernel package %s is installed" % name)
        check_cmd_str = ["pacman", "-Q", name]
        if logger.getEffectiveLevel() == 10:
            logger.debug("Running cmd = %s" % check_cmd_str)

        process_kernel_query = subprocess.Popen(
            check_cmd_str,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=locale_env,
        )

        out, err = process_kernel_query.communicate(timeout=process_timeout)

        if process_kernel_query.returncode == 0:
            for line in out.decode("utf-8").splitlines():
                if line.split(" ")[0] == name:

                    logger.info("Kernel installed")

                    return True

        else:
            logger.info("Kernel is not installed")
            return False

        return False
    except Exception as e:
        logger.error("Exception in check_kernel_installed(): %s" % e)


def wait_for_pacman_process():
    logger.info("Waiting for pacman process")
    timeout = 120
    i = 0
    while check_pacman_lockfile():
        time.sleep(0.1)
        if logger.getEffectiveLevel() == 10:
            logger.debug("Pacman lockfile found .. waiting")
        i += 1
        if i == timeout:
            logger.info("Timeout reached")
            break


# =====================================================
#               REMOVE KERNEL
# =====================================================


def uninstall(self):
    try:
        kernel_installed = check_kernel_installed(self.kernel.name)
        logger.info("Kernel installed = %s" % kernel_installed)
        kernel_headers_installed = check_kernel_installed(self.kernel.name + "-headers")
        logger.info("Kernel headers installed = %s" % kernel_headers_installed)

        uninstall_cmd_str = None
        event_log = []
        # self.errors_found = False

        if kernel_installed is True and kernel_headers_installed is True:
            uninstall_cmd_str = [
                "pacman",
                "-Rs",
                self.kernel.name,
                self.kernel.name + "-headers",
                "--noconfirm",
            ]

        if kernel_installed is True and kernel_headers_installed is False:
            uninstall_cmd_str = ["pacman", "-Rs", self.kernel.name, "--noconfirm"]

        if kernel_installed == 0:
            logger.info("Kernel is not installed, uninstall not required")
            self.kernel_state_queue.put((0, "uninstall"))
            return

        if logger.getEffectiveLevel() == 10:
            logger.debug("Uninstall cmd = %s" % uninstall_cmd_str)

        # check if kernel, and kernel header is actually installed
        if uninstall_cmd_str is not None:

            wait_for_pacman_process()

            event = "%s [INFO]: Running %s\n" % (
                datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
                " ".join(uninstall_cmd_str),
            )
            self.messages_queue.put(event)

            with subprocess.Popen(
                uninstall_cmd_str,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                env=locale_env,
                bufsize=1,
            ) as process:
                while True:
                    if process.poll() is not None:
                        break
                    for line in process.stdout:
                        if logger.getEffectiveLevel() == 10:
                            print(line.strip())
                        # print(line.strip())
                        self.messages_queue.put(line)
                        # event_log.append(line.lower().strip())
                        if (
                            "error" in line.lower().strip()
                            or "errors" in line.lower().strip()
                        ):
                            self.errors_found = True
                            break

                        # self.pacmanlog_queue.put(line)
                        # process_stdout_lst.append(line)

                    # time.sleep(0.1)

            # query to check if kernel installed
            if "headers" in uninstall_cmd_str:
                if check_kernel_installed(self.kernel.name + "-headers") is True:
                    self.kernel_state_queue.put((1, "uninstall"))

                    event = (
                        "%s [ERROR]: Uninstall failed\n"
                        % datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
                    )

                    self.messages_queue.put(event)

                else:
                    self.kernel_state_queue.put((0, "uninstall"))

                    event = (
                        "%s [INFO]: Uninstall completed\n"
                        % datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
                    )

                    self.messages_queue.put(event)

            else:
                if check_kernel_installed(self.kernel.name) is True:
                    self.kernel_state_queue.put((1, "uninstall"))

                    event = (
                        "%s [ERROR]: Uninstall failed\n"
                        % datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
                    )

                    self.messages_queue.put(event)

                else:
                    self.kernel_state_queue.put((0, "uninstall"))

                    event = (
                        "%s [INFO]: Uninstall completed\n"
                        % datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
                    )

                    self.messages_queue.put(event)

            # signal to say end reached
            self.kernel_state_queue.put(None)

    except Exception as e:
        logger.error("Exception in uninstall(): %s" % e)


# =====================================================
#               LIST COMMUNITY KERNELS
# =====================================================


def get_community_kernels(self):
    try:
        logger.info("Fetching package information for community based kernels")
        for community_kernel in sorted(community_kernels_dict):
            if community_kernels_dict[community_kernel][2] in pacman_repos_list:
                pacman_repo = community_kernels_dict[community_kernel][2]
                headers = community_kernels_dict[community_kernel][1]
                name = community_kernel

                # fetch kernel info
                query_cmd_str = [
                    "pacman",
                    "-Si",
                    "%s/%s" % (pacman_repo, name),
                ]

                # logger.debug("Running %s" % query_cmd_str)
                process_kernel_query = subprocess.Popen(
                    query_cmd_str,
                    shell=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=locale_env,
                )
                out, err = process_kernel_query.communicate(timeout=process_timeout)
                version = None
                install_size = None
                build_date = None
                if process_kernel_query.returncode == 0:
                    for line in out.decode("utf-8").splitlines():
                        if line.startswith("Version         :"):
                            version = line.split("Version         :")[1].strip()
                        if line.startswith("Installed Size  :"):
                            install_size = line.split("Installed Size  :")[1].strip()
                            if logger.getEffectiveLevel() == 10:
                                logger.debug(
                                    "%s installed kernel size = %s"
                                    % (name, install_size)
                                )
                            if "MiB" in install_size:
                                if install_size.find(",") >= 0:
                                    if logger.getEffectiveLevel() == 10:
                                        logger.debug("Comma found inside install size")
                                    install_size = round(
                                        float(
                                            install_size.replace(",", ".")
                                            .strip()
                                            .replace("MiB", "")
                                            .strip()
                                        )
                                        * 1.048576,
                                        1,
                                    )
                                else:
                                    install_size = round(
                                        float(install_size.replace("MiB", "").strip())
                                        * 1.048576,
                                        1,
                                    )

                        if line.startswith("Build Date      :"):
                            build_date = line.split("Build Date      :")[1].strip()

                            if name and version and install_size and build_date:
                                community_kernels_list.append(
                                    CommunityKernel(
                                        name,
                                        headers,
                                        pacman_repo,
                                        version,
                                        build_date,
                                        install_size,
                                    )
                                )

        self.queue_community_kernels.put(community_kernels_list)

    except Exception as e:
        logger.error("Exception in get_community_kernels(): %s" % e)


# =====================================================
#               INSTALL COMMUNITY KERNELS
# =====================================================
def install_community_kernel(self):
    try:
        if logger.getEffectiveLevel() == 10:
            logger.debug("Cleaning pacman cache, removing community packages")
        if os.path.exists(pacman_cache):
            for root, dirs, files in os.walk(pacman_cache):
                for name in files:
                    for comm_kernel in community_kernels_dict.keys():
                        if name.startswith(comm_kernel):
                            if os.path.exists(os.path.join(root, name)):
                                os.remove(os.path.join(root, name))

        error = False
        install_cmd_str = [
            "pacman",
            "-S",
            "%s/%s" % (self.kernel.repository, self.kernel.name),
            "%s/%s" % (self.kernel.repository, "%s-headers" % self.kernel.name),
            "--noconfirm",
            "--needed",
        ]
        if logger.getEffectiveLevel() == 10:
            logger.debug("Running %s" % install_cmd_str)

        event = "%s [INFO]: Running %s\n" % (
            datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
            " ".join(install_cmd_str),
        )

        error = False

        self.messages_queue.put(event)

        with subprocess.Popen(
            install_cmd_str,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            env=locale_env,
        ) as process:
            while True:
                if process.poll() is not None:
                    break
                for line in process.stdout:
                    if logger.getEffectiveLevel() == 10:
                        print(line.strip())

                    self.messages_queue.put(line)

                    if "no space left on device" in line.lower().strip():
                        error = True
                        break
                    if "initcpio" in line.lower().strip():
                        if "image generation successful" in line.lower().strip():
                            error = False
                            break
                    if (
                        "installation finished. no error reported"
                        in line.lower().strip()
                    ):
                        error = False
                        break
                    if (
                        "error" in line.lower().strip()
                        or "errors" in line.lower().strip()
                    ):
                        error = True
                        break
                time.sleep(0.1)

        if error is True:

            self.errors_found = True

            error = True

            GLib.idle_add(
                show_mw,
                self,
                "System changes",
                f"Kernel {self.action} failed\n"
                f"<b>There have been errors, please review the logs</b>\n",
                priority=GLib.PRIORITY_DEFAULT,
            )

        if check_kernel_installed(self.kernel.name) and error is False:
            self.kernel_state_queue.put((0, "install"))

            event = "%s [INFO]: Installation of %s completed\n" % (
                datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
                self.kernel.name,
            )

            self.messages_queue.put(event)

        else:
            self.kernel_state_queue.put((1, "install"))

            event = "%s [ERROR]: Installation of %s failed\n" % (
                datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
                self.kernel.name,
            )

            self.errors_found = True
            self.messages_queue.put(event)

        # signal to say end reached
        self.kernel_state_queue.put(None)
    except Exception as e:
        logger.error("Exception in install_community_kernel(): %s " % e)
    finally:
        if os.path.exists(self.lockfile):
            os.unlink(self.lockfile)


# =====================================================
#               CHECK PACMAN LOCK FILE EXISTS
# =====================================================


# check pacman lockfile
def check_pacman_lockfile():
    return os.path.exists(pacman_lockfile)


# ======================================================================
#                   GET PACMAN REPOS
# ======================================================================


def get_pacman_repos():
    if os.path.exists(pacman_conf_file):
        list_repos_cmd_str = ["pacman-conf", "-l"]
        with subprocess.Popen(
            list_repos_cmd_str,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
            env=locale_env,
        ) as process:
            while True:
                if process.poll() is not None:
                    break
                for line in process.stdout:
                    pacman_repos_list.append(line.strip())

    else:
        logger.error("Failed to locate %s, are you on an ArchLinux based system ?")


# ======================================================================
#                   GET INSTALLED KERNEL INFO
# ======================================================================


def get_installed_kernel_info(package_name):
    logger.info("Installed kernel info - %s" % package_name)
    query_str = ["pacman", "-Qi", package_name]

    try:
        process_kernel_query = subprocess.Popen(
            query_str,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=locale_env,
        )
        out, err = process_kernel_query.communicate(timeout=process_timeout)
        install_size = None
        install_date = None
        if process_kernel_query.returncode == 0:
            for line in out.decode("utf-8").splitlines():
                if line.startswith("Installed Size  :"):
                    install_size = line.split("Installed Size  :")[1].strip()
                    if logger.getEffectiveLevel() == 10:
                        logger.debug(
                            "%s installed kernel size = %s"
                            % (package_name, install_size)
                        )
                    if "MiB" in install_size:
                        if install_size.find(",") >= 0:
                            logger.debug("Comma found inside install size")
                            install_size = round(
                                float(
                                    install_size.replace(",", ".")
                                    .strip()
                                    .replace("MiB", "")
                                    .strip()
                                )
                                * 1.048576,
                                1,
                            )
                        else:
                            install_size = round(
                                float(install_size.replace("MiB", "").strip())
                                * 1.048576,
                                1,
                            )
                if line.startswith("Install Date    :"):
                    install_date = line.split("Install Date    :")[1].strip()
            return install_size, install_date
        else:
            logger.error("Failed to get installed kernel info")
    except Exception as e:
        logger.error("Exception in get_installed_kernel_info(): %s" % e)


# ======================================================================
#                   GET INSTALLED KERNELS
# ======================================================================


def get_installed_kernels():
    logger.info("Get installed kernels")
    query_str = ["pacman", "-Q"]
    installed_kernels = []

    try:
        with subprocess.Popen(
            query_str,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            env=locale_env,
        ) as process:
            while True:
                if process.poll() is not None:
                    break
                for line in process.stdout:
                    if line.lower().strip().startswith("linux"):
                        package_name = line.split(" ")[0].strip()
                        package_version = line.split(" ")[1].strip()

                        if (
                            package_name in supported_kernels_dict
                            or package_name in community_kernels_dict
                        ):
                            if logger.getEffectiveLevel() == 10:
                                logger.debug(
                                    "Installed linux package = %s" % package_name
                                )
                            install_size, install_date = get_installed_kernel_info(
                                package_name
                            )
                            installed_kernel = InstalledKernel(
                                package_name,
                                package_version,
                                install_date,
                                install_size,
                            )

                            installed_kernels.append(installed_kernel)
    except Exception as e:
        logger.error("Exception in get_installed_kernels(): %s" % e)
    finally:
        return installed_kernels


# ======================================================================
#                   GET ACTIVE KERNEL
# ======================================================================


def get_active_kernel():
    logger.info("Getting active Linux kernel")
    # cmd = ["uname", "-rs"]
    cmd = ["kernel-install"]

    try:
        process_kernel_query = subprocess.Popen(
            cmd,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=locale_env,
        )

        out, err = process_kernel_query.communicate(timeout=process_timeout)

        if process_kernel_query.returncode == 0:
            for line in out.decode("utf-8").splitlines():
                if len(line.strip()) > 0:
                    if "Kernel Version:" in line:
                        logger.info(
                            "Active kernel = %s"
                            % line.split("Kernel Version:")[1].strip()
                        )
                        return line.split("Kernel Version:")[1].strip()
        else:
            return "unknown"

    except Exception as e:
        logger.error("Exception in get_active_kernel(): %s" % e)


# =====================================================
#               PACMAN SYNC PACKAGE DB
# =====================================================
def sync_package_db():
    try:
        sync_str = ["pacman", "-Sy"]
        logger.info("Synchronizing pacman package databases")

        cmd = ["pacman", "-Sy"]

        if logger.getEffectiveLevel() == 10:
            logger.debug("Running cmd = %s" % cmd)

        process = subprocess.Popen(
            cmd,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=locale_env,
        )

        out, err = process.communicate(timeout=600)

        if logger.getEffectiveLevel() == 10:
            print(out.decode("utf-8"))

        if process.returncode == 0:
            return None
        else:
            return out.decode("utf-8")

    except Exception as e:
        logger.error("Exception in sync_package_db(): %s" % e)


def get_boot_loader():
    try:
        logger.info("Getting bootloader")
        cmd = ["bootctl", "status"]
        if logger.getEffectiveLevel() == 10:
            logger.debug("Running %s" % " ".join(cmd))

        process = subprocess.run(
            cmd,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=process_timeout,
            universal_newlines=True,
            bufsize=1,
            env=locale_env,
        )

        if process.returncode == 0:
            for line in process.stdout.splitlines():
                if line.strip().startswith("Product:"):
                    product = line.strip().split("Product:")[1].strip()
                    if "grub" in product.lower():
                        logger.info("bootctl product reports booted with grub")
                        return "grub"
                    elif "systemd-boot" in product.lower():
                        logger.info("bootctl product reports booted with systemd-boot")
                        return "systemd-boot"
                    else:
                        # "n/a" in product
                        logger.info("bootctl product reports n/a, using default grub")
                        return "grub"

                elif line.strip().startswith("Not booted with EFI"):  # noqa
                    # bios
                    logger.info(
                        "bootctl - not booted with EFI, setting bootloader to grub"
                    )
                    return "grub"
        else:
            logger.error("Failed to run %s" % " ".join(cmd))
            logger.error(process.stdout)
    except Exception as e:
        logger.error("Exception in get_boot_loader(): %s" % e)


# ======================================================================
#                  GET INSTALLED KERNEL VERSION
# ======================================================================


def get_kernel_modules_version(kernel, db):
    cmd = None
    if db == "local":
        if logger.getEffectiveLevel() == 10:
            logger.debug("Getting kernel module version from local pacman repo")
        cmd = ["pacman", "-Qli", kernel]
    if db == "package":
        if logger.getEffectiveLevel() == 10:
            logger.debug("Getting kernel module version from package cache file")
        cmd = ["pacman", "-Qlip", kernel]
    # pacman_kernel_version = None
    kernel_modules_path = None
    try:
        if logger.getEffectiveLevel() == 10:
            logger.debug("Running %s" % " ".join(cmd))

        process = subprocess.run(
            cmd,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=process_timeout,
            universal_newlines=True,
            env=locale_env,
        )

        if process.returncode == 0:
            for line in process.stdout.splitlines():
                if "usr/lib/modules/" in line:
                    if "kernel" in line.split(" ")[1]:
                        kernel_modules_path = line.split(" ")[1]
                        break

            if kernel_modules_path is not None:
                return (
                    kernel_modules_path.split("usr/lib/modules/")[1]
                    .strip()
                    .split("/kernel/")[0]
                    .strip()
                )
            else:
                return None
        else:
            return None

    except Exception as e:
        logger.error("Exception in get_kernel_modules_version(): %s" % e)


def run_process(self):
    error = False
    self.stdout_lines = []
    if logger.getEffectiveLevel() == 10:
        logger.debug("Running process = %s" % " ".join(self.cmd))

    event = "%s [INFO]: Running %s\n" % (
        datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
        " ".join(self.cmd),
    )
    self.messages_queue.put(event)
    with subprocess.Popen(
        self.cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        env=locale_env,
    ) as process:
        while True:
            if process.poll() is not None:
                break
            for line in process.stdout:
                self.messages_queue.put(line)
                self.stdout_lines.append(line.lower().strip())
                if logger.getEffectiveLevel() == 10:
                    print(line.strip())

    for log in self.stdout_lines:
        if "error" in log or "errors" in log or "failed" in log:
            self.errors_found = True
            error = True

    if error is True:
        logger.error("%s failed" % " ".join(self.cmd))

        return True
    else:
        logger.info("%s completed" % " ".join(self.cmd))

        return False

        # time.sleep(0.3)


# ======================================================================
#                  KERNEL INITRD IMAGES TO AND FROM /BOOT
# ======================================================================


def kernel_initrd(self):
    logger.info("Adding and removing kernel and initird images")
    pkg_modules_version = None

    if self.action == "install":
        if self.source == "official":

            pkg_modules_version = get_kernel_modules_version(
                "%s/%s"
                % (
                    pacman_cache,
                    "%s-x86_64%s" % (self.kernel.version, self.kernel.file_format),
                ),
                "package",
            )

        if self.source == "community":
            pkg_modules_version = get_kernel_modules_version(
                "%s/%s"
                % (
                    pacman_cache,
                    "%s-%s-x86_64.pkg.tar.zst"
                    % (self.kernel.name, self.kernel.version),
                ),
                "package",
            )

        if pkg_modules_version is None:
            logger.error("Failed to extract modules version from package")
            return 1

        logger.debug("Package modules version = %s" % pkg_modules_version)

    # cmd = ["pacman", "-Qlp", "%s/" % pacman_cache]

    if self.action == "install":
        logger.info("Adding kernel and initrd images to /boot")
        self.image = "images/48x48/akm-install.png"

        if self.local_modules_version is not None:
            for self.cmd in [
                [
                    "kernel-install",
                    "remove",
                    self.local_modules_version,
                ],
                [
                    "kernel-install",
                    "add",
                    pkg_modules_version,
                    "/lib/modules/%s/vmlinuz" % pkg_modules_version,
                ],
            ]:
                err = run_process(self)
                if err is True:
                    return 1

        else:
            self.cmd = [
                "kernel-install",
                "add",
                pkg_modules_version,
                "/lib/modules/%s/vmlinuz" % pkg_modules_version,
            ]
            err = run_process(self)
            if err is True:
                return 1

    else:
        logger.info("Removing kernel and initrd images from /boot")
        self.image = "images/48x48/akm-remove.png"
        if self.local_modules_version is not None:
            self.cmd = [
                "kernel-install",
                "remove",
                self.local_modules_version,
            ]
            err = run_process(self)
            if err is True:
                return 1


# ======================================================================
#                  CHECK PACMAN REPO
# ======================================================================
def check_pacman_repo(repo):
    logger.info("Checking %s pacman repository is configured" % repo)
    cmd = ["pacman-conf", "-r", repo]

    try:
        with subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            env=locale_env,
        ) as process:
            while True:
                if process.poll() is not None:
                    break
                # for line in process.stdout:
                #     if logger.getEffectiveLevel() == 10:
                #         print(line.strip())

            if process.returncode == 0:
                return True
            else:
                return False
    except Exception as e:
        logger.error("Exception in check_pacman_repo(): %s" % e)


# ======================================================================
#                  UPDATE BOOTLOADER ENTRIES
# ======================================================================


# grub - grub-mkconfig /boot/grub/grub.cfg
# systemd-boot - bootctl update
def update_bootloader(self):
    logger.info("Updating bootloader")
    cmds = []
    error = False
    stdout_lines = []

    try:
        logger.info("Current bootloader = %s" % self.bootloader)

        cmd = None

        if self.bootloader == "grub":

            self.label_notify_revealer.set_text(
                "Updating bootloader %s" % self.bootloader
            )
            self.reveal_notify()

            if self.bootloader_grub_cfg is not None:
                cmd = ["grub-mkconfig", "-o", self.bootloader_grub_cfg]
            else:
                logger.error("Bootloader grub config file not specified")

            event = "%s [INFO]: Running %s\n" % (
                datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
                " ".join(cmd),
            )
            self.messages_queue.put(event)

        elif self.bootloader == "systemd-boot":
            # cmd = ["bootctl", "update"]
            # graceful update systemd-boot
            # cmd = ["bootctl", "--no-variables", "--graceful", "update"]
            # event = "%s [INFO]: Running %s\n" % (
            #     datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
            #     " ".join(cmd),
            # )

            self.label_notify_revealer.set_text(
                "%s skipping bootloader update" % self.bootloader
            )
            self.reveal_notify()

            event = (
                "%s [INFO]: systemd-boot skipping bootloader update\n"
                % datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            )

            logger.info("systemd-boot skipping bootloader update")

            self.messages_queue.put(event)

            if (
                self.restore is not None
                and self.restore is False
                and self.errors_found is False
            ):
                GLib.idle_add(
                    show_mw,
                    self,
                    "System changes",
                    f"<b>Kernel {self.action} completed</b>\n"
                    f"This window can now be closed",
                    priority=GLib.PRIORITY_DEFAULT,
                )
            # elif self.errors_found is True:
            #     GLib.idle_add(
            #         show_mw,
            #         self,
            #         "System changes",
            #         f"<b>There have been errors, please review the logs</b>\n",
            #         self.image,
            #         priority=GLib.PRIORITY_DEFAULT,
            #     )
        else:
            logger.error("Bootloader is empty / not supported")

        if cmd is not None:
            self.stdout_lines = []
            if logger.getEffectiveLevel() == 10:
                logger.debug("Running %s" % " ".join(cmd))

            with subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                env=locale_env,
            ) as process:
                while True:
                    if process.poll() is not None:
                        break
                    for line in process.stdout:
                        self.stdout_lines.append(line.strip())
                        self.messages_queue.put(line)
                        if logger.getEffectiveLevel() == 10:
                            print(line.strip())
                        # print(line.strip())

                    # time.sleep(0.3)

                if process.returncode == 0:
                    self.label_notify_revealer.set_text(
                        "Bootloader %s updated" % self.bootloader
                    )
                    self.reveal_notify()

                    logger.info("%s update completed" % self.bootloader)

                    event = "%s [INFO]: %s update completed\n" % (
                        datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
                        self.bootloader,
                    )
                    self.messages_queue.put(event)

                    if self.restore is False and self.errors_found is False:
                        GLib.idle_add(
                            show_mw,
                            self,
                            "System changes",
                            f"<b>Kernel {self.action} completed</b>\n"
                            f"This window can now be closed",
                            priority=GLib.PRIORITY_DEFAULT,
                        )
                else:
                    if (
                        "Skipping"
                        or "same boot loader version in place already." in stdout_lines
                    ):
                        logger.info("%s update completed" % self.bootloader)

                        event = "%s [INFO]: <b>%s update completed</b>\n" % (
                            datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
                            self.bootloader,
                        )
                        self.messages_queue.put(event)

                        if self.restore is False and self.errors_found is False:
                            GLib.idle_add(
                                show_mw,
                                self,
                                "System changes",
                                f"<b>Kernel {self.action} completed</b>\n"
                                f"This window can now be closed",
                                self.image,
                                priority=GLib.PRIORITY_DEFAULT,
                            )

                    else:
                        self.label_notify_revealer.set_text(
                            "Bootloader %s update failed" % self.bootloader
                        )
                        self.reveal_notify()

                        event = "%s [ERROR]: <b>%s update failed</b>\n" % (
                            datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
                            self.bootloader,
                        )

                        logger.error("%s update failed" % self.bootloader)
                        logger.error(str(stdout_lines))
                        self.messages_queue.put(event)

                        GLib.idle_add(
                            show_mw,
                            self,
                            "System changes",
                            f"<b>Kernel {self.action} failed .. attempting kernel restore</b>\n"
                            f"There have been errors, please review the logs",
                            priority=GLib.PRIORITY_DEFAULT,
                        )

    except Exception as e:
        logger.error("Exception in update_bootloader(): %s" % e)
    finally:
        if os.path.exists(self.lockfile):
            os.unlink(self.lockfile)


# ======================================================================
#                   SHOW MESSAGE WINDOW AFTER BOOTLOADER UPDATE
# ======================================================================
def show_mw(self, title, msg):
    mw = MessageWindow(
        title=title,
        message=msg,
        detailed_message=False,
        transient_for=self,
    )

    mw.present()


# ======================================================================
#                   CHECKS PACMAN PROCESS
# ======================================================================
def check_pacman_process(self):
    try:
        process_found = False
        for proc in psutil.process_iter():
            try:
                pinfo = proc.as_dict(attrs=["pid", "name", "create_time"])

                if pinfo["name"] == "pacman":
                    process_found = True

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if process_found is True:
            logger.info("Pacman process is running")
            return True
        else:
            return False
    except Exception as e:
        logger.error("Exception in check_pacman_process() : %s" % e)
