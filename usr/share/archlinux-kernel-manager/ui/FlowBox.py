import datetime

import gi
import os
import libs.functions as fn
from ui.ProgressWindow import ProgressWindow
from ui.MessageWindow import MessageWindow

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio, GLib

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class FlowBox(Gtk.FlowBox):
    def __init__(
        self,
        kernel,
        active_kernel,
        manager_gui,
        source,
    ):
        super(FlowBox, self).__init__()

        self.manager_gui = manager_gui

        # self.set_row_spacing(1)
        # self.set_column_spacing(1)
        # self.set_name("hbox_kernel")
        # self.set_activate_on_single_click(True)
        # self.connect("child-activated", self.on_child_activated)
        self.set_valign(Gtk.Align.START)

        self.set_selection_mode(Gtk.SelectionMode.NONE)

        # self.set_homogeneous(True)

        self.set_max_children_per_line(2)
        self.set_min_children_per_line(2)
        self.kernel_count = 0

        self.active_kernel_found = False
        self.kernels = []

        self.kernel = kernel
        self.source = source

        if self.source == "official":
            self.flowbox_official()

        if self.source == "community":
            self.flowbox_community()

    def flowbox_community(self):
        for community_kernel in self.kernel:
            self.kernels.append(community_kernel)

            self.kernel_count += 1

        if len(self.kernels) > 0:
            installed = False

            for cache in self.kernels:
                fb_child = Gtk.FlowBoxChild()
                fb_child.set_name(
                    "%s %s %s" % (cache.name, cache.version, cache.repository)
                )

                vbox_kernel_widgets = Gtk.Box(
                    orientation=Gtk.Orientation.VERTICAL, spacing=0
                )
                vbox_kernel_widgets.set_name("vbox_kernel_widgets")
                vbox_kernel_widgets.set_homogeneous(True)

                switch_kernel = Gtk.Switch()
                switch_kernel.set_halign(Gtk.Align.START)

                hbox_kernel_switch = Gtk.Box(
                    orientation=Gtk.Orientation.HORIZONTAL, spacing=0
                )

                hbox_kernel_switch.append(switch_kernel)

                label_kernel_size = Gtk.Label(xalign=0, yalign=0)
                label_kernel_size.set_name("label_kernel_flowbox")

                label_kernel_name = Gtk.Label(xalign=0, yalign=0)
                label_kernel_name.set_name("label_kernel_version")
                label_kernel_name.set_markup(
                    "<b>%s</b> %s <i>%s</i>"
                    % (cache.name, cache.version, cache.repository)
                )
                label_kernel_name.set_selectable(True)

                vbox_kernel_widgets.append(label_kernel_name)

                tux_icon = Gtk.Picture.new_for_file(
                    file=Gio.File.new_for_path(
                        os.path.join(base_dir, "images/48x48/akm-tux.png")
                    )
                )
                tux_icon.set_can_shrink(True)

                for installed_kernel in self.manager_gui.installed_kernels:
                    if "{}-{}".format(
                        installed_kernel.name, installed_kernel.version
                    ) == "{}-{}".format(cache.name, cache.version):
                        installed = True

                    if cache.name == installed_kernel.name:
                        if (
                            cache.version > installed_kernel.version
                            or cache.version != installed_kernel.version
                        ):
                            fn.logger.info(
                                "Kernel upgrade available - %s %s"
                                % (cache.name, cache.version)
                            )

                            tux_icon = Gtk.Picture.new_for_file(
                                file=Gio.File.new_for_path(
                                    os.path.join(
                                        base_dir, "images/48x48/akm-update.png"
                                    )
                                )
                            )
                            tux_icon.set_can_shrink(True)

                            label_kernel_name.set_markup(
                                "<b>*%s</b> %s <i>%s</i>"
                                % (cache.name, cache.version, cache.repository)
                            )

                if installed is True:
                    switch_kernel.set_state(True)
                    switch_kernel.set_active(True)

                else:
                    switch_kernel.set_state(False)
                    switch_kernel.set_active(False)

                tux_icon.set_content_fit(content_fit=Gtk.ContentFit.SCALE_DOWN)
                tux_icon.set_halign(Gtk.Align.START)

                installed = False
                switch_kernel.connect("state-set", self.kernel_toggle_state, cache)

                hbox_kernel = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
                hbox_kernel.set_name("hbox_kernel")

                label_kernel_size.set_text("%sM" % str(cache.install_size))

                vbox_kernel_widgets.append(label_kernel_size)

                label_kernel_build_date = Gtk.Label(xalign=0, yalign=0)
                label_kernel_build_date.set_name("label_kernel_flowbox")
                label_kernel_build_date.set_text(cache.build_date)

                vbox_kernel_widgets.append(label_kernel_build_date)

                vbox_kernel_widgets.append(hbox_kernel_switch)

                hbox_kernel.append(tux_icon)
                hbox_kernel.append(vbox_kernel_widgets)

                fb_child.set_child(hbox_kernel)

                self.append(fb_child)

    def flowbox_official(self):
        for official_kernel in self.manager_gui.official_kernels:
            if official_kernel.name == self.kernel:
                self.kernels.append(official_kernel)
                self.kernel_count += 1

        if len(self.kernels) > 0:
            installed = False

            latest = sorted(self.kernels)[:-1][0]

            for cache in sorted(self.kernels):
                fb_child = Gtk.FlowBoxChild()
                fb_child.set_name("%s %s" % (cache.name, cache.version))
                if cache == latest:
                    tux_icon = Gtk.Picture.new_for_file(
                        file=Gio.File.new_for_path(
                            os.path.join(base_dir, "images/48x48/akm-new.png")
                        )
                    )

                else:
                    tux_icon = Gtk.Picture.new_for_file(
                        file=Gio.File.new_for_path(
                            os.path.join(base_dir, "images/48x48/akm-tux.png")
                        )
                    )

                tux_icon.set_content_fit(content_fit=Gtk.ContentFit.SCALE_DOWN)
                tux_icon.set_halign(Gtk.Align.START)

                vbox_kernel_widgets = Gtk.Box(
                    orientation=Gtk.Orientation.VERTICAL, spacing=0
                )
                vbox_kernel_widgets.set_homogeneous(True)

                hbox_kernel_switch = Gtk.Box(
                    orientation=Gtk.Orientation.HORIZONTAL, spacing=0
                )

                switch_kernel = Gtk.Switch()
                switch_kernel.set_halign(Gtk.Align.START)

                hbox_kernel_switch.append(switch_kernel)

                label_kernel_version = Gtk.Label(xalign=0, yalign=0)
                label_kernel_version.set_name("label_kernel_version")
                label_kernel_version.set_selectable(True)

                label_kernel_size = Gtk.Label(xalign=0, yalign=0)
                label_kernel_size.set_name("label_kernel_flowbox")

                if self.manager_gui.installed_kernels is None:
                    self.manager_gui.installed_kernels = fn.get_installed_kernels()

                for installed_kernel in self.manager_gui.installed_kernels:
                    if (
                        "{}-{}".format(installed_kernel.name, installed_kernel.version)
                        == cache.version
                    ):
                        installed = True

                if installed is True:
                    switch_kernel.set_state(True)
                    switch_kernel.set_active(True)

                else:
                    switch_kernel.set_state(False)
                    switch_kernel.set_active(False)

                installed = False
                switch_kernel.connect("state-set", self.kernel_toggle_state, cache)

                label_kernel_version.set_markup("<b>%s</b>" % cache.version)

                hbox_kernel = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
                hbox_kernel.set_name("hbox_kernel")

                label_kernel_size.set_text(cache.size)

                vbox_kernel_widgets.append(label_kernel_version)
                vbox_kernel_widgets.append(label_kernel_size)

                label_kernel_modified = Gtk.Label(xalign=0, yalign=0)
                label_kernel_modified.set_name("label_kernel_flowbox")
                label_kernel_modified.set_text(cache.last_modified)

                vbox_kernel_widgets.append(label_kernel_modified)

                vbox_kernel_widgets.append(hbox_kernel_switch)

                hbox_kernel.append(tux_icon)
                hbox_kernel.append(vbox_kernel_widgets)

                fb_child.set_child(hbox_kernel)

                self.append(fb_child)

        else:
            fn.logger.error("Failed to read in kernels.")

    def kernel_toggle_state(self, switch, data, kernel):
        fn.logger.debug(
            "Switch toggled, kernel selected = %s %s" % (kernel.name, kernel.version)
        )
        message = None
        title = None

        if fn.check_pacman_lockfile() is False:
            # switch widget is currently toggled off
            if switch.get_state() is False:  # and switch.get_active() is True:
                for inst_kernel in fn.get_installed_kernels():
                    if inst_kernel.name == kernel.name:
                        if self.source == "official":
                            if (
                                inst_kernel.version
                                > kernel.version.split("%s-" % inst_kernel.name)[1]
                            ):
                                title = "Downgrading %s kernel" % kernel.name
                            else:
                                title = "Upgrading %s kernel" % kernel.name

                        break

                if title is None:
                    title = "Kernel install"

                if self.source == "community":
                    message = "This will install <b>%s-%s</b> - Is this ok ?" % (
                        kernel.name,
                        kernel.version,
                    )
                elif self.source == "official":
                    message = (
                        "This will install <b>%s</b> - Is this ok ?" % kernel.version
                    )

                message_window = FlowBoxMessageWindow(
                    title=title,
                    message=message,
                    action="install",
                    kernel=kernel,
                    transient_for=self.manager_gui,
                    textview=self.manager_gui.textview,
                    textbuffer=self.manager_gui.textbuffer,
                    switch=switch,
                    source=self.source,
                    manager_gui=self.manager_gui,
                )
                message_window.present()
                return True

            # switch widget is currently toggled on
            # if widget.get_state() == True and widget.get_active() == False:
            if switch.get_state() is True:
                # and switch.get_active() is False:
                installed_kernels = fn.get_installed_kernels()

                if len(installed_kernels) > 1:

                    if self.source == "community":
                        message = "This will remove <b>%s-%s</b> - Is this ok ?" % (
                            kernel.name,
                            kernel.version,
                        )
                    elif self.source == "official":
                        message = (
                            "This will remove <b>%s</b> - Is this ok ?" % kernel.version
                        )

                    message_window = FlowBoxMessageWindow(
                        title="Kernel uninstall",
                        message=message,
                        action="uninstall",
                        kernel=kernel,
                        transient_for=self.manager_gui,
                        textview=self.manager_gui.textview,
                        textbuffer=self.manager_gui.textbuffer,
                        switch=switch,
                        source=self.source,
                        manager_gui=self.manager_gui,
                    )
                    message_window.present()
                    return True
                else:
                    switch.set_state(True)
                    # switch.set_active(False)
                    fn.logger.warn(
                        "You only have 1 kernel installed, and %s-%s is currently running, uninstall aborted."
                        % (kernel.name, kernel.version)
                    )
                    msg_win = MessageWindow(
                        title="Warning: Uninstall aborted",
                        message=f"You only have 1 kernel installed\n"
                        f"<b>{kernel.name} {kernel.version}</b> is currently active\n",
                        image_path="images/48x48/akm-remove.png",
                        transient_for=self.manager_gui,
                        detailed_message=False,
                    )
                    msg_win.present()
                    return True

        else:
            fn.logger.error(
                "Pacman lockfile found, is another pacman process running ?"
            )

            msg_win = MessageWindow(
                title="Warning",
                message="Pacman lockfile found, which indicates another pacman process is running",
                transient_for=self.manager_gui,
                detailed_message=False,
                image_path="images/48x48/akm-warning.png",
            )
            msg_win.present()
            return True

        # while self.manager_gui.default_context.pending():
        #     self.manager_gui.default_context.iteration(True)


