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
headers = {"Content-Type": "text/plain;charset=UTF-8"}

dist_id = distro.id()
dist_name = distro.name()

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

logger = logging.getLogger("logger")

# create console handler and set level to debug
ch = logging.StreamHandler()


logger.setLevel(logging.DEBUG)
ch.setLevel(logging.DEBUG)

# create formatter
formatter = logging.Formatter(
    "%(asctime)s:%(levelname)s > %(message)s", "%Y-%m-%d %H:%M:%S"
)
# add formatter to ch
ch.setFormatter(formatter)


# add ch to logger
logger.addHandler(ch)


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
                                ) > (
                                    datetime.datetime.strptime(
                                        cache_timestamp, "%Y-%m-%d %H-%M-%S"
                                    ).date()
                                ):
                                    logger.info(
                                        "Linux kernel package updated, cache refresh required"
                                    )

                                    refresh_cache(self)

                                    return True

                                else:
                                    logger.info(
                                        "Linux kernel package not updated, cache refresh not required"
                                    )

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


def permissions(dst):
    try:
        groups = subprocess.run(
            ["sh", "-c", "id " + sudo_username],
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        for x in groups.stdout.decode().split(" "):
            if "gid" in x:
                g = x.split("(")[1]
                group = g.replace(")", "").strip()
        subprocess.call(["chown", "-R", sudo_username + ":" + group, dst], shell=False)

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
        logger.debug("Config file = %s" % config_file)
        logger.info("Reading in config file")
        config_data = None
        with open(config_file, "rb") as f:
            config_data = tomlkit.load(f)

            for official_kernel in config_data["kernels"]["official"]:
                supported_kernels_dict[official_kernel["name"]] = (
                    official_kernel["description"],
                    official_kernel["headers"],
                )

            for community_kernel in config_data["kernels"]["community"]:
                community_kernels_dict[community_kernel["name"]] = (
                    community_kernel["description"],
                    community_kernel["headers"],
                    community_kernel["repository"],
                )

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
        install_cmd_str = [
            "pacman",
            "-U",
            self.official_kernels[0],
            self.official_kernels[1],
            "--noconfirm",
            "--needed",
        ]

        wait_for_pacman_process()

        logger.info("Running %s" % install_cmd_str)

        event = "%s [INFO]: Running %s\n" % (
            datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
            " ".join(install_cmd_str),
        )

        event_log = []
        self.messages_queue.put(event)

        with subprocess.Popen(
            install_cmd_str,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
        ) as process:
            while True:
                if process.poll() is not None:
                    break
                for line in process.stdout:
                    print(line.strip())
                    self.messages_queue.put(line)
                    event_log.append(line.lower().strip())

                time.sleep(0.3)

        error = None

        if (
            "installation finished. no error reported."
            or "initcpio image generation successful" in event_log
        ):
            error = False

        else:
            if error is None:
                # check errors and indicate to user install failed
                for log in event_log:
                    # if "installation finished. no error reported." in log:
                    #     error = False
                    #     break
                    if "error" in log or "errors" in log:
                        event = (
                            "%s <b>[ERROR]: Errors have been encountered during installation</b>\n"
                            % (datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"))
                        )

                        logger.error(log)

                        self.messages_queue.put(event)

                        self.errors_found = True

                        error = True

                        GLib.idle_add(
                            show_mw,
                            self,
                            "System changes",
                            f"Kernel {self.action} failed\n"
                            f"<b>There have been errors, please review the logs</b>\n",
                            "images/48x48/akm-warning.png",
                            priority=GLib.PRIORITY_DEFAULT,
                        )

                        break

        # query to check if kernel installed

        if check_kernel_installed(self.kernel.name + "-headers") and error is False:

            self.kernel_state_queue.put((0, "install", self.kernel.name + "-headers"))

            event = "%s [INFO]: Installation of %s-headers completed\n" % (
                datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
                self.kernel.name,
            )

            self.messages_queue.put(event)

        else:
            self.kernel_state_queue.put((1, "install", self.kernel.name + "-headers"))

            event = "%s [ERROR]: Installation of %s-headers failed\n" % (
                datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
                self.kernel.name,
            )

            self.errors_found = True
            self.messages_queue.put(event)

        if check_kernel_installed(self.kernel.name) and error is False:
            self.kernel_state_queue.put((0, "install", self.kernel.name))

            event = "%s [INFO]: Installation of kernel %s completed\n" % (
                datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
                self.kernel.name,
            )

            self.messages_queue.put(event)

        else:
            self.kernel_state_queue.put((1, "install", self.kernel.name))

            event = "%s [ERROR]: Installation of kernel %s failed\n" % (
                datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
                self.kernel.name,
            )

            self.messages_queue.put(event)

        # signal to say end reached
        self.kernel_state_queue.put(None)

    except Exception as e:
        logger.error("Exception in install_archive_kernel(): %s" % e)

        GLib.idle_add(
            show_mw,
            self,
            "System changes",
            f"<b>Kernel {self.action} failed</b>\n"
            f"There have been errors, please review the logs\n",
            "images/48x48/akm-warning.png",
            priority=GLib.PRIORITY_DEFAULT,
        )


def refresh_cache(self):
    if os.path.exists(cache_file):
        os.remove(cache_file)
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

                                # if (
                                #     datetime.datetime.now().year
                                #     - datetime.datetime.strptime(
                                #         k["last_modified"], "%d-%b-%Y %H:%M"
                                #     ).year
                                #     <= 2
                                # ):
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
    try:
        kernel_versions = {}
        for kernel in supported_kernels_dict:
            check_cmd_str = ["pacman", "-Si", kernel]

            process_kernel_query = subprocess.Popen(
                check_cmd_str,
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            out, err = process_kernel_query.communicate(timeout=process_timeout)

            if process_kernel_query.returncode == 0:
                for line in out.decode("utf-8").splitlines():
                    if line.startswith("Version         :"):
                        kernel_versions[kernel] = line.split("Version         :")[1]
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
        # time.sleep(0.1)
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
        logger.debug("Response is 200")
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

            if len(fetched_kernels_dict) > 0:  # and self.refresh_cache is True:
                write_cache()
                read_cache(self)

                self.queue_kernels.put(cached_kernels_list)
            # elif self.refresh_cache is False:
            #     logger.info("Cache already processed")
            #     read_cache(self)
            #     self.queue_kernels.put(cached_kernels_list)

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
        logger.info("Thread = %s and state is %s" % (thread.name, thread.is_alive()))


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
        logger.debug("Running cmd = %s" % check_cmd_str)
        process_kernel_query = subprocess.Popen(
            check_cmd_str, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        out, err = process_kernel_query.communicate(timeout=process_timeout)

        logger.debug(out.decode("utf-8"))

        if process_kernel_query.returncode == 0:
            for line in out.decode("utf-8").splitlines():
                if line.split(" ")[0] == name:
                    return True
        else:
            return False

        return False
    except Exception as e:
        logger.error("Exception in check_kernel_installed(): %s" % e)


def wait_for_pacman_process():

    timeout = 120
    i = 0
    while check_pacman_lockfile():
        time.sleep(0.1)
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
            self.kernel_state_queue.put((0, "uninstall", self.kernel.name))

        logger.debug("Uninstall cmd = %s" % uninstall_cmd_str)

        # check if kernel, and kernel header is actually installed
        if uninstall_cmd_str is not None:

            wait_for_pacman_process()

            logger.info("Running %s" % uninstall_cmd_str)

            event = "%s [INFO]: Running %s\n" % (
                datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
                " ".join(uninstall_cmd_str),
            )
            self.messages_queue.put(event)

            with subprocess.Popen(
                uninstall_cmd_str,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                universal_newlines=True,
            ) as process:
                while True:
                    if process.poll() is not None:
                        break
                    for line in process.stdout:
                        self.messages_queue.put(line)
                        print(line.strip())
                        event_log.append(line.lower().strip())

                        # self.pacmanlog_queue.put(line)
                        # process_stdout_lst.append(line)

                    time.sleep(0.3)

            self.errors_found = False
            for log in event_log:
                if "error" in log:
                    self.errors_found = True

            # query to check if kernel installed
            if "headers" in uninstall_cmd_str:
                if check_kernel_installed(self.kernel.name + "-headers") is True:
                    self.kernel_state_queue.put(
                        (1, "uninstall", self.kernel.name + "-headers")
                    )

                    event = (
                        "%s [ERROR]: Uninstall failed\n"
                        % datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
                    )

                    self.messages_queue.put(event)

                else:
                    self.kernel_state_queue.put((0, "uninstall", self.kernel.name))

                    event = (
                        "%s [INFO]: Uninstall completed\n"
                        % datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
                    )

                    self.messages_queue.put(event)

            else:
                if check_kernel_installed(self.kernel.name) is True:
                    self.kernel_state_queue.put((1, "uninstall", self.kernel.name))

                    event = (
                        "%s [ERROR]: Uninstall failed\n"
                        % datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
                    )

                    self.messages_queue.put(event)

                else:
                    self.kernel_state_queue.put((0, "uninstall", self.kernel.name))

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
                            if "MiB" in install_size:
                                install_size = round(
                                    float(install_size.replace("MiB", "").strip())
                                    * 1.048576,
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
        error = False
        install_cmd_str = [
            "pacman",
            "-S",
            "%s/%s" % (self.kernel.repository, self.kernel.name),
            "%s/%s" % (self.kernel.repository, "%s-headers" % self.kernel.name),
            "--noconfirm",
            "--needed",
        ]

        logger.info("Running %s" % install_cmd_str)

        event = "%s [INFO]: Running %s\n" % (
            datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
            " ".join(install_cmd_str),
        )

        event_log = []

        self.messages_queue.put(event)

        with subprocess.Popen(
            install_cmd_str,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
        ) as process:
            while True:
                if process.poll() is not None:
                    break
                for line in process.stdout:
                    print(line.strip())
                    self.messages_queue.put(line)
                    event_log.append(line.lower().strip())

                time.sleep(0.3)

        for log in event_log:
            if "installation finished. no error reported." in log:
                error = False
                break

            if "error" in log:
                error = True

        if check_kernel_installed(self.kernel.name) and error is False:
            logger.info("Kernel = installed")

            self.kernel_state_queue.put((0, "install", self.kernel.name))

            event = "%s [INFO]: Installation of %s completed\n" % (
                datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
                self.kernel.name,
            )

            self.messages_queue.put(event)

        else:
            logger.error("Kernel = install failed")

            self.kernel_state_queue.put((1, "install", self.kernel.name))

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
    query_str = ["pacman", "-Qi", package_name]

    try:
        process_kernel_query = subprocess.Popen(
            query_str, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        out, err = process_kernel_query.communicate(timeout=process_timeout)
        install_size = None
        install_date = None
        if process_kernel_query.returncode == 0:
            for line in out.decode("utf-8").splitlines():
                if line.startswith("Installed Size  :"):
                    install_size = line.split("Installed Size  :")[1].strip()
                    if "MiB" in install_size:
                        install_size = round(
                            float(install_size.replace("MiB", "").strip()) * 1.048576,
                        )
                if line.startswith("Install Date    :"):
                    install_date = line.split("Install Date    :")[1].strip()
            return install_size, install_date
    except Exception as e:
        logger.error("Exception in get_installed_kernel_info(): %s" % e)


# ======================================================================
#                   GET INSTALLED KERNELS
# ======================================================================


def get_installed_kernels():
    query_str = ["pacman", "-Q"]
    installed_kernels = []

    try:
        process_kernel_query = subprocess.Popen(
            query_str, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        out, err = process_kernel_query.communicate(timeout=process_timeout)
        if process_kernel_query.returncode == 0:
            for line in out.decode("utf-8").splitlines():
                if line.lower().strip().startswith("linux"):
                    package_name = line.split(" ")[0]
                    package_version = line.split(" ")[1]

                    if (
                        package_name in supported_kernels_dict
                        or package_name in community_kernels_dict
                    ):
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

        return installed_kernels
    except Exception as e:
        logger.error("Exception in get_installed_kernels(): %s" % e)


# ======================================================================
#                   GET ACTIVE KERNEL
# ======================================================================


def get_active_kernel():
    logger.info("Getting active Linux kernel")
    query_str = ["uname", "-rs"]

    try:
        process_kernel_query = subprocess.Popen(
            query_str, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        out, err = process_kernel_query.communicate(timeout=process_timeout)

        if process_kernel_query.returncode == 0:
            for line in out.decode("utf-8").splitlines():
                if len(line.strip()) > 0:
                    kernel = line.strip()
                    _version = "-".join(kernel.split("-")[:-1])
                    _type = kernel.split("-")[-1]

                    logger.info("Active kernel = %s" % kernel)

                    return kernel
    except Exception as e:
        logger.error("Exception in get_active_kernel(): %s" % e)


# =====================================================
#               PACMAN SYNC PACKAGE DB
# =====================================================
def sync_package_db():
    try:
        sync_str = ["pacman", "-Sy"]
        logger.info("Synchronizing pacman package databases")
        process_sync = subprocess.run(
            sync_str,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=process_timeout,
        )

        if process_sync.returncode == 0:
            return None
        else:
            if process_sync.stdout:
                out = str(process_sync.stdout.decode("utf-8"))
                logger.error(out)

                return out

    except Exception as e:
        logger.error("Exception in sync_package_db(): %s" % e)


def get_boot_loader():
    try:
        logger.info("Getting bootloader")
        cmd = ["bootctl", "status"]
        logger.debug("Running %s" % " ".join(cmd))
        process = subprocess.run(
            cmd,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=process_timeout,
            universal_newlines=True,
            bufsize=1,
        )

        if process.returncode == 0:
            for line in process.stdout.splitlines():
                if line.strip().startswith("Product:"):
                    product = line.strip().split("Product:")[1].strip()
                    if "grub" in product.lower():
                        logger.info("bootctl product reports booted with grub")
                        return "grub"
                    if "systemd-boot" in product.lower():
                        logger.info("bootcl product reports booted with systemd-boot")
                        return "systemd-boot"
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


def get_kernel_version(kernel):
    cmd = ["pacman", "-Qli", kernel]
    # pacman_kernel_version = None
    kernel_modules_path = None
    try:
        logger.debug("Running %s" % " ".join(cmd))
        process = subprocess.run(
            cmd,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=process_timeout,
            universal_newlines=True,
            bufsize=1,
        )

        if process.returncode == 0:
            for line in process.stdout.splitlines():
                # if line.startswith("Version         :"):
                #     pacman_kernel_version = line.split("Version         :")[1].strip()
                #     print(pacman_kernel_version)

                if "/usr/lib/modules/" in line:
                    if "kernel" in line.split(" ")[1]:
                        kernel_modules_path = line.split(" ")[1]
                        break

            if kernel_modules_path is not None:
                return (
                    kernel_modules_path.split("/usr/lib/modules/")[1]
                    .strip()
                    .split("/kernel/")[0]
                    .strip()
                )
        else:
            return None

    except Exception as e:
        logger.error("Exception in get_kernel_version(): %s" % e)


def run_process(self):
    error = False

    logger.debug("Running process = %s" % " ".join(self.cmd))
    with subprocess.Popen(
        self.cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        universal_newlines=True,
    ) as process:
        while True:
            if process.poll() is not None:
                break
            for line in process.stdout:
                self.messages_queue.put(line)
                self.stdout_lines.append(line.lower().strip())
                print(line.strip())

    for log in self.stdout_lines:
        if "error" in log or "errors" in log:
            self.errors_found = True

            error = True

    if error is True:
        self.label_notify_revealer.set_text("%s failed" % " ".join(self.cmd))
        self.reveal_notify()

        logger.error("%s failed" % " ".join(self.cmd))
    else:
        self.label_notify_revealer.set_text("%s completed" % " ".join(self.cmd))
        self.reveal_notify()

        logger.info("%s completed" % " ".join(self.cmd))

        # time.sleep(0.3)


# ======================================================================
#                  UPDATE BOOTLOADER ENTRIES
# ======================================================================


# grub - grub-mkconfig /boot/grub/grub.cfg
# systemd-boot - bootctl update
def update_bootloader(self):
    cmds = []
    error = False
    self.stdout_lines = []

    if self.action == "install":
        image = "images/48x48/akm-install.png"

        if self.installed_kernel_version is not None:

            for self.cmd in [
                ["kernel-install", "add-all"],
                ["kernel-install", "remove", self.installed_kernel_version],
            ]:
                run_process(self)

        else:
            self.cmd = ["kernel-install", "add-all"]
            run_process(self)

    else:
        image = "images/48x48/akm-remove.png"
        if self.installed_kernel_version is not None:
            self.cmd = ["kernel-install", "remove", self.installed_kernel_version]
            run_process(self)

    try:

        """
        kernel-install -add-all
        kernel-install remove $kernel_version
        this is for systems which do not have any pacman hooks in place
        useful for vanilla arch installs
        """

        self.label_notify_revealer.set_text("Updating bootloader %s" % self.bootloader)
        self.reveal_notify()

        logger.info("Current bootloader = %s" % self.bootloader)

        cmd = None

        if self.bootloader == "grub":
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
            cmd = ["bootctl", "--no-variables", "--graceful", "update"]
            event = "%s [INFO]: Running %s\n" % (
                datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
                " ".join(cmd),
            )
            self.messages_queue.put(event)
        else:
            logger.error("Bootloader is empty / not supported")

        if cmd is not None:
            self.stdout_lines = []
            logger.info("Running %s" % " ".join(cmd))
            with subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                universal_newlines=True,
            ) as process:
                while True:
                    if process.poll() is not None:
                        break
                    for line in process.stdout:
                        self.stdout_lines.append(line.strip())
                        self.messages_queue.put(line)
                        print(line.strip())

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

                    logger.info("Linux packages have changed a reboot is recommended")
                    event = "%s [INFO]: <b>#### Linux packages have changed a reboot is recommended ####</b>\n" % datetime.datetime.now().strftime(
                        "%Y-%m-%d-%H-%M-%S"
                    )
                    self.messages_queue.put(event)

                    if self.restore is False:
                        GLib.idle_add(
                            show_mw,
                            self,
                            "System changes",
                            f"<b>Kernel {self.action} completed</b>\n"
                            f"This window can now be closed\n",
                            image,
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

                        if self.restore is False:
                            GLib.idle_add(
                                show_mw,
                                self,
                                "System changes",
                                f"<b>Kernel {self.action} completed</b>\n"
                                f"This window can now be closed\n",
                                image,
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
                            f"There have been errors, please review the logs\n",
                            image,
                            priority=GLib.PRIORITY_DEFAULT,
                        )

        else:
            logger.error("Bootloader update failed")

            GLib.idle_add(
                show_mw,
                self,
                "System changes",
                f"<b>Kernel {self.action} failed</b>\n"
                f"There have been errors, please review the logs\n",
                image,
                priority=GLib.PRIORITY_DEFAULT,
            )
        # else:
        #     logger.error("Bootloader update cannot continue, failed to set command.")
    except Exception as e:
        logger.error("Exception in update_bootloader(): %s" % e)


# ======================================================================
#                   SHOW MESSAGE WINDOW AFTER BOOTLOADER UPDATE
# ======================================================================
def show_mw(self, title, msg, image):
    mw = MessageWindow(
        title=title,
        message=msg,
        image_path=image,
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
