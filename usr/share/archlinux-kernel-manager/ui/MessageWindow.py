import gi
import os
import libs.functions as fn

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio, GLib

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class MessageWindow(Gtk.Window):
    def __init__(self, title, message, image_path, detailed_message, **kwargs):
        super().__init__(**kwargs)

        # self.set_title(title=title)
        self.set_modal(modal=True)
        self.set_resizable(False)
        icon_name = "akm-tux"
        self.set_icon_name(icon_name)

        header_bar = Gtk.HeaderBar()
        header_bar.set_show_title_buttons(True)

        hbox_title = Gtk.Box.new(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        label_title = Gtk.Label(xalign=0.5, yalign=0.5)
        label_title.set_markup("<b>%s</b>" % title)

        hbox_title.append(label_title)
        header_bar.set_title_widget(hbox_title)

        self.set_titlebar(header_bar)

        vbox_message = Gtk.Box.new(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox_message.set_name("vbox_flowbox_message")

        image = Gtk.Picture.new_for_filename(os.path.join(base_dir, image_path))

        image.set_content_fit(content_fit=Gtk.ContentFit.SCALE_DOWN)
        image.set_halign(Gtk.Align.START)

        hbox_image = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)

        # hbox_image.append(image)

        self.set_child(child=vbox_message)

        if detailed_message is True:
            scrolled_window = Gtk.ScrolledWindow()

            textview = Gtk.TextView()
            textview.set_property("editable", False)
            textview.set_property("monospace", True)

            textview.set_vexpand(True)
            textview.set_hexpand(True)

            msg_buffer = textview.get_buffer()
            msg_buffer.insert(
                msg_buffer.get_end_iter(),
                "Event timestamp = %s\n"
                % fn.datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
            msg_buffer.insert(msg_buffer.get_end_iter(), "%s\n" % message)

            scrolled_window.set_child(textview)

            hbox_image.append(scrolled_window)

            self.set_size_request(700, 500)
            self.set_resizable(True)
        else:
            label_message = Gtk.Label(xalign=0, yalign=0)
            label_message.set_markup("%s" % message)
            label_message.set_name("label_flowbox_message")

            hbox_image.append(image)
            hbox_image.append(label_message)

        vbox_message.append(hbox_image)

        button_ok = Gtk.Button.new_with_label("OK")
        button_ok.set_size_request(100, 30)
        button_ok.set_halign(Gtk.Align.END)
        button_ok.connect("clicked", self.on_button_ok_clicked)

        hbox_buttons = Gtk.Box.new(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        hbox_buttons.set_halign(Gtk.Align.END)
        hbox_buttons.append(button_ok)

        vbox_message.append(hbox_buttons)

    def on_button_ok_clicked(self, button):
        self.hide()
        self.destroy()