class FlowBoxInstalled(Gtk.FlowBox):
    def __init__(self, installed_kernels, manager_gui, **kwargs):
        super().__init__(**kwargs)

        self.set_selection_mode(Gtk.SelectionMode.NONE)

        self.set_homogeneous(True)
        self.set_max_children_per_line(2)
        self.set_min_children_per_line(2)

        self.manager_gui = manager_gui

        for installed_kernel in installed_kernels:
            tux_icon = Gtk.Picture.new_for_file(
                file=Gio.File.new_for_path(
                    os.path.join(base_dir, "images/48x48/akm-tux.png")
                )
            )

            fb_child = Gtk.FlowBoxChild()
            fb_child.set_name(
                "%s %s" % (installed_kernel.name, installed_kernel.version)
            )

            tux_icon.set_content_fit(content_fit=Gtk.ContentFit.SCALE_DOWN)
            tux_icon.set_halign(Gtk.Align.START)

            label_installed_kernel_version = Gtk.Label(xalign=0, yalign=0)
            label_installed_kernel_version.set_name("label_kernel_version")
            label_installed_kernel_version.set_markup(
                "<b>%s</b> %s" % (installed_kernel.name, installed_kernel.version)
            )
            label_installed_kernel_version.set_selectable(True)

            hbox_installed_version = Gtk.Box(
                orientation=Gtk.Orientation.HORIZONTAL, spacing=0
            )

            hbox_installed_version.append(label_installed_kernel_version)

            label_installed_kernel_size = Gtk.Label(xalign=0, yalign=0)
            label_installed_kernel_size.set_name("label_kernel_flowbox")
            label_installed_kernel_size.set_text("%sM" % str(installed_kernel.size))

            label_installed_kernel_date = Gtk.Label(xalign=0, yalign=0)
            label_installed_kernel_date.set_name("label_kernel_flowbox")
            label_installed_kernel_date.set_text("%s" % installed_kernel.date)

            btn_uninstall_kernel = Gtk.Button.new_with_label("Remove")

            btn_context = btn_uninstall_kernel.get_style_context()
            btn_context.add_class("destructive-action")

            vbox_uninstall_button = Gtk.Box(
                orientation=Gtk.Orientation.HORIZONTAL, spacing=0
            )
            vbox_uninstall_button.set_name("box_padding_left")

            btn_uninstall_kernel.set_hexpand(False)
            btn_uninstall_kernel.set_halign(Gtk.Align.CENTER)
            btn_uninstall_kernel.set_vexpand(False)
            btn_uninstall_kernel.set_valign(Gtk.Align.CENTER)

            vbox_uninstall_button.append(btn_uninstall_kernel)

            btn_uninstall_kernel.connect(
                "clicked", self.button_uninstall_kernel, installed_kernel
            )

            vbox_kernel_widgets = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL, spacing=0
            )

            vbox_kernel_widgets.append(hbox_installed_version)
            vbox_kernel_widgets.append(label_installed_kernel_size)
            vbox_kernel_widgets.append(label_installed_kernel_date)
            vbox_kernel_widgets.append(vbox_uninstall_button)

            hbox_kernel = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
            hbox_kernel.set_name("hbox_kernel")

            hbox_kernel.append(tux_icon)
            hbox_kernel.append(vbox_kernel_widgets)

            fb_child.set_child(hbox_kernel)

            self.append(fb_child)

    def button_uninstall_kernel(self, button, installed_kernel):
        installed_kernels = fn.get_installed_kernels()

        if len(installed_kernels) > 1:
            fn.logger.info(
                "Selected kernel to remove = %s %s"
                % (installed_kernel.name, installed_kernel.version)
            )

            message_window = FlowBoxMessageWindow(
                title="Kernel uninstall",
                message="This will remove <b>%s-%s</b> - Is this ok ?"
                % (installed_kernel.name, installed_kernel.version),
                action="uninstall",
                kernel=installed_kernel,
                transient_for=self.manager_gui,
                textview=self.manager_gui.textview,
                textbuffer=self.manager_gui.textbuffer,
                switch=None,
                source=None,
                manager_gui=self.manager_gui,
            )
            message_window.present()
        else:
            fn.logger.warn(
                "You only have 1 kernel installed %s %s, uninstall aborted."
                % (installed_kernel.name, installed_kernel.version)
            )
            msg_win = MessageWindow(
                title="Warning: Uninstall aborted",
                message=f"You only have 1 kernel installed\n"
                f"<b>{installed_kernel.name} {installed_kernel.version}</b>\n",
                image_path="images/48x48/akm-remove.png",
                transient_for=self.manager_gui,
                detailed_message=False,
            )
            msg_win.present()


