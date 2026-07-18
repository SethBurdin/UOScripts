# test_screenshot.py
# Standalone trial for the guardian death-screenshot feature.
#
# Misc.CaptureNow() is a legacy-OSI-client feature — under ClassicUO's
# hardware-accelerated renderer it produces a solid-black image every time
# (confirmed: every existing capture in the RazorEnhanced Plugins folder is
# an identical 631 bytes, i.e. one flat color). There's no fix via that API.
#
# Instead this grabs the primary display through .NET's Graphics.CopyFromScreen,
# which reads the DWM-composited desktop output and works fine with
# hardware-accelerated windows. RazorEnhanced scripts run on IronPython, so
# System.Drawing / System.Windows.Forms are available directly via clr.
#
# NOTE: this captures the whole primary monitor, not just the client window.
# Fine if ClassicUO is fullscreen/maximized there; if you run windowed or on
# a second monitor let me know and we'll crop to the window rect instead.

if False:
    from razorenhanced_stubs import *

import os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import clr
clr.AddReference('System.Windows.Forms')
clr.AddReference('System.Drawing')
from System.Drawing import Bitmap, Graphics, Imaging
from System.Windows.Forms import Screen

LOCAL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local")
os.makedirs(LOCAL_DIR, exist_ok=True)


def capture_screenshot(label="test"):
    """Screenshot the primary display and save it into local/ with a timestamp.
    Returns the saved path."""
    bounds = Screen.PrimaryScreen.Bounds
    bmp = Bitmap(bounds.Width, bounds.Height)
    g = Graphics.FromImage(bmp)
    g.CopyFromScreen(bounds.X, bounds.Y, 0, 0, bounds.Size)
    g.Dispose()

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(LOCAL_DIR, "%s_%s.png" % (label, timestamp))
    bmp.Save(dest, Imaging.ImageFormat.Png)
    bmp.Dispose()

    Misc.SendMessage("[test-screenshot] Saved: %s" % dest, 68)
    return dest


capture_screenshot("test")
