import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


class Stack(Gtk.Stack):
    def __init__(self, transition_type):
        super(Stack, self).__init__()

        # self.set_transition_type(Gtk.StackTransitionType.ROTATE_LEFT)
        if transition_type == "ROTATE_LEFT":
            transition_type = Gtk.StackTransitionType.ROTATE_LEFT
        if transition_type == "ROTATE_RIGHT":
            transition_type = Gtk.StackTransitionType.ROTATE_RIGHT
        if transition_type == "CROSSFADE":
            transition_type = Gtk.StackTransitionType.CROSSFADE
        if transition_type == "SLIDE_UP":
            transition_type = Gtk.StackTransitionType.SLIDE_UP
        if transition_type == "SLIDE_DOWN":
            transition_type = Gtk.StackTransitionType.SLIDE_DOWN
        if transition_type == "OVER_DOWN":
            transition_type = Gtk.StackTransitionType.OVER_DOWN

        self.set_transition_type(transition_type)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_transition_duration(250)
        self.set_hhomogeneous(False)
        self.set_vhomogeneous(False)
