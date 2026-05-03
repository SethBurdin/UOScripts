'''
utilities/logger.py

Lightweight debug logger for Razor Enhanced scripts.
Sends messages in-game and optionally appends timestamped lines to a file.

Usage
-----
    from Scripts.utilities.logger import Logger

    import os
    log = Logger(
        enabled  = True,
        log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'my_script.log'),
    )

    log('starting up')                   # default color (cyan)
    log('something bad', color='red')    # named color from glossary/colors
    log('raw hue', color=1100)           # or pass an integer hue directly

Toggle debug at the top of your script:
    log.enabled = False   # silences both in-game messages and file writes
    log.enabled = True    # re-enables both
'''

import datetime
import os

_colors = {
    'green':  65,
    'cyan':   90,
    'orange': 43,
    'red':    1100,
    'yellow': 52,
}


class Logger(object):

    def __init__(self, enabled=True, log_file=None, default_color='cyan'):
        '''
        enabled       -- bool, master on/off switch
        log_file      -- absolute path string; None disables file output
        default_color -- key from glossary/colors or an int hue
        '''
        self.enabled       = enabled
        self.log_file      = log_file
        self.default_color = default_color

        if log_file and enabled:
            self._write_header()

    # ── public call interface ──────────────────────────────────────────────────

    def __call__(self, msg, color=None):
        '''log(msg) or log(msg, color='red') or log(msg, color=52)'''
        if not self.enabled:
            return

        hue = self._resolve_color(color if color is not None else self.default_color)
        Misc.SendMessage(str(msg), hue)

        if self.log_file:
            self._append(msg)

    # ── convenience level helpers ──────────────────────────────────────────────

    def info(self, msg):
        self(msg, color='cyan')

    def ok(self, msg):
        self(msg, color='green')

    def warn(self, msg):
        self(msg, color='yellow')

    def error(self, msg):
        self(msg, color='red')

    # ── file helpers ───────────────────────────────────────────────────────────

    def _resolve_color(self, color):
        if isinstance(color, int):
            return color
        return _colors.get(str(color), _colors.get('cyan', 90))

    def _now(self):
        return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def _append(self, msg):
        try:
            with open(self.log_file, 'a') as f:
                f.write('[%s] %s\n' % (self._now(), msg))
        except Exception as e:
            Misc.SendMessage('Logger write error: %s' % e, _colors.get('red', 1100))

    def _write_header(self):
        try:
            dir_path = os.path.dirname(self.log_file)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path)
            with open(self.log_file, 'a') as f:
                f.write('\n=== run started %s ===\n' % self._now())
        except Exception:
            pass
