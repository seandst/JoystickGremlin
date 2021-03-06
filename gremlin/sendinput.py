# -*- coding: utf-8; -*-

# Copyright (C) 2015 - 2018 Lionel Ott
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import ctypes
import ctypes.wintypes
import enum
import math
import threading
import time

from gremlin.common import MouseButton, SingletonDecorator


"""Defines flags used when specifying MOUSEINPUT structures.

https://msdn.microsoft.com/en-us/library/ms646273(v=VS.85).aspx
"""
WHEEL_DELTA = 120
XBUTTON1 = 0x0001
XBUTTON2 = 0x0002
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_HWHEEL = 0x01000
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_MOVE_NOCOALESCE = 0x2000
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_VIRTUALDESK = 0x4000
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_XDOWN = 0x0080
MOUSEEVENTF_XUP = 0x0100


"""Defines data structure type for INPUT structures.

https://msdn.microsoft.com/en-us/library/ms646270(v=vs.85).aspx
"""
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1


@SingletonDecorator
class MouseController:

    """Centralizes sending mouse events in a organized manner."""

    def __init__(self):
        """Creates a new instance."""
        self._delta_x = 0
        self._delta_y = 0
        self._acceleration = 0.0
        self._max_speed = 0
        self._last_start_time = time.time()

        self._is_running = False
        self._thread = threading.Thread(target=self._control_loop)

    @property
    def acceleration(self):
        return self._acceleration

    @acceleration.setter
    def acceleration(self, value):
        self._acceleration = float(value)

    @property
    def dx(self):
        return self._delta_x

    @dx.setter
    def dx(self, value):
        self._last_start_time = time.time()
        self._delta_x = int(value)

    @property
    def dy(self):
        return self._delta_y

    @dy.setter
    def dy(self, value):
        self._last_start_time = time.time()
        self._delta_y = int(value)

    @property
    def max_speed(self):
        return self._max_speed

    @max_speed.setter
    def max_speed(self, value):
        self._max_speed = int(value)

    def start(self):
        """Starts the thread that will send motions when required."""
        if not self._is_running:
            self._thread = threading.Thread(target=self._control_loop)
            self._thread.start()

    def stop(self):
        """Stops the thread that sends motion events."""
        if self._thread.is_alive():
            self._is_running = False
            self._thread.join()

    def _control_loop(self):
        """Loop responsible for creating and sending mouse motion events."""
        self._is_running = True
        while self._is_running:
            # Only send motion events if they are non zero
            if self._delta_x == 0 and self._delta_y == 0:
                time.sleep(0.01)
                continue

            delta_x = self._delta_x
            delta_y = self._delta_y
            # Handle acceleration enabled motions
            if self._acceleration > 0.0:
                change = self.acceleration * \
                         (time.time() - self._last_start_time)
                if delta_x != 0:
                    delta_x = min(self.max_speed, change + abs(delta_x))
                    delta_x = int(round(math.copysign(delta_x, self._delta_x)))
                if delta_y != 0:
                    delta_y = min(self.max_speed, change + abs(delta_y))
                    delta_y = int(round(math.copysign(delta_y, self._delta_y)))

            # Send mouse motion event and then sleep
            mouse_relative_motion(delta_x, delta_y)
            time.sleep(0.01)


class _MOUSEINPUT(ctypes.Structure):

    """Defines the MOUSEINPUT structure.

    https://msdn.microsoft.com/en-us/library/ms646273(v=VS.85).aspx
    """

    _fields_ = (
        ("dx", ctypes.wintypes.LONG),
        ("dy", ctypes.wintypes.LONG),
        ("mouseData", ctypes.wintypes.DWORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.wintypes.ULONG)),
    )


class _KEYBDINPUT(ctypes.Structure):

    """Defines the KEYBDINPUT structure.

    https://msdn.microsoft.com/en-us/library/ms646271(v=vs.85).aspx
    """

    _fields_ = (
        ("wVk", ctypes.wintypes.WORD),
        ("wScan", ctypes.wintypes.WORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("wExtraInfo", ctypes.POINTER(ctypes.wintypes.ULONG))
    )


class _INPUTunion(ctypes.Union):

    """Defines the INPUT union type.

    https://msdn.microsoft.com/en-us/library/ms646270(v=vs.85).aspx
    """

    _fields_ = (
        ("mi", _MOUSEINPUT),
        ("ki", _KEYBDINPUT)
    )


class _INPUT(ctypes.Structure):

    """Defines the INPUT structure.

    https://msdn.microsoft.com/en-us/library/ms646270(v=vs.85).aspx
    """

    _fields_ = (
        ("type", ctypes.wintypes.DWORD),
        ("union", _INPUTunion)
    )


def mouse_relative_motion(dx, dy):
    _send_input(
        _mouse_input(MOUSEEVENTF_MOVE, dx, dy)
    )


def mouse_press(button):
    if button == MouseButton.Left:
        _send_input(_mouse_input(MOUSEEVENTF_LEFTDOWN))
    elif button == MouseButton.Right:
        _send_input(_mouse_input(MOUSEEVENTF_RIGHTDOWN))
    elif button == MouseButton.Middle:
        _send_input(_mouse_input(MOUSEEVENTF_MIDDLEDOWN))
    elif button == MouseButton.Back:
        _send_input(_mouse_input(MOUSEEVENTF_XDOWN, data=XBUTTON1))
    elif button == MouseButton.Forward:
        _send_input(_mouse_input(MOUSEEVENTF_XDOWN, data=XBUTTON2))


def mouse_release(button):
    if button == MouseButton.Left:
        _send_input(_mouse_input(MOUSEEVENTF_LEFTUP))
    elif button == MouseButton.Right:
        _send_input(_mouse_input(MOUSEEVENTF_RIGHTUP))
    elif button == MouseButton.Middle:
        _send_input(_mouse_input(MOUSEEVENTF_MIDDLEUP))
    elif button == MouseButton.Back:
        _send_input(_mouse_input(MOUSEEVENTF_XUP, data=XBUTTON1))
    elif button == MouseButton.Forward:
        _send_input(_mouse_input(MOUSEEVENTF_XUP, data=XBUTTON2))


def mouse_wheel(motion):
    _send_input(_mouse_input(MOUSEEVENTF_WHEEL, data=-motion*WHEEL_DELTA))


def _mouse_input(flags, dx=0, dy=0, data=0):
    return _INPUT(
        INPUT_MOUSE,
        _INPUTunion(mi=_MOUSEINPUT(dx, dy, data, flags, 0, None))
    )


def _send_input(*inputs):
    nInputs = len(inputs)
    LPINPUT = _INPUT * nInputs
    pInputs = LPINPUT(*inputs)
    cbSize = ctypes.c_int(ctypes.sizeof(_INPUT))

    return ctypes.windll.user32.SendInput(nInputs, pInputs, cbSize)
