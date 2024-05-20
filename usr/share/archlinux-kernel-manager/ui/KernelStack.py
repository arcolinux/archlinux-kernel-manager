import gi
import os
import libs.functions as fn
from ui.FlowBox import FlowBox, FlowBoxInstalled
from ui.Stack import Stack
from libs.Kernel import Kernel, InstalledKernel, CommunityKernel

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio, Gdk

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class KernelStack:
    def __init__(
        self,
        manager_gui,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.manager_gui = manager_gui
        self.flowbox_stacks = []
        self.search_entries = []

    def add_installed_kernels_to_stack(self, reload):
        vbox_header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        vbox_header.set_name("vbox_header")

        lbl_heading = Gtk.Label(xalign=0.5, yalign=0.5)
        lbl_heading.set_name("label_flowbox_message")
        lbl_heading.set_text("%s" % "Installed kernels".upper())

        lbl_padding = Gtk.Label(xalign=0.0, yalign=0.0)
        lbl_padding.set_text(" ")

        grid_banner_img = Gtk.Grid()

        image_settings = Gtk.Image.new_from_file(
            os.path.join(base_dir, "images/48x48/akm-install.png")
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

        label_installed_desc = Gtk.Label(xalign=0, yalign=0)
        label_installed_desc.set_text("Installed Linux kernel and modules")
        label_installed_desc.set_name("label_stack_desc")

        label_installed_count = Gtk.Label(xalign=0, yalign=0)

        label_installed_count.set_name("label_stack_count")

        vbox_search_entry = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)

        search_entry_installed = Gtk.SearchEntry()
        search_entry_installed.set_name("search_entry_installed")
        search_entry_installed.set_placeholder_text("Search installed kernels...")
        search_entry_installed.connect("search_changed", self.flowbox_filter_installed)

        vbox_search_entry.append(search_entry_installed)

        if reload is True:
            if self.manager_gui.vbox_installed_kernels is not None:
                for widget in self.manager_gui.vbox_installed_kernels:
                    if widget.get_name() == "label_stack_count":
                        widget.set_markup(
                            "<i>%s Installed kernels</i>"
                            % len(self.manager_gui.installed_kernels)
                        )

                    if widget.get_name() == "scrolled_window_installed":
                        self.manager_gui.vbox_installed_kernels.remove(widget)

            scrolled_window_installed = Gtk.ScrolledWindow()
            scrolled_window_installed.set_name("scrolled_window_installed")
            scrolled_window_installed.set_policy(
                Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC
            )
            scrolled_window_installed.set_propagate_natural_height(True)
            scrolled_window_installed.set_propagate_natural_width(True)

            self.flowbox_installed = FlowBoxInstalled(
                installed_kernels=self.manager_gui.installed_kernels,
                manager_gui=self.manager_gui,
            )
            vbox_installed_flowbox = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL, spacing=12
            )

            # vbox_installed_flowbox.set_halign(align=Gtk.Align.FILL)

            vbox_installed_flowbox.append(self.flowbox_installed)

            scrolled_window_installed.set_child(vbox_installed_flowbox)

            self.manager_gui.vbox_installed_kernels.append(scrolled_window_installed)

            if self.manager_gui.vbox_active_installed_kernel is not None:
                self.manager_gui.vbox_installed_kernels.reorder_child_after(
                    self.manager_gui.vbox_active_installed_kernel,
                    scrolled_window_installed,
                )
        else:
            self.manager_gui.vbox_installed_kernels = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL, spacing=5
            )
            self.manager_gui.vbox_installed_kernels.set_name("vbox_installed_kernels")

            self.manager_gui.vbox_active_installed_kernel = Gtk.Box(
                orientation=Gtk.Orientation.HORIZONTAL, spacing=5
            )
            self.manager_gui.vbox_active_installed_kernel.set_name("vbox_active_kernel")

            label_active_installed_kernel = Gtk.Label(xalign=0.5, yalign=0.5)
            label_active_installed_kernel.set_name("label_active_kernel")
            label_active_installed_kernel.set_selectable(True)

            label_active_installed_kernel.set_markup(
                "<b>Active kernel:</b> %s" % self.manager_gui.active_kernel
            )
            label_active_installed_kernel.set_halign(Gtk.Align.START)
            self.manager_gui.vbox_active_installed_kernel.append(
                label_active_installed_kernel
            )

            scrolled_window_installed = Gtk.ScrolledWindow()
            scrolled_window_installed.set_name("scrolled_window_installed")
            scrolled_window_installed.set_policy(
                Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC
            )
            scrolled_window_installed.set_propagate_natural_height(True)
            scrolled_window_installed.set_propagate_natural_width(True)

            label_installed_count.set_markup(
                "<i>%s Installed kernels</i>" % len(self.manager_gui.installed_kernels)
            )

            self.flowbox_installed = FlowBoxInstalled(
                installed_kernels=self.manager_gui.installed_kernels,
                manager_gui=self.manager_gui,
            )
            vbox_installed_flowbox = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL, spacing=12
            )

            # vbox_installed_flowbox.set_halign(align=Gtk.Align.FILL)

            vbox_installed_flowbox.append(self.flowbox_installed)

            scrolled_window_installed.set_child(vbox_installed_flowbox)

            # self.manager_gui.vbox_installed_kernels.append(label_installed_title)
            self.manager_gui.vbox_installed_kernels.append(vbox_header)
            self.manager_gui.vbox_installed_kernels.append(label_installed_desc)
            self.manager_gui.vbox_installed_kernels.append(label_installed_count)
            self.manager_gui.vbox_installed_kernels.append(vbox_search_entry)
            self.manager_gui.vbox_installed_kernels.append(scrolled_window_installed)
            self.manager_gui.vbox_installed_kernels.append(
                self.manager_gui.vbox_active_installed_kernel
            )

            self.manager_gui.stack.add_titled(
                self.manager_gui.vbox_installed_kernels, "Installed", "Installed"
            )

    def add_official_kernels_to_stack(self, reload):
        if reload is True:
            self.flowbox_stacks.clear()
            for kernel in fn.supported_kernels_dict:
                vbox_flowbox = None
                stack_child = self.manager_gui.stack.get_child_by_name(kernel)

                if stack_child is not None:
                    for stack_widget in stack_child:
                        if stack_widget.get_name() == "scrolled_window_official":
                            scrolled_window_official = stack_widget
                            vbox_flowbox = (
                                scrolled_window_official.get_child().get_child()
                            )

                            for widget in vbox_flowbox:
                                widget.remove_all()

                    self.flowbox_official_kernel = FlowBox(
                        kernel,
                        self.manager_gui.active_kernel,
                        self.manager_gui,
                        "official",
                    )
                    self.flowbox_stacks.append(self.flowbox_official_kernel)

                    vbox_flowbox.append(self.flowbox_official_kernel)

                # while self.manager_gui.default_context.pending():
                #     self.manager_gui.default_context.iteration(True)
        else:
            for kernel in fn.supported_kernels_dict:
                self.manager_gui.vbox_kernels = Gtk.Box(
                    orientation=Gtk.Orientation.VERTICAL, spacing=5
                )

                self.manager_gui.vbox_kernels.set_name("stack_%s" % kernel)

                hbox_sep_kernels = Gtk.Box(
                    orientation=Gtk.Orientation.VERTICAL, spacing=10
                )

                hsep_kernels = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)

                vbox_active_kernel = Gtk.Box(
                    orientation=Gtk.Orientation.HORIZONTAL, spacing=5
                )
                vbox_active_kernel.set_name("vbox_active_kernel")

                label_active_kernel = Gtk.Label(xalign=0.5, yalign=0.5)
                label_active_kernel.set_name("label_active_kernel")
                label_active_kernel.set_selectable(True)
                label_active_kernel.set_markup(
                    "<b>Active kernel:</b> %s" % self.manager_gui.active_kernel
                )
                label_active_kernel.set_halign(Gtk.Align.START)

                label_bottom_padding = Gtk.Label(xalign=0, yalign=0)
                label_bottom_padding.set_text(" ")

                hbox_sep_kernels.append(hsep_kernels)

                self.flowbox_official_kernel = FlowBox(
                    kernel, self.manager_gui.active_kernel, self.manager_gui, "official"
                )

                self.flowbox_stacks.append(self.flowbox_official_kernel)

                vbox_flowbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
                vbox_flowbox.set_name("vbox_flowbox_%s" % kernel)
                # vbox_flowbox.set_halign(align=Gtk.Align.FILL)
                vbox_flowbox.append(self.flowbox_official_kernel)

                scrolled_window_official = Gtk.ScrolledWindow()
                scrolled_window_official.set_name("scrolled_window_official")
                scrolled_window_official.set_policy(
                    Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC
                )
                scrolled_window_official.set_propagate_natural_height(True)
                scrolled_window_official.set_propagate_natural_width(True)

                label_title = Gtk.Label(xalign=0.5, yalign=0.5)
                label_title.set_text(kernel.upper())
                label_title.set_name("label_stack_kernel")

                label_desc = Gtk.Label(xalign=0, yalign=0)
                label_desc.set_text(fn.supported_kernels_dict[kernel][0])
                label_desc.set_name("label_stack_desc")

                label_count = Gtk.Label(xalign=0, yalign=0)
                label_count.set_markup(
                    "<i>%s Available kernels</i>"
                    % self.flowbox_official_kernel.kernel_count
                )

                label_count.set_name("label_stack_count")

                vbox_search_entry = Gtk.Box(
                    orientation=Gtk.Orientation.VERTICAL, spacing=5
                )

                search_entry_official = Gtk.SearchEntry()
                search_entry_official.set_name(kernel)
                search_entry_official.set_placeholder_text(
                    "Search %s kernels..." % kernel
                )
                search_entry_official.connect(
                    "search_changed", self.flowbox_filter_official
                )

                self.search_entries.append(search_entry_official)

                vbox_search_entry.append(search_entry_official)

                vbox_active_kernel.append(label_active_kernel)

                vbox_header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
                vbox_header.set_name("vbox_header")

                lbl_heading = Gtk.Label(xalign=0.5, yalign=0.5)
                lbl_heading.set_name("label_flowbox_message")
                lbl_heading.set_text(
                    "%s - Verified and official kernels" % kernel.upper()
                )

                lbl_padding = Gtk.Label(xalign=0.0, yalign=0.0)
                lbl_padding.set_text(" ")

                grid_banner_img = Gtk.Grid()

                image_settings = Gtk.Image.new_from_file(
                    os.path.join(base_dir, "images/48x48/akm-verified.png")
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

                # vbox_kernels.append(label_title)
                self.manager_gui.vbox_kernels.append(vbox_header)
                # self.manager_gui.vbox_kernels.append(label_title)
                self.manager_gui.vbox_kernels.append(label_desc)
                self.manager_gui.vbox_kernels.append(label_count)
                self.manager_gui.vbox_kernels.append(vbox_search_entry)
                self.manager_gui.vbox_kernels.append(hbox_sep_kernels)

                scrolled_window_official.set_child(vbox_flowbox)
                self.manager_gui.vbox_kernels.append(scrolled_window_official)
                self.manager_gui.vbox_kernels.append(vbox_active_kernel)

                kernel_sidebar_title = None

                if kernel == "linux":
                    kernel_sidebar_title = "Linux"
                elif kernel == "linux-lts":
                    kernel_sidebar_title = "Linux-LTS"
                elif kernel == "linux-zen":
                    kernel_sidebar_title = "Linux-ZEN"
                elif kernel == "linux-hardened":
                    kernel_sidebar_title = "Linux-Hardened"
                elif kernel == "linux-rt":
                    kernel_sidebar_title = "Linux-RT"
                elif kernel == "linux-rt-lts":
                    kernel_sidebar_title = "Linux-RT-LTS"

                self.manager_gui.stack.add_titled(
                    self.manager_gui.vbox_kernels, kernel, kernel_sidebar_title
                )

    def flowbox_filter_official(self, search_entry):
        def filter_func(fb_child, text):
            if search_entry.get_name() == fb_child.get_name().split(" ")[0]:
                if text in fb_child.get_name():
                    return True
                else:
                    return False
            else:
                return True

        text = search_entry.get_text()

        for flowbox in self.flowbox_stacks:
            flowbox.set_filter_func(filter_func, text)

    def flowbox_filter_community(self, search_entry):
        def filter_func(fb_child, text):
            if search_entry.get_name() == "search_entry_community":
                if text in fb_child.get_name():
                    return True
                else:
                    return False
            else:
                return True

        text = search_entry.get_text()

        self.flowbox_community.set_filter_func(filter_func, text)

    def flowbox_filter_installed(self, search_entry):
        def filter_func(fb_child, text):
            if search_entry.get_name() == "search_entry_installed":
                if text in fb_child.get_name():
                    return True
                else:
                    return False
            else:
                return True

        text = search_entry.get_text()

        self.flowbox_installed.set_filter_func(filter_func, text)

    def add_community_kernels_to_stack(self, reload):
        vbox_active_kernel = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        vbox_active_kernel.set_name("vbox_active_kernel")
        vbox_kernels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        hbox_sep_kernels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        hsep_kernels = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        hbox_sep_kernels.append(hsep_kernels)

        label_active_kernel = Gtk.Label(xalign=0.5, yalign=0.5)
        label_active_kernel.set_name("label_active_kernel")
        label_active_kernel.set_selectable(True)
        label_active_kernel.set_markup(
            "<b>Active kernel:</b> %s" % self.manager_gui.active_kernel
        )
        label_active_kernel.set_halign(Gtk.Align.START)

        label_count = Gtk.Label(xalign=0, yalign=0)
        label_count.set_name("label_stack_count")

        vbox_search_entry = None

        search_entry_community = Gtk.SearchEntry()
        search_entry_community.set_name("search_entry_community")
        search_entry_community.set_placeholder_text(
            "Search %s kernels..." % "community based"
        )
        search_entry_community.connect("search_changed", self.flowbox_filter_community)

        hbox_warning_message = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=5
        )
        hbox_warning_message.set_name("hbox_warning_message")

        label_pacman_warning = Gtk.Label(xalign=0, yalign=0)
        label_pacman_warning.set_name("label_community_warning")

        image_warning = Gtk.Image.new_from_file(
            os.path.join(base_dir, "images/48x48/akm-warning.png")
        )
        image_warning.set_name("image_warning")

        image_warning.set_icon_size(Gtk.IconSize.LARGE)
        image_warning.set_halign(Gtk.Align.CENTER)

        hbox_warning = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        hbox_warning.set_name("hbox_warning")

        hbox_warning.append(image_warning)
        # hbox_warning.append(label_pacman_warning)

        label_warning = Gtk.Label(xalign=0, yalign=0)
        label_warning.set_name("label_community_warning")
        label_warning.set_markup(
            f"These are user produced content\n"
            f"<b>Any use of the provided files is at your own risk</b>"
        )

        hbox_warning.append(label_warning)

        if reload is True:
            vbox_flowbox = None
            stack_child = self.manager_gui.stack.get_child_by_name("Community Kernels")

            if stack_child is not None:
                for stack_widget in stack_child:
                    if stack_widget.get_name() == "label_stack_count":
                        stack_widget.set_markup(
                            "<i>%s Available kernels</i>"
                            % len(self.manager_gui.community_kernels)
                        )
                    if stack_widget.get_name() == "vbox_search_entry":
                        if len(self.manager_gui.community_kernels) == 0:
                            for search_entry in stack_widget:
                                search_entry.set_visible(False)
                        else:
                            for search_entry in stack_widget:
                                search_entry.set_visible(True)

                    if stack_widget.get_name() == "scrolled_window_community":
                        scrolled_window_community = stack_widget
                        vbox_flowbox = scrolled_window_community.get_child().get_child()

                        for widget in vbox_flowbox:
                            if widget.get_name() != "vbox_no_community":
                                widget.remove_all()
                            else:
                                if len(self.manager_gui.community_kernels) > 0:
                                    # widget.hide()
                                    for box_widget in widget:
                                        box_widget.hide()

                                    vbox_search_entry = Gtk.Box(
                                        orientation=Gtk.Orientation.VERTICAL, spacing=5
                                    )

                                    vbox_search_entry.append(search_entry_community)
                                    # widget.append(hbox_warning)
                                    widget.append(vbox_search_entry)

                self.flowbox_community = FlowBox(
                    self.manager_gui.community_kernels,
                    self.manager_gui.active_kernel,
                    self.manager_gui,
                    "community",
                )
                vbox_flowbox.append(self.flowbox_community)

            while self.manager_gui.default_context.pending():
                # fn.time.sleep(0.1)
                self.manager_gui.default_context.iteration(True)
        else:
            self.flowbox_community = None

            vbox_flowbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            # vbox_flowbox.set_halign(align=Gtk.Align.FILL)

            if len(self.manager_gui.community_kernels) == 0:
                label_count.set_markup("<i>%s Available kernels</i>" % 0)
            else:
                self.flowbox_community = FlowBox(
                    self.manager_gui.community_kernels,
                    self.manager_gui.active_kernel,
                    self.manager_gui,
                    "community",
                )

                vbox_flowbox.append(self.flowbox_community)

                label_count.set_markup(
                    "<i>%s Available kernels</i>" % self.flowbox_community.kernel_count
                )

                vbox_search_entry = Gtk.Box(
                    orientation=Gtk.Orientation.VERTICAL, spacing=5
                )

                vbox_search_entry.set_name("vbox_search_entry")

                vbox_search_entry.append(search_entry_community)

            if reload is False:
                scrolled_window_community = Gtk.ScrolledWindow()
                scrolled_window_community.set_name("scrolled_window_community")
                scrolled_window_community.set_policy(
                    Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC
                )
                scrolled_window_community.set_propagate_natural_height(True)
                scrolled_window_community.set_propagate_natural_width(True)

                label_title = Gtk.Label(xalign=0.5, yalign=0.5)
                label_title.set_text("Community Kernels")
                label_title.set_name("label_stack_kernel")

                label_desc = Gtk.Label(xalign=0, yalign=0)
                label_desc.set_text("Community Linux kernel and modules")
                label_desc.set_name("label_stack_desc")

                vbox_active_kernel.append(label_active_kernel)

                vbox_header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
                vbox_header.set_name("vbox_header")

                lbl_heading = Gtk.Label(xalign=0.5, yalign=0.5)
                lbl_heading.set_name("label_flowbox_message")

                lbl_heading.set_text(
                    "%s - Unofficial kernels" % "Community based".upper()
                )

                lbl_padding = Gtk.Label(xalign=0.0, yalign=0.0)
                lbl_padding.set_text(" ")

                grid_banner_img = Gtk.Grid()

                image_settings = Gtk.Image.new_from_file(
                    os.path.join(base_dir, "images/48x48/akm-community.png")
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

                vbox_kernels.append(vbox_header)
                vbox_kernels.append(label_desc)
                vbox_kernels.append(hbox_warning)
                vbox_kernels.append(label_count)

                if vbox_search_entry is not None:
                    vbox_kernels.append(vbox_search_entry)
                vbox_kernels.append(hbox_sep_kernels)

                scrolled_window_community.set_child(vbox_flowbox)

                vbox_kernels.append(scrolled_window_community)
                vbox_kernels.append(vbox_active_kernel)

                self.manager_gui.stack.add_titled(
                    vbox_kernels, "Community Kernels", "Community"
                )
