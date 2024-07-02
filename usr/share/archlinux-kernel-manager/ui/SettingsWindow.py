import gi
import os
from ui.Stack import Stack
from ui.MessageWindow import MessageWindow
import libs.functions as fn
from gi.repository import Gtk, Gio, GLib, GObject

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class SettingsWindow(Gtk.Window):
    def __init__(self, fn, manager_gui, **kwargs):
        super().__init__(**kwargs)

        self.set_title("Arch Linux Kernel Manager - Settings")
        self.set_resizable(False)
        self.set_size_request(600, 600)
        stack = Stack(transition_type="CROSSFADE")

        self.set_icon_name("akm-tux")
        self.manager_gui = manager_gui
        self.set_modal(True)
        self.set_transient_for(self.manager_gui)

        self.queue_kernels = self.manager_gui.queue_kernels

        header_bar = Gtk.HeaderBar()

        header_bar.set_show_title_buttons(True)

        self.set_titlebar(header_bar)

        hbox_main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        hbox_main.set_name("box")
        self.set_child(child=hbox_main)

        vbox_header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        vbox_header.set_name("vbox_header")

        lbl_heading = Gtk.Label(xalign=0.5, yalign=0.5)
        lbl_heading.set_name("label_flowbox_message")
        lbl_heading.set_text("Preferences")

        lbl_padding = Gtk.Label(xalign=0.0, yalign=0.0)
        lbl_padding.set_text(" ")

        grid_banner_img = Gtk.Grid()

        image_settings = Gtk.Image.new_from_file(
            os.path.join(base_dir, "images/48x48/akm-settings.png")
        )

        image_settings.set_icon_size(Gtk.IconSize.LARGE)
        image_settings.set_halign(Gtk.Align.START)

        grid_banner_img.attach(image_settings, 0, 1, 1, 1)
        grid_banner_img.attach_next_to(
            lbl_padding,
            image_settings,
            Gtk.PositionType.RIGHT,
            1,
            1,
        )

        grid_banner_img.attach_next_to(
            lbl_heading,
            lbl_padding,
            Gtk.PositionType.RIGHT,
            1,
            1,
        )

        vbox_header.append(grid_banner_img)

        hbox_main.append(vbox_header)

        stack_switcher = Gtk.StackSwitcher()
        stack_switcher.set_orientation(Gtk.Orientation.HORIZONTAL)
        stack_switcher.set_stack(stack)

        button_close = Gtk.Button(label="Close")
        button_close.connect("clicked", self.on_close_clicked)

        hbox_stack_sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        hbox_stack_sidebar.set_name("box")

        hbox_stack_sidebar.append(stack_switcher)
        hbox_stack_sidebar.append(stack)

        hbox_main.append(hbox_stack_sidebar)

        vbox_button = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        vbox_button.set_halign(Gtk.Align.END)
        vbox_button.set_name("box")

        vbox_button.append(button_close)

        hbox_stack_sidebar.append(vbox_button)

        vbox_settings = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        vbox_settings.set_name("box")

        label_official_kernels = Gtk.Label(xalign=0, yalign=0)
        label_official_kernels.set_markup(
            "<b>Latest Official kernels (%s)</b>" % len(fn.supported_kernels_dict)
        )

        label_community_kernels = Gtk.Label(xalign=0, yalign=0)
        label_community_kernels.set_markup(
            "<b>Latest Community based kernels (%s)</b>"
            % len(self.manager_gui.community_kernels)
        )

        vbox_settings_listbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)

        self.listbox_official_kernels = Gtk.ListBox()
        self.listbox_official_kernels.set_selection_mode(Gtk.SelectionMode.NONE)

        self.label_loading_kernels = Gtk.Label(xalign=0, yalign=0)
        self.label_loading_kernels.set_text("Loading ...")

        self.listbox_official_kernels.append(self.label_loading_kernels)

        listbox_community_kernels = Gtk.ListBox()
        listbox_community_kernels.set_selection_mode(Gtk.SelectionMode.NONE)

        scrolled_window_community = Gtk.ScrolledWindow()
        scrolled_window_official = Gtk.ScrolledWindow()

        scrolled_window_community.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC
        )

        scrolled_window_official.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC
        )

        scrolled_window_community.set_size_request(0, 150)
        scrolled_window_official.set_size_request(0, 150)

        scrolled_window_official.set_child(self.listbox_official_kernels)
        vbox_community_warning = None

        self.kernel_versions_queue = fn.Queue()
        fn.Thread(
            target=fn.get_latest_versions,
            args=(self,),
            daemon=True,
        ).start()

        fn.Thread(target=self.check_official_version_queue, daemon=True).start()

        if len(self.manager_gui.community_kernels) > 0:
            for community_kernel in self.manager_gui.community_kernels:
                row_community_kernel = Gtk.ListBoxRow()
                hbox_community_kernel = Gtk.Box(
                    orientation=Gtk.Orientation.VERTICAL, spacing=5
                )
                hbox_community_kernel.set_name("box_row")

                hbox_row_official_kernel_row = Gtk.Box(
                    orientation=Gtk.Orientation.HORIZONTAL, spacing=10
                )

                label_community_kernel = Gtk.Label(xalign=0, yalign=0)
                label_community_kernel.set_text("%s" % community_kernel.name)

                label_community_kernel_version = Gtk.Label(xalign=0, yalign=0)
                label_community_kernel_version.set_text("%s" % community_kernel.version)

                hbox_row_official_kernel_row.append(label_community_kernel)
                hbox_row_official_kernel_row.append(label_community_kernel_version)

                hbox_community_kernel.append(hbox_row_official_kernel_row)

                row_community_kernel.set_child(hbox_community_kernel)
                listbox_community_kernels.append(row_community_kernel)
                scrolled_window_community.set_child(listbox_community_kernels)
        else:
            vbox_community_warning = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL, spacing=10
            )
            image_warning = Gtk.Image.new_from_file(
                os.path.join(base_dir, "images/48x48/akm-warning.png")
            )

            image_warning.set_icon_size(Gtk.IconSize.LARGE)
            image_warning.set_halign(Gtk.Align.START)

            hbox_warning = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
            hbox_warning.set_name("hbox_warning")

            hbox_warning.append(image_warning)

            label_pacman_no_community = Gtk.Label(xalign=0, yalign=0)
            label_pacman_no_community.set_name("label_community_warning")
            label_pacman_no_community.set_markup(
                f"<b>Cannot find any supported unofficial pacman repository's</b>\n"
                f"<b>Add the Chaotic-AUR pacman repository to access Community based kernels</b>"
            )

            hbox_warning.append(label_pacman_no_community)

            vbox_community_warning.append(hbox_warning)

        vbox_settings_listbox.append(label_official_kernels)
        vbox_settings_listbox.append(scrolled_window_official)
        vbox_settings_listbox.append(label_community_kernels)

        if len(self.manager_gui.community_kernels) > 0:
            vbox_settings_listbox.append(scrolled_window_community)
        else:
            vbox_settings_listbox.append(vbox_community_warning)

        vbox_settings.append(vbox_settings_listbox)

        vbox_settings_adv = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)

        vbox_settings_adv.set_name("box")

        self.listbox_settings_adv = Gtk.ListBox()
        self.listbox_settings_adv.set_selection_mode(Gtk.SelectionMode.NONE)

        row_settings_adv = Gtk.ListBoxRow()
        self.listbox_settings_adv.append(row_settings_adv)

        hbox_bootloader_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        hbox_bootloader_row.set_name("box_row")
        hbox_bootloader_row.set_halign(Gtk.Align.START)

        self.hbox_bootloader_grub_row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=5
        )
        self.hbox_bootloader_grub_row.set_name("box_row")
        self.hbox_bootloader_grub_row.set_halign(Gtk.Align.START)

        self.text_entry_bootloader_file = Gtk.Entry()

        hbox_switch_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        hbox_switch_row.set_name("box_row")
        hbox_switch_row.set_halign(Gtk.Align.START)

        hbox_log_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        hbox_log_row.set_name("box_row")
        hbox_log_row.set_halign(Gtk.Align.START)

        label_bootloader = Gtk.Label(xalign=0, yalign=0)
        label_bootloader.set_markup("<b>Bootloader</b>")

        hbox_warning = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        hbox_warning.set_name("hbox_warning")

        label_bootloader_warning = Gtk.Label(xalign=0, yalign=0)
        label_bootloader_warning.set_markup(
            f"Only change this setting if you know what you are doing\n"
            f"The selected Grub/Systemd-boot bootloader entry will be updated\n"
            f"<b>This may break your system</b>"
        )

        hbox_warning.append(label_bootloader_warning)

        label_settings_bootloader_title = Gtk.Label(xalign=0.5, yalign=0.5)
        label_settings_bootloader_title.set_markup("Current Bootloader")

        self.label_settings_bootloader_file = Gtk.Label(xalign=0.5, yalign=0.5)
        self.label_settings_bootloader_file.set_text("GRUB config file")

        self.button_override_bootloader = Gtk.Button(
            label="Override bootloader settings"
        )
        self.button_override_bootloader.connect("clicked", self.on_override_clicked)
        self.hbox_bootloader_override_row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=20
        )
        self.hbox_bootloader_override_row.set_name("box_row")
        self.hbox_bootloader_override_row.append(self.button_override_bootloader)

        boot_loaders = {0: "grub", 1: "systemd-boot"}

        # Set up the factory
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_factory_setup)
        factory.connect("bind", self._on_factory_bind)

        self.model = Gio.ListStore(item_type=Bootloader)
        for bootloader_id in boot_loaders.keys():
            self.model.append(
                Bootloader(
                    id=bootloader_id,
                    name=boot_loaders[bootloader_id],
                )
            )

        self.dropdown_bootloader = Gtk.DropDown(
            model=self.model, factory=factory, hexpand=True
        )

        self.dropdown_bootloader.set_sensitive(False)

        self.selected_bootloader = None

        self._bootloader_grub_config = "/boot/grub/grub.cfg"

        row_settings_override_grub = Gtk.ListBoxRow()
        row_settings_grub = Gtk.ListBoxRow()
        self.listbox_settings_adv.append(row_settings_grub)

        self.listbox_settings_adv.append(row_settings_override_grub)

        self.text_entry_bootloader_file.connect("changed", self.on_entry_changed)
        self.text_entry_bootloader_file.props.editable = False
        text_entry_buffer_file = Gtk.EntryBuffer()

        if self.manager_gui.bootloader_grub_cfg is not None:
            text_entry_buffer_file.set_text(
                self.manager_gui.bootloader_grub_cfg,
                len(self.manager_gui.bootloader_grub_cfg),
            )
        else:
            text_entry_buffer_file.set_text(
                self._bootloader_grub_config,
                len(self._bootloader_grub_config),
            )

        self.text_entry_bootloader_file.set_buffer(text_entry_buffer_file)
        self.text_entry_bootloader_file.set_halign(Gtk.Align.END)
        self.text_entry_bootloader_file.set_sensitive(False)

        label_grub_file_path = Gtk.Label(xalign=0.5, yalign=0.5)
        label_grub_file_path.set_markup("Grub file path")

        self.hbox_bootloader_grub_row.append(label_grub_file_path)
        self.hbox_bootloader_grub_row.append(self.text_entry_bootloader_file)

        row_settings_grub.set_child(self.hbox_bootloader_grub_row)

        if manager_gui.bootloader == "grub":
            self.dropdown_bootloader.set_selected(0)
            self.selected_bootloader = 0
            self.hbox_bootloader_grub_row.set_visible(True)

            row_settings_override_grub.set_child(self.hbox_bootloader_override_row)

        if manager_gui.bootloader == "systemd-boot":

            self.selected_bootloader = 1

            self.dropdown_bootloader.set_selected(1)
            row_settings_override_systemd = Gtk.ListBoxRow()
            self.listbox_settings_adv.append(row_settings_override_systemd)
            row_settings_override_systemd.set_child(self.hbox_bootloader_override_row)

            self.hbox_bootloader_grub_row.set_visible(False)

        self.dropdown_bootloader.connect(
            "notify::selected-item", self._on_selected_item_notify
        )

        hbox_bootloader_row.append(label_settings_bootloader_title)
        hbox_bootloader_row.append(self.dropdown_bootloader)

        row_settings_adv.set_child(hbox_bootloader_row)

        vbox_settings_adv.append(label_bootloader)
        vbox_settings_adv.append(hbox_warning)
        vbox_settings_adv.append(self.listbox_settings_adv)

        listbox_settings_cache = Gtk.ListBox()
        listbox_settings_cache.set_selection_mode(Gtk.SelectionMode.NONE)

        row_settings_cache = Gtk.ListBoxRow()
        listbox_settings_cache.append(row_settings_cache)

        label_cache = Gtk.Label(xalign=0, yalign=0)
        label_cache.set_markup("<b>Refresh data from Arch Linux Archive</b>")

        label_cache_update = Gtk.Label(xalign=0.5, yalign=0.5)
        label_cache_update.set_text("Update (this will take some time)")

        self.label_cache_update_status = Gtk.Label(xalign=0.5, yalign=0.5)

        switch_refresh_cache = Gtk.Switch()
        switch_refresh_cache.connect("state-set", self.refresh_toggle)

        label_cache_file = Gtk.Label(xalign=0, yalign=0)
        label_cache_file.set_text(fn.cache_file)
        label_cache_file.set_selectable(True)

        self.label_cache_lastmodified = Gtk.Label(xalign=0, yalign=0)
        self.label_cache_lastmodified.set_markup(
            "Last modified date: <b>%s</b>" % fn.get_cache_last_modified()
        )

        hbox_switch_row.append(label_cache_update)
        hbox_switch_row.append(switch_refresh_cache)
        hbox_switch_row.append(self.label_cache_update_status)

        row_settings_cache.set_child(hbox_switch_row)

        label_logfile = Gtk.Label(xalign=0, yalign=0)
        label_logfile.set_markup("<b>Log file</b>")

        button_logfile = Gtk.Button(label="Open event log file")
        button_logfile.connect("clicked", self.on_button_logfile_clicked)

        label_logfile_location = Gtk.Label(xalign=0.5, yalign=0.5)
        label_logfile_location.set_text(fn.event_log_file)
        label_logfile_location.set_selectable(True)
        hbox_log_row.append(button_logfile)
        hbox_log_row.append(label_logfile_location)

        listbox_settings_log = Gtk.ListBox()
        listbox_settings_log.set_selection_mode(Gtk.SelectionMode.NONE)

        row_settings_log = Gtk.ListBoxRow()
        listbox_settings_log.append(row_settings_log)

        row_settings_log.set_child(hbox_log_row)

        vbox_settings_adv.append(label_cache)
        vbox_settings_adv.append(self.label_cache_lastmodified)
        vbox_settings_adv.append(label_cache_file)
        vbox_settings_adv.append(listbox_settings_cache)
        vbox_settings_adv.append(label_logfile)
        vbox_settings_adv.append(listbox_settings_log)

        stack.add_titled(vbox_settings_adv, "Advanced Settings", "Advanced")
        stack.add_titled(vbox_settings, "Kernels", "Kernel versions")

    def populate_official_kernels(self):
        self.label_loading_kernels.hide()
        for official_kernel in fn.supported_kernels_dict:
            row_official_kernel = Gtk.ListBoxRow()
            hbox_row_official = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)

            hbox_row_official_kernel_row = Gtk.Box(
                orientation=Gtk.Orientation.HORIZONTAL, spacing=10
            )

            hbox_row_official.set_name("box_row")

            label_kernel = Gtk.Label(xalign=0, yalign=0)
            label_kernel.set_text("%s" % official_kernel)

            label_kernel_version = Gtk.Label(xalign=0, yalign=0)
            label_kernel_version.set_text("%s" % self.kernel_versions[official_kernel])

            hbox_row_official_kernel_row.append(label_kernel)
            hbox_row_official_kernel_row.append(label_kernel_version)

            hbox_row_official.append(hbox_row_official_kernel_row)

            row_official_kernel.set_child(hbox_row_official)

            self.listbox_official_kernels.append(row_official_kernel)

    def check_official_version_queue(self):
        while True:
            self.kernel_versions = self.kernel_versions_queue.get()

            if self.kernel_versions is not None and len(self.kernel_versions) > 0:
                break

        self.kernel_versions_queue.task_done()

        GLib.idle_add(self.populate_official_kernels, priority=GLib.PRIORITY_DEFAULT)

    def on_entry_changed(self, entry):
        if (
            len(entry.get_text()) > 0
            and entry.get_text() != self.manager_gui.bootloader_grub_cfg
        ):
            self.button_override_bootloader.get_child().set_text("Apply changes")

    def _on_factory_setup(self, factory, list_item):
        label = Gtk.Label()
        list_item.set_child(label)

    def _on_factory_bind(self, factory, list_item):
        label = list_item.get_child()
        bootloader = list_item.get_item()
        label.set_text(bootloader.name)

    def on_override_clicked(self, widget):
        if self.button_override_bootloader.get_child().get_text() == "Apply changes":
            # validate bootloader
            if self.dropdown_bootloader.get_selected() == 1:
                if not os.path.exists(
                    "/sys/firmware/efi/fw_platform_size"
                ) or not os.path.exists("/sys/firmware/efi/efivars"):
                    mw = MessageWindow(
                        title="Legacy boot detected",
                        message="Cannot select systemd-boot, UEFI boot mode is not available",
                        transient_for=self,
                        detailed_message=False,
                    )

                    mw.present()
                    self.dropdown_bootloader.set_selected(0)
                    return

            config_data = fn.read_config(self)

            if config_data is not None:
                # grub

                if (
                    self.dropdown_bootloader.get_selected() == 0
                    and len(
                        self.text_entry_bootloader_file.get_buffer().get_text().strip()
                    )
                    > 0
                ):
                    if fn.os.path.exists(
                        self.text_entry_bootloader_file.get_buffer().get_text().strip()
                    ):
                        if "bootloader" in config_data.keys():
                            config_data.remove("bootloader")

                        bootloader = fn.tomlkit.table(True)
                        bootloader.update({"name": "grub"})
                        bootloader.update(
                            {
                                "grub_config": self.text_entry_bootloader_file.get_buffer()
                                .get_text()
                                .strip()
                            }
                        )

                        config_data.append("bootloader", bootloader)

                        if fn.update_config(config_data, "grub") is True:
                            self.manager_gui.bootloader = "grub"
                            self.manager_gui.bootloader_grub_cfg = (
                                self.text_entry_bootloader_file.get_buffer()
                                .get_text()
                                .strip()
                            )
                    else:
                        mw = MessageWindow(
                            title="Grub config file",
                            message="The specified Grub config file %s does not exist"
                            % self.text_entry_bootloader_file.get_buffer()
                            .get_text()
                            .strip(),
                            transient_for=self,
                            detailed_message=False,
                        )

                        mw.present()
                        self.button_override_bootloader.get_child().set_text(
                            "Override bootloader settings"
                        )

                elif (
                    self.dropdown_bootloader.get_selected() == 1
                    and self.selected_bootloader
                    != self.dropdown_bootloader.get_selected()
                ):
                    if "bootloader" in config_data.keys():
                        config_data.remove("bootloader")

                    self.hbox_bootloader_grub_row.set_visible(True)

                    bootloader = fn.tomlkit.table(True)
                    bootloader.update({"name": "systemd-boot"})

                    config_data.append("bootloader", bootloader)

                    if fn.update_config(config_data, "systemd-boot") is True:
                        self.manager_gui.bootloader = "systemd-boot"

        else:
            self.dropdown_bootloader.set_sensitive(True)

            if self.dropdown_bootloader.get_selected() == 0:
                self.hbox_bootloader_grub_row.set_visible(True)
                self.text_entry_bootloader_file.set_sensitive(True)
                self.text_entry_bootloader_file.props.editable = True
            elif self.dropdown_bootloader.get_selected() == 1:
                self.hbox_bootloader_grub_row.set_visible(False)

    def _on_selected_item_notify(self, dd, _):
        if self.dropdown_bootloader.get_selected() != self.selected_bootloader:
            self.button_override_bootloader.get_child().set_text("Apply changes")
        else:
            self.button_override_bootloader.get_child().set_text(
                "Override bootloader settings"
            )
        if dd.get_selected() == 1:
            if self.text_entry_bootloader_file is not None:
                self.hbox_bootloader_grub_row.set_visible(False)
        elif dd.get_selected() == 0:
            if self.text_entry_bootloader_file is not None:
                self.hbox_bootloader_grub_row.set_visible(True)
                self.text_entry_bootloader_file.set_sensitive(True)
                self.text_entry_bootloader_file.props.editable = True

    def monitor_kernels_queue(self, switch):
        while True:
            if len(fn.fetched_kernels_dict) > 0:
                self.manager_gui.official_kernels = self.queue_kernels.get()
                self.queue_kernels.task_done()
                self.refreshed = True
                if self.manager_gui.official_kernels is not None:
                    switch.set_sensitive(False)
                    self.update_official_list()
                    self.update_community_list()
                    self.update_timestamp()
                    self.label_cache_update_status.set_markup(
                        "<b>Cache refresh completed</b>"
                    )
                else:
                    self.label_cache_update_status.set_markup(
                        "<b>Cache refresh failed</b>"
                    )
                    self.refreshed = False
                    self.update_timestamp()
                break
            else:
                self.label_cache_update_status.set_markup(
                    "<b>Cache refresh in progress</b>"
                )
                # fn.time.sleep(0.3)

    def refresh_toggle(self, switch, data):
        if switch.get_active() is True:
            # refresh cache
            fn.logger.info("Refreshing cache file %s" % fn.cache_file)
            switch.set_sensitive(False)

            try:
                th_refresh_cache = fn.Thread(
                    name=fn.thread_refresh_cache,
                    target=fn.refresh_cache,
                    args=(self,),
                    daemon=True,
                )

                th_refresh_cache.start()

                # monitor queue
                fn.Thread(
                    target=self.monitor_kernels_queue, daemon=True, args=(switch,)
                ).start()

            except Exception as e:
                fn.logger.error("Exception in refresh_toggle(): %s" % e)
                self.label_cache_update_status.set_markup("<b>Cache refresh failed</b>")

    def update_timestamp(self):
        if self.refreshed is True:
            self.label_cache_lastmodified.set_markup(
                "Last modified date: <span foreground='orange'><b>%s</b></span>"
                % fn.get_cache_last_modified()
            )
        else:
            self.label_cache_lastmodified.set_markup(
                "Last modified date: <span foreground='orange'><b>%s</b></span>"
                % "Refresh failed"
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

    def on_close_clicked(self, widget):
        self.destroy()

    def on_button_logfile_clicked(self, widget):
        try:
            cmd = ["sudo", "-u", fn.sudo_username, "xdg-open", fn.event_log_file]
            fn.subprocess.Popen(
                cmd,
                shell=False,
                stdout=fn.subprocess.PIPE,
                stderr=fn.subprocess.STDOUT,
            )

        except Exception as e:
            fn.logger.error("Exception in on_button_logfile_clicked(): %s" % e)


class Bootloader(GObject.Object):
    __gtype_name__ = "Bootloader"

    def __init__(self, id, name):
        super().__init__()

        self.id = id
        self.name = name

    @GObject.Property
    def bootloader_id(self):
        return self.id

    @GObject.Property
    def bootloader_name(self):
        return self.name
