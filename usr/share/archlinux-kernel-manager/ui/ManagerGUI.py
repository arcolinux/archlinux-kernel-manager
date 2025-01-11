import gi
import os
from ui.MenuButton import MenuButton
from ui.Stack import Stack
from ui.KernelStack import KernelStack
from ui.FlowBox import FlowBox, FlowBoxInstalled
from ui.AboutDialog import AboutDialog
from ui.SplashScreen import SplashScreen
from ui.MessageWindow import MessageWindow
from ui.SettingsWindow import SettingsWindow
import libs.functions as fn

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio, Gdk, GLib


base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class ManagerGUI(Gtk.ApplicationWindow):
    def __init__(self, app_name, default_context, app_version, **kwargs):
        super().__init__(**kwargs)

        self.default_context = default_context

        self.app_version = app_version

        if self.app_version == "${app_version}":
            self.app_version = "dev"

        self.set_title(app_name)
        self.set_resizable(True)
        self.set_default_size(950, 650)

        # get list of kernels from the arch archive website, aur, then cache
        self.official_kernels = []
        self.community_kernels = []

        # splashscreen queue for threading
        self.queue_load_progress = fn.Queue()

        # official kernels queue for threading
        self.queue_kernels = fn.Queue()

        # community kernels queue for threading
        self.queue_community_kernels = fn.Queue()

        self.splash_screen = SplashScreen(app_name)

        try:
            fn.Thread(
                target=self.wait_for_gui_load,
                daemon=True,
            ).start()
        except Exception as e:
            fn.logger.error(e)

        while self.default_context.pending():
            fn.time.sleep(0.1)
            self.default_context.iteration(True)

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

        # while self.default_context.pending():
        #     fn.time.sleep(0.1)
        #     self.default_context.iteration(True)

        self.bootloader = None
        self.bootloader_grub_cfg = None

        # self.bootloader = fn.get_boot_loader()

        config_data = fn.setup_config(self)

        fn.logger.info("Version = %s" % self.app_version)
        fn.logger.info("Distro = %s" % fn.distro.id())

        if "bootloader" in config_data.keys():
            if config_data["bootloader"]["name"] is not None:
                self.bootloader = config_data["bootloader"]["name"].lower()

                if self.bootloader == "grub":
                    if config_data["bootloader"]["grub_config"] is not None:
                        self.bootloader_grub_cfg = config_data["bootloader"][
                            "grub_config"
                        ]
                elif self.bootloader != "systemd-boot" or self.bootloader != "grub":
                    fn.logger.warning(
                        "Invalid bootloader config found it should only be systemd-boot or grub"
                    )

                    fn.logger.warning("Using bootctl to determine current bootloader")
                    self.bootloader = None

        if self.bootloader is not None or self.bootloader_grub_cfg is not None:
            fn.logger.info("User provided bootloader options read from config file")
            fn.logger.info("User bootloader option = %s " % self.bootloader)
            if self.bootloader_grub_cfg is not None:
                fn.logger.info(
                    "User bootloader Grub config  = %s " % self.bootloader_grub_cfg
                )
        else:
            # no config setting found for bootloader use default method
            self.bootloader = fn.get_boot_loader()
            if self.bootloader == "grub":
                self.bootloader_grub_cfg = "/boot/grub/grub.cfg"

        if self.bootloader is not None:
            fn.create_cache_dir()
            fn.create_log_dir()
            fn.get_pacman_repos()

            self.stack = Stack(transition_type="OVER_DOWN")
            self.kernel_stack = KernelStack(self)

            header_bar = Gtk.HeaderBar()

            label_title = Gtk.Label(xalign=0.5, yalign=0.5)
            label_title.set_markup("<b>%s</b>" % app_name)

            header_bar.set_title_widget(label_title)
            header_bar.set_show_title_buttons(True)

            self.set_titlebar(header_bar)

            menu_outerbox = Gtk.Box(spacing=6, orientation=Gtk.Orientation.VERTICAL)
            header_bar.pack_end(menu_outerbox)

            menu_outerbox.show()

            menubutton = MenuButton()

            menu_outerbox.append(menubutton)

            menubutton.show()

            action_about = Gio.SimpleAction(name="about")
            action_about.connect("activate", self.on_about)

            action_settings = Gio.SimpleAction(name="settings")
            action_settings.connect("activate", self.on_settings, fn)

            self.add_action(action_settings)

            self.add_action(action_about)

            action_refresh = Gio.SimpleAction(name="refresh")
            action_refresh.connect("activate", self.on_refresh)

            self.add_action(action_refresh)

            action_quit = Gio.SimpleAction(name="quit")
            action_quit.connect("activate", self.on_quit)

            self.add_action(action_quit)

            # add shortcut keys

            event_controller_key = Gtk.EventControllerKey.new()
            event_controller_key.connect("key-pressed", self.key_pressed)

            self.add_controller(event_controller_key)

            # overlay = Gtk.Overlay()
            # self.set_child(child=overlay)

            self.vbox = Gtk.Box.new(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            self.vbox.set_name("main")

            self.set_child(child=self.vbox)

            self.vbox.append(self.notify_revealer)

            self.installed_kernels = fn.get_installed_kernels()
            if self.installed_kernels is not None:
                fn.logger.info("Installed kernels = %s" % len(self.installed_kernels))

            self.active_kernel = fn.get_active_kernel()

            self.refresh_cache = False

            self.refresh_cache = fn.get_latest_kernel_updates(self)

            self.start_get_kernels_threads()

            self.load_kernels_gui()

            # validate bootloader
            if self.bootloader_grub_cfg and not os.path.exists(
                self.bootloader_grub_cfg
            ):
                mw = MessageWindow(
                    title="Grub config file not found",
                    message=f"The specified Grub config file: {self.bootloader_grub_cfg} does not exist\n"
                    f"This will cause an issue when updating the bootloader\n"
                    f"Update the configuration file/use the Advanced Settings to change this\n",
                    detailed_message=False,
                    transient_for=self,
                )

                mw.present()
            if self.bootloader == "systemd-boot":
                if not os.path.exists(
                    "/sys/firmware/efi/fw_platform_size"
                ) or not os.path.exists("/sys/firmware/efi/efivars"):
                    mw = MessageWindow(
                        title="Legacy boot detected",
                        message=f"Cannot select systemd-boot, UEFI boot mode is not available\n"
                        f"Update the configuration file\n"
                        f"Or use the Advanced Settings to change this\n",
                        detailed_message=False,
                        transient_for=self,
                    )

                    mw.present()

        else:
            fn.logger.error("Failed to set bootloader, application closing - Refind is not supported")
            fn.sys.exit(1)

    def key_pressed(self, keyval, keycode, state, userdata):
        shortcut = Gtk.accelerator_get_label(
            keycode, keyval.get_current_event().get_modifier_state()
        )

        # quit application
        if shortcut in ("Ctrl+Q", "Ctrl+Mod2+Q"):
            self.destroy()

    def open_settings(self, fn):
        settings_win = SettingsWindow(fn, self)
        settings_win.present()

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

    def start_get_kernels_threads(self):
        if self.refresh_cache is False:
            fn.logger.info("Starting get official Linux kernels thread")
            try:
                fn.Thread(
                    name=fn.thread_get_kernels,
                    target=fn.get_official_kernels,
                    daemon=True,
                    args=(self,),
                ).start()

            except Exception as e:
                fn.logger.error("Exception in thread fn.get_official_kernels(): %s" % e)
            finally:
                self.official_kernels = self.queue_kernels.get()
                self.queue_kernels.task_done()

        else:
            self.official_kernels = self.queue_kernels.get()
            self.queue_kernels.task_done()

    # =====================================================
    #               PACMAN DB SYNC
    # =====================================================

    def pacman_db_sync(self):
        sync_err = fn.sync_package_db()

        if sync_err is not None:
            # fn.logger.error("Pacman db synchronization failed")

            GLib.idle_add(
                self.show_sync_window,
                sync_err,
                priority=GLib.PRIORITY_DEFAULT,
            )

            return False

        else:
            fn.logger.info("Pacman DB synchronization completed")
            return True

    def show_sync_window(self, sync_err):
        mw = MessageWindow(
            title="Error - Pacman db synchronization",
            message=f"Pacman db synchronization failed\n"
            f"Failed to run 'pacman -Syu'\n"
            f"{sync_err}\n",
            transient_for=self,
            detailed_message=True,
        )

        mw.present()

    # keep splash screen open, until main gui is loaded
    def wait_for_gui_load(self):
        while True:
            if fn.logger.getEffectiveLevel() == 10:
                fn.logger.debug("Waiting for GUI to load ..")

            # fn.time.sleep(0.2)
            status = self.queue_load_progress.get()
            try:

                if fn.logger.getEffectiveLevel() == 10:
                    fn.logger.debug("Status = %s" % status)

                if status == 1:
                    if fn.logger.getEffectiveLevel() == 10:
                        fn.logger.debug("Destroying splashscreen")

                    GLib.idle_add(
                        self.splash_screen.destroy,
                        priority=GLib.PRIORITY_DEFAULT,
                    )
                    break
            except Exception as e:
                fn.logger.error("Exception in wait_for_gui_load(): %s" % e)
            finally:
                self.queue_load_progress.task_done()

    def on_settings(self, action, param, fn):
        self.open_settings(fn)

    def on_about(self, action, param):
        about_dialog = AboutDialog(self)
        about_dialog.present()

    def on_refresh(self, action, param):
        fn.backup_config(self)
        fn.overwrite_setup_config(self)
        if not fn.is_thread_alive(fn.thread_refresh_ui):
            fn.Thread(
                name=fn.thread_refresh_ui,
                target=self.refresh_ui,
                daemon=True,
            ).start()

    def refresh_ui(self):
        if fn.logger.getEffectiveLevel() == 10:
            fn.logger.debug("Refreshing UI")

        self.label_notify_revealer.set_text("Refreshing UI started")
        GLib.idle_add(
            self.reveal_notify,
            priority=GLib.PRIORITY_DEFAULT,
        )
        fn.pacman_repos_list = []
        fn.get_pacman_repos()

        fn.cached_kernels_list = []
        fn.community_kernels_list = []

        self.official_kernels = None

        self.community_kernels = None

        self.installed_kernels = None

        self.start_get_kernels_threads()

        if self.pacman_db_sync() is False:
            fn.logger.error("Pacman DB synchronization failed")
        else:
            if fn.logger.getEffectiveLevel() == 10:
                fn.logger.debug("Adding community kernels to UI")

            try:
                thread_get_community_kernels = fn.Thread(
                    name=fn.thread_get_community_kernels,
                    target=fn.get_community_kernels,
                    daemon=True,
                    args=(self,),
                )

                thread_get_community_kernels.start()

            except Exception as e:
                fn.logger.error("Exception in thread_get_community_kernels: %s" % e)
            finally:
                self.community_kernels = self.queue_community_kernels.get()
                self.queue_community_kernels.task_done()

        self.installed_kernels = fn.get_installed_kernels()

        self.label_notify_revealer.set_text("Refreshing official kernels")
        GLib.idle_add(
            self.reveal_notify,
            priority=GLib.PRIORITY_DEFAULT,
        )

        GLib.idle_add(
            self.kernel_stack.add_official_kernels_to_stack,
            True,
            priority=GLib.PRIORITY_DEFAULT,
        )

        self.label_notify_revealer.set_text("Refreshing community kernels")
        GLib.idle_add(
            self.reveal_notify,
            priority=GLib.PRIORITY_DEFAULT,
        )

        GLib.idle_add(
            self.kernel_stack.add_community_kernels_to_stack,
            True,
            priority=GLib.PRIORITY_DEFAULT,
        )

        self.label_notify_revealer.set_text("Refreshing installed kernels")
        GLib.idle_add(
            self.reveal_notify,
            priority=GLib.PRIORITY_DEFAULT,
        )

        GLib.idle_add(
            self.kernel_stack.add_installed_kernels_to_stack,
            True,
            priority=GLib.PRIORITY_DEFAULT,
        )

        while self.default_context.pending():
            if fn.logger.getEffectiveLevel() == 10:
                fn.logger.debug("Waiting for UI loop")
            fn.time.sleep(0.3)
            self.default_context.iteration(False)

        # fn.time.sleep(0.5)
        if fn.logger.getEffectiveLevel() == 10:
            fn.logger.debug("Refresh UI completed")

        self.label_notify_revealer.set_text("Refreshing UI completed")
        GLib.idle_add(
            self.reveal_notify,
            priority=GLib.PRIORITY_DEFAULT,
        )

    def on_quit(self, action, param):
        self.destroy()
        fn.logger.info("Application quit")

    def on_button_quit_response(self, widget):
        self.destroy()
        fn.logger.info("Application quit")

    def load_kernels_gui(self):
        self.queue_load_progress.put(0)
        hbox_sep = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        hsep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        hbox_sep.append(hsep)

        # handle error here with message
        if self.official_kernels is None:
            fn.logger.error("Failed to retrieve kernel list")
            self.queue_load_progress.put(1)

        stack_sidebar = Gtk.StackSidebar()
        stack_sidebar.set_name("stack_sidebar")
        stack_sidebar.set_stack(self.stack)

        hbox_stack_sidebar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        hbox_stack_sidebar.set_name("hbox_stack_sidebar")
        hbox_stack_sidebar.append(stack_sidebar)
        hbox_stack_sidebar.append(self.stack)

        self.vbox.append(hbox_stack_sidebar)

        button_quit = Gtk.Button.new_with_label("Quit")
        # button_quit.set_size_request(100, 30)
        button_quit.connect(
            "clicked",
            self.on_button_quit_response,
        )

        btn_context = button_quit.get_style_context()
        btn_context.add_class("destructive-action")

        grid_bottom_panel = Gtk.Grid()
        grid_bottom_panel.set_halign(Gtk.Align.END)
        grid_bottom_panel.set_row_homogeneous(True)

        grid_bottom_panel.attach(button_quit, 0, 1, 1, 1)

        self.vbox.append(grid_bottom_panel)

        self.textbuffer = Gtk.TextBuffer()

        self.textview = Gtk.TextView()
        self.textview.set_property("editable", False)
        self.textview.set_property("monospace", True)

        self.textview.set_vexpand(True)
        self.textview.set_hexpand(True)

        self.textview.set_buffer(self.textbuffer)

        fn.logger.info("Creating kernel UI")

        # add official kernel flowbox
        if fn.logger.getEffectiveLevel() == 10:
            fn.logger.debug("Adding official kernels to UI")

        self.queue_load_progress.put(0)

        self.kernel_stack.add_official_kernels_to_stack(reload=False)

        # fn.logger.debug("Adding community kernels to UI")
        # self.kernel_stack.add_community_kernels_to_stack(reload=False)

        fn.logger.info("Starting pacman db synchronization")

        if self.pacman_db_sync() is False:
            fn.logger.error("Pacman DB synchronization failed")

        else:
            if fn.logger.getEffectiveLevel() == 10:
                fn.logger.debug("Adding community kernels to UI")

            try:
                thread_get_community_kernels = fn.Thread(
                    name=fn.thread_get_community_kernels,
                    target=fn.get_community_kernels,
                    daemon=True,
                    args=(self,),
                )

                thread_get_community_kernels.start()

            except Exception as e:
                fn.logger.error("Exception in thread_get_community_kernels: %s" % e)
            finally:
                self.community_kernels = self.queue_community_kernels.get()
                self.queue_community_kernels.task_done()

                self.kernel_stack.add_community_kernels_to_stack(reload=False)

        if fn.logger.getEffectiveLevel() == 10:
            fn.logger.debug("Sending signal to destroy splashscreen")

        # signal to destroy splash screen
        self.queue_load_progress.put(1)

        if fn.logger.getEffectiveLevel() == 10:
            fn.logger.debug("Adding installed kernels to UI")

        self.kernel_stack.add_installed_kernels_to_stack(reload=False)

        fn.logger.info("Application started")

        # while self.default_context.pending():
        #     if fn.logger.getEffectiveLevel() == 10:
        #         fn.logger.debug("Waiting for UI loop")
        #     self.default_context.iteration(False)
        #     fn.time.sleep(0.3)