class FlowBoxMessageWindow(Gtk.Window):
    def __init__(
        self,
        title,
        message,
        action,
        kernel,
        textview,
        textbuffer,
        switch,
        source,
        manager_gui,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.set_title(title=title)
        self.set_modal(modal=True)
        self.set_resizable(False)
        self.set_icon_name("archlinux-kernel-manager-tux")

        header_bar = Gtk.HeaderBar()
        header_bar.set_show_title_buttons(False)

        label_title = Gtk.Label(xalign=0.5, yalign=0.5)
        label_title.set_markup("<b>%s</b>" % title)

        self.set_titlebar(header_bar)

        header_bar.set_title_widget(label_title)

        self.textview = textview
        self.textbuffer = textbuffer
        self.manager_gui = manager_gui
        self.kernel = kernel
        self.action = action
        self.switch = switch
        self.source = source

        vbox_flowbox_message = Gtk.Box.new(
            orientation=Gtk.Orientation.VERTICAL, spacing=10
        )
        vbox_flowbox_message.set_name("vbox_flowbox_message")

        self.set_child(child=vbox_flowbox_message)

        label_flowbox_message = Gtk.Label(xalign=0, yalign=0)
        label_flowbox_message.set_markup("%s" % message)
        label_flowbox_message.set_name("label_flowbox_message")

        vbox_flowbox_message.set_halign(Gtk.Align.CENTER)

        # Widgets.
        button_yes = Gtk.Button.new_with_label("Yes")
        button_yes.set_size_request(100, 30)
        button_yes.set_halign(Gtk.Align.END)
        button_yes_context = button_yes.get_style_context()
        button_yes_context.add_class("destructive-action")
        button_yes.connect("clicked", self.on_button_yes_clicked)

        button_no = Gtk.Button.new_with_label("No")
        button_no.set_size_request(100, 30)
        button_no.set_halign(Gtk.Align.END)
        button_no.connect("clicked", self.on_button_no_clicked)

        hbox_buttons = Gtk.Box.new(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        hbox_buttons.set_halign(Gtk.Align.CENTER)
        hbox_buttons.append(button_yes)
        hbox_buttons.append(button_no)

        vbox_flowbox_message.append(label_flowbox_message)
        vbox_flowbox_message.append(hbox_buttons)

    def on_button_yes_clicked(self, button):
        self.hide()
        self.destroy()
        progress_window = None
        if fn.check_pacman_lockfile() is False:
            if self.action == "uninstall":
                progress_window = ProgressWindow(
                    title="Removing kernel",
                    action="uninstall",
                    textview=self.textview,
                    textbuffer=self.textbuffer,
                    kernel=self.kernel,
                    switch=self.switch,
                    source=self.source,
                    manager_gui=self.manager_gui,
                    transient_for=self.manager_gui,
                )

            if self.action == "install":
                progress_window = ProgressWindow(
                    title="Installing kernel",
                    action="install",
                    textview=self.textview,
                    textbuffer=self.textbuffer,
                    kernel=self.kernel,
                    switch=self.switch,
                    source=self.source,
                    manager_gui=self.manager_gui,
                    transient_for=self.manager_gui,
                )
        else:
            fn.logger.error(
                "Pacman lockfile found, is another pacman process running ?"
            )

    def on_button_no_clicked(self, button):
        if self.action == "uninstall":
            if self.switch is not None:
                self.switch.set_state(True)

        elif self.action == "install":
            if self.switch is not None:
                self.switch.set_state(False)

        self.hide()
        self.destroy()

        return True
