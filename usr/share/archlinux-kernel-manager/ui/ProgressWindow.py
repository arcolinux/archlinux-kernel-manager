import sys
import gi
import os
import libs.functions as fn
from ui.MessageWindow import MessageWindow
from gi.repository import Gtk, Gio, GLib

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class ProgressWindow(Gtk.Window):
    def __init__(
        self,
        title,
        action,
        textview,
        textbuffer,
        kernel,
        switch,
        source,
        manager_gui,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.set_title(title=title)
        self.set_modal(modal=True)
        self.set_resizable(True)
        self.set_size_request(700, 400)
        self.connect("close-request", self.on_close)

        self.textview = textview
        self.textbuffer = textbuffer

        self.kernel_state_queue = fn.Queue()
        self.messages_queue = fn.Queue()
        self.kernel = kernel
        self.timeout_id = None
        self.errors_found = False

        self.action = action
        self.switch = switch

        self.restore = False

        self.source = source
        self.manager_gui = manager_gui

        self.bootloader = self.manager_gui.bootloader
        self.bootloader_grub_cfg = self.manager_gui.bootloader_grub_cfg

        vbox_progress = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        vbox_progress.set_name("main")

        self.set_child(child=vbox_progress)

        header_bar = Gtk.HeaderBar()
        self.label_title = Gtk.Label(xalign=0.5, yalign=0.5)

        header_bar.set_show_title_buttons(True)

        self.set_titlebar(header_bar)

        self.label_title.set_markup("<b>%s</b>" % title)
        header_bar.set_title_widget(self.label_title)

        vbox_icon_settings = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        vbox_icon_settings.set_name("vbox_icon_settings")

        lbl_heading = Gtk.Label(xalign=0.5, yalign=0.5)
        lbl_heading.set_name("label_flowbox_message")

        lbl_padding = Gtk.Label(xalign=0.0, yalign=0.0)
        lbl_padding.set_text(" ")

        grid_banner_img = Gtk.Grid()

        image_settings = None

        if action == "install":
            image_settings = Gtk.Image.new_from_file(
                os.path.join(base_dir, "images/48x48/akm-install.png")
            )
            lbl_heading.set_markup(
                "Installing <b>%s version %s </b>"
                % (self.kernel.name, self.kernel.version)
            )
        if action == "uninstall":
            image_settings = Gtk.Image.new_from_file(
                os.path.join(base_dir, "images/48x48/akm-remove.png")
            )
            lbl_heading.set_markup(
                "Removing <b>%s version %s </b>"
                % (self.kernel.name, self.kernel.version)
            )

        # get kernel version from pacman
        self.installed_kernel_version = fn.get_kernel_version(self.kernel.name)

        if self.installed_kernel_version is not None:
            fn.logger.debug(
                "Installed kernel version = %s" % self.installed_kernel_version
            )
        else:
            fn.logger.debug("Nothing to remove .. previous kernel not installed")

        image_settings.set_halign(Gtk.Align.START)
        image_settings.set_icon_size(Gtk.IconSize.LARGE)

        hbox_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        hbox_header.set_name("vbox_header")

        hbox_header.append(image_settings)
        hbox_header.append(lbl_heading)

        vbox_progress.append(hbox_header)

        self.spinner = Gtk.Spinner()
        self.spinner.set_spinning(True)

        image_warning = Gtk.Image.new_from_file(
            os.path.join(base_dir, "images/48x48/akm-warning.png")
        )

        image_warning.set_icon_size(Gtk.IconSize.LARGE)
        image_warning.set_halign(Gtk.Align.START)

        hbox_progress_warning = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=5
        )
        hbox_progress_warning.set_name("hbox_warning")

        hbox_progress_warning.append(image_warning)

        self.label_progress_window_desc = Gtk.Label(xalign=0, yalign=0)

        self.label_progress_window_desc.set_markup(
            f"Do not close this window while a kernel {self.action} activity is in progress\n"
            f"Progress can be monitored in the log below\n"
            f"<b>A reboot is recommended when Linux packages have changed</b>"
        )

        hbox_progress_warning.append(self.label_progress_window_desc)

        self.label_status = Gtk.Label(xalign=0, yalign=0)

        button_close = Gtk.Button.new_with_label("Close")
        button_close.set_size_request(100, 30)
        button_close.set_halign(Gtk.Align.END)

        button_close.connect(
            "clicked",
            self.on_button_close_response,
        )

        self.label_spinner_progress = Gtk.Label(xalign=0, yalign=0)
        if self.action == "install":
            self.label_spinner_progress.set_markup(
                "<b>Please wait kernel %s is in progress</b>" % "installation"
            )
        elif self.action == "uninstall":
            self.label_spinner_progress.set_markup(
                "<b>Please wait kernel %s is in progress</b>" % "removal"
            )

        self.hbox_spinner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        self.hbox_spinner.append(self.label_spinner_progress)
        self.hbox_spinner.append(self.spinner)

        vbox_padding = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        vbox_padding.set_valign(Gtk.Align.END)

        label_padding = Gtk.Label(xalign=0, yalign=0)
        label_padding.set_valign(Gtk.Align.END)
        vbox_padding.append(label_padding)

        hbox_button_close = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)

        hbox_button_close.append(button_close)
        hbox_button_close.set_halign(Gtk.Align.END)

        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_propagate_natural_height(True)
        self.scrolled_window.set_propagate_natural_width(True)
        self.scrolled_window.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC
        )

        hbox_notify_revealer = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=20
        )

        hbox_notify_revealer.set_name("hbox_notify_revealer")
        hbox_notify_revealer.set_halign(Gtk.Align.CENTER)

        self.notify_revealer = Gtk.Revealer()
        self.notify_revealer.set_reveal_child(False)
        self.label_notify_revealer = Gtk.Label(xalign=0, yalign=0)
        self.label_notify_revealer.set_name("label_notify_revealer")

        self.notify_revealer.set_child(hbox_notify_revealer)

        hbox_notify_revealer.append(self.label_notify_revealer)

        if self.textview.get_buffer() is not None:
            self.textview = Gtk.TextView()
            self.textview.set_property("editable", False)
            self.textview.set_property("monospace", True)

            self.textview.set_vexpand(True)
            self.textview.set_hexpand(True)

            self.textview.set_buffer(self.textbuffer)
            self.scrolled_window.set_child(self.textview)

        self.scrolled_window.set_size_request(300, 300)

        vbox_progress.append(hbox_progress_warning)
        vbox_progress.append(self.notify_revealer)
        vbox_progress.append(self.scrolled_window)
        vbox_progress.append(self.hbox_spinner)
        vbox_progress.append(self.label_status)
        vbox_progress.append(vbox_padding)
        vbox_progress.append(hbox_button_close)

        self.present()

        self.linux_headers = None

        if (
            self.source == "official"
            and action == "install"
            or action == "uninstall"
            and self.source == "official"
        ):
            if kernel.name == "linux":
                self.linux_headers = "linux-headers"
            if kernel.name == "linux-rt":
                self.linux_headers = "linux-rt-headers"
            if kernel.name == "linux-rt-lts":
                self.linux_headers = "linux-rt-lts-headers"
            if kernel.name == "linux-hardened":
                self.linux_headers = "linux-hardened-headers"
            if kernel.name == "linux-zen":
                self.linux_headers = "linux-zen-headers"
            if kernel.name == "linux-lts":
                self.linux_headers = "linux-lts-headers"

            self.official_kernels = [
                "%s/packages/l/%s/%s-x86_64%s"
                % (
                    fn.archlinux_mirror_archive_url,
                    kernel.name,
                    kernel.version,
                    kernel.file_format,
                ),
                "%s/packages/l/%s/%s-x86_64%s"
                % (
                    fn.archlinux_mirror_archive_url,
                    self.linux_headers,
                    kernel.headers,
                    kernel.file_format,
                ),
            ]

        # in the event an install goes wrong, fallback and reinstall previous kernel

        if self.source == "official":
            self.restore_kernel = None

            for inst_kernel in fn.get_installed_kernels():
                if inst_kernel.name == self.kernel.name:

                    self.restore_kernel = inst_kernel
                    break

            if self.restore_kernel:
                fn.logger.info("Restore kernel = %s" % self.restore_kernel.name)
                fn.logger.info(
                    "Restore kernel version = %s" % self.restore_kernel.version
                )
            else:
                fn.logger.info("No previous %s kernel installed" % self.kernel.name)
        else:
            fn.logger.info("Community kernel, no kernel restore available")

        if fn.check_pacman_lockfile() is False:
            th_monitor_messages_queue = fn.threading.Thread(
                name=fn.thread_monitor_messages,
                target=fn.monitor_messages_queue,
                daemon=True,
                args=(self,),
            )

            th_monitor_messages_queue.start()

            if fn.is_thread_alive(fn.thread_monitor_messages):
                self.textbuffer.delete(
                    self.textbuffer.get_start_iter(), self.textbuffer.get_end_iter()
                )

            if not fn.is_thread_alive(fn.thread_check_kernel_state):
                th_check_kernel_state = fn.threading.Thread(
                    name=fn.thread_check_kernel_state,
                    target=self.check_kernel_state,
                    daemon=True,
                )
                th_check_kernel_state.start()

            if action == "install" and self.source == "community":
                self.label_notify_revealer.set_text(
                    "Installing from %s" % kernel.repository
                )
                self.reveal_notify()
                event = (
                    "%s [INFO]: Installing kernel from repository %s, kernel = %s-%s\n"
                    % (
                        fn.datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
                        self.kernel.repository,
                        self.kernel.name,
                        self.kernel.version,
                    )
                )
                self.messages_queue.put(event)

                if not fn.is_thread_alive(fn.thread_install_community_kernel):
                    th_install_ch = fn.threading.Thread(
                        name=fn.thread_install_community_kernel,
                        target=fn.install_community_kernel,
                        args=(self,),
                        daemon=True,
                    )

                    th_install_ch.start()

            if action == "install" and self.source == "official":
                self.label_notify_revealer.set_text("Installing kernel packages ...")

                self.reveal_notify()

                event = "%s [INFO]: Installing kernel = %s | version = %s\n" % (
                    fn.datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
                    self.kernel.name,
                    self.kernel.version,
                )
                self.messages_queue.put(event)

                if not fn.is_thread_alive(fn.thread_install_archive_kernel):
                    th_install = fn.threading.Thread(
                        name=fn.thread_install_archive_kernel,
                        target=fn.install_archive_kernel,
                        args=(self,),
                        daemon=True,
                    )

                    th_install.start()

            if action == "uninstall":
                if fn.check_pacman_lockfile() is False:
                    self.label_notify_revealer.set_text("Removing kernel packages ...")
                    self.reveal_notify()

                    event = "%s [INFO]: Uninstalling kernel %s %s\n" % (
                        fn.datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
                        self.kernel.name,
                        self.kernel.version,
                    )
                    self.messages_queue.put(event)

                    if not fn.is_thread_alive(fn.thread_uninstall_kernel):
                        th_uninstall_kernel = fn.threading.Thread(
                            name=fn.thread_uninstall_kernel,
                            target=self.uninstall_kernel,
                            daemon=True,
                        )

                        th_uninstall_kernel.start()
        else:
            self.label_notify_revealer.set_text(
                "Pacman lockfile found cannot continue ..."
            )

            self.reveal_notify()

            fn.logger.error(
                "Pacman lockfile found, is another pacman process running ?"
            )

    def timeout(self):
        self.hide_notify()

    def hide_notify(self):
        self.notify_revealer.set_reveal_child(False)
        if self.timeout_id is not None:
            GLib.source_remove(self.timeout_id)
        self.timeout_id = None

    def reveal_notify(self):
        # reveal = self.notify_revealer.get_reveal_child()
        self.notify_revealer.set_reveal_child(True)
        self.timeout_id = GLib.timeout_add(3000, self.timeout)

    def on_button_close_response(self, widget):
        if fn.check_pacman_process(self):
            mw = MessageWindow(
                title="Pacman process running",
                message="Pacman is busy processing a transaction .. please wait",
                image_path="images/48x48/akm-progress.png",
                transient_for=self,
                detailed_message=False,
            )

            mw.present()
        else:
            self.destroy()

    def on_close(self, data):
        if fn.check_pacman_process(self):
            mw = MessageWindow(
                title="Pacman process running",
                message="Pacman is busy processing a transaction .. please wait",
                image_path="images/48x48/akm-progress.png",
                transient_for=self,
                detailed_message=False,
            )

            mw.present()

            return True
        return False

    def check_kernel_state(self):
        returncode = None
        kernel = None
        while True:
            items = self.kernel_state_queue.get()

            try:
                if items is not None:
                    returncode, action, kernel = items

                    if returncode == 0:
                        self.label_notify_revealer.set_text(
                            "Kernel %s completed" % action
                        )
                        self.reveal_notify()

                        fn.logger.info("Kernel %s completed" % action)

                    if returncode == 1:
                        self.errors_found = True

                        self.label_notify_revealer.set_text("Kernel %s failed" % action)
                        self.reveal_notify()

                        fn.logger.error("Kernel %s failed" % action)

                        event = "%s <b>[ERROR]: Kernel %s failed</b>\n" % (
                            fn.datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
                            action,
                        )
                        self.messages_queue.put(event)

                        self.label_status.set_markup(
                            "<span foreground='orange'><b>Kernel %s failed - see logs above</b></span>"
                            % action
                        )

                        # undo action here if action == install

                        event = (
                            "%s<b> [INFO]: Attempting to undo previous Linux package changes</b>\n"
                            % (
                                fn.datetime.datetime.now().strftime(
                                    "%Y-%m-%d-%H-%M-%S"
                                ),
                            )
                        )

                        self.messages_queue.put(event)

                        if action == "install" and self.restore_kernel is not None:
                            self.restore = True
                            fn.logger.info(
                                "Installation failed, attempting removal of previous Linux package changes"
                            )
                            self.set_title("Kernel installation failed")

                            self.label_spinner_progress.set_markup(
                                "<b>Please wait restoring kernel %s</b>"
                                % self.restore_kernel.version
                            )

                            fn.uninstall(self)

                            fn.logger.info(
                                "Restoring previously installed kernel %s"
                                % self.restore_kernel.version
                            )

                            self.official_kernels = [
                                "%s/packages/l/%s/%s-%s-x86_64%s"
                                % (
                                    fn.archlinux_mirror_archive_url,
                                    self.restore_kernel.name,
                                    self.restore_kernel.name,
                                    self.restore_kernel.version,
                                    ".pkg.tar.zst",
                                ),
                                "%s/packages/l/%s/%s-%s-x86_64%s"
                                % (
                                    fn.archlinux_mirror_archive_url,
                                    self.linux_headers,
                                    self.linux_headers,
                                    self.restore_kernel.version,
                                    ".pkg.tar.zst",
                                ),
                            ]
                            self.errors_found = False
                            fn.install_archive_kernel(self)
                            self.set_title("Kernel installation failed")
                            self.label_status.set_markup(
                                f"<span foreground='orange'><b>Kernel %s failed - see logs above</b></span>\n"
                                % action
                            )

                    # self.spinner.set_spinning(False)
                    # self.hbox_spinner.hide()
                    #
                    # self.label_progress_window_desc.set_markup(
                    #     f"<b>This window can be now closed</b>\n"
                    #     f"<b>A reboot is recommended when Linux packages have changed</b>"
                    # )

                    # break
                else:
                    if (
                        returncode == 0
                        and "-headers" in kernel
                        or action == "uninstall"
                        or action == "install"
                        and self.errors_found is False
                    ):

                        fn.update_bootloader(self)
                        self.update_installed_list()
                        self.update_official_list()

                        if len(self.manager_gui.community_kernels) > 0:
                            self.update_community_list()

                        if self.restore == False:
                            self.label_title.set_markup(
                                "<b>Kernel %s completed</b>" % action
                            )

                            self.label_status.set_markup(
                                "<span foreground='orange'><b>Kernel %s completed</b></span>"
                                % action
                            )

                            self.spinner.set_spinning(False)
                            self.hbox_spinner.hide()

                            self.label_progress_window_desc.set_markup(
                                f"<b>This window can be now closed</b>\n"
                                f"<b>A reboot is recommended when Linux packages have changed</b>"
                            )
                        else:
                            self.label_title.set_markup(
                                "<b>Kernel %s failed</b>" % action
                            )

                            self.label_status.set_markup(
                                "<span foreground='orange'><b>Kernel %s failed</b></span>"
                                % action
                            )

                            self.spinner.set_spinning(False)
                            self.hbox_spinner.hide()

                            self.label_progress_window_desc.set_markup(
                                f"<b>This window can be now closed</b>\n"
                                f"<b>Previous kernel restored due to failure</b>\n"
                                f"<b>A reboot is recommended when Linux packages have changed</b>"
                            )

                    # # else:
                    # self.spinner.set_spinning(False)
                    # self.hbox_spinner.hide()
                    #
                    # self.label_progress_window_desc.set_markup(
                    #     f"<b>This window can be now closed</b>\n"
                    #     f"<b>A reboot is recommended when Linux packages have changed</b>"
                    # )

                    break
            except Exception as e:
                fn.logger.error("Exception in check_kernel_state(): %s" % e)

            finally:
                self.kernel_state_queue.task_done()

    def update_installed_list(self):
        self.manager_gui.installed_kernels = fn.get_installed_kernels()
        GLib.idle_add(
            self.manager_gui.kernel_stack.add_installed_kernels_to_stack, True
        )

    def update_official_list(self):
        self.manager_gui.installed_kernels = fn.get_installed_kernels()
        GLib.idle_add(
            self.manager_gui.kernel_stack.add_official_kernels_to_stack,
            True,
        )

    def update_community_list(self):
        self.manager_gui.installed_kernels = fn.get_installed_kernels()
        GLib.idle_add(
            self.manager_gui.kernel_stack.add_community_kernels_to_stack,
            True,
        )

    def uninstall_kernel(self):
        event = "%s [INFO]: Uninstalling kernel %s\n" % (
            fn.datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
            self.kernel.version,
        )

        self.messages_queue.put(event)

        fn.uninstall(self)
