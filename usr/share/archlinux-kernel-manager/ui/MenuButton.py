import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

# Gtk.Builder xml for the application menu
APP_MENU = """
<?xml version="1.0" encoding="UTF-8"?>
<interface>
<menu id='app-menu'>
  <section>
    <item>
      <attribute name='label' translatable='yes'>_About</attribute>
      <attribute name='action'>win.about</attribute>
    </item>
    <item>
      <attribute name='label' translatable='yes'>_Settings</attribute>
      <attribute name='action'>win.settings</attribute>
    </item>
    <item>
      <attribute name='label' translatable='yes'>_Refresh</attribute>
      <attribute name='action'>win.refresh</attribute>
    </item>
    <item>
      <attribute name='label' translatable='yes'>_Quit</attribute>
      <attribute name='action'>win.quit</attribute>
    </item>
  </section>
</menu>
</interface>
"""


class MenuButton(Gtk.MenuButton):
    """
    Wrapper class for at Gtk.Menubutton with a menu defined
    in a Gtk.Builder xml string
    """

    def __init__(self, icon_name="open-menu-symbolic"):
        super(MenuButton, self).__init__()
        builder = Gtk.Builder.new_from_string(APP_MENU, -1)
        menu = builder.get_object("app-menu")
        self.set_menu_model(menu)
        self.set_icon_name(icon_name)
