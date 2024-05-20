import gi
import libs.functions as fn

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio, GLib, GdkPixbuf, GObject, Gdk

base_dir = fn.os.path.abspath(fn.os.path.join(fn.os.path.dirname(__file__), ".."))


class SplashScreen(Gtk.Window):
    def __init__(self, app_name, **kwargs):
        super().__init__(**kwargs)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_modal(True)
        self.set_title(app_name)
        self.set_icon_name("archlinux-kernel-manager-tux")

        tux_icon = Gtk.Picture.new_for_file(
            file=Gio.File.new_for_path(
                fn.os.path.join(base_dir, "images/364x408/akm-tux-splash.png")
            )
        )
        tux_icon.set_content_fit(content_fit=Gtk.ContentFit.FILL)

        self.set_child(child=tux_icon)
        self.present()
