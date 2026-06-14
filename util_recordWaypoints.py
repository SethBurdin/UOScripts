'''
Records player waypoints to a JSON file as you walk a route.

Usage:
  1. (Optional) Set OUTPUT_NAME below to a fixed filename, e.g. 'dropoff'.
     Leave as None to auto-generate a timestamped name.
  2. Run this script.
  3. Walk your route.
  4. Press Stop in Razor Enhanced — file is saved after every point.

Output: saved in the same folder as this script.
Format: [[x, y], ...]  compatible with nav.load_waypoints()
'''

import json, os, time

INTERVAL = 5   # minimum tiles moved before a new point is recorded

# Set to a string like 'dropoff' to use a fixed filename.
# Leave as None to auto-generate: waypoints_YYYYMMDD_HHMM.json
OUTPUT_NAME = None

_TAG = '[recorder]'


def _log(msg, color=85):
    Misc.SendMessage(_TAG + ' ' + msg, color)


def _resolve_filename():
    if OUTPUT_NAME:
        return OUTPUT_NAME
    return 'waypoints_' + time.strftime('%Y%m%d_%H%M')


def main():
    name = _resolve_filename()

    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), name + '.json')
    _log('Saving to: %s' % output_path)
    _log('Walk your route. Press Stop when done.')

    pts    = []
    last_x = None
    last_y = None

    while not Player.IsGhost:
        x = Player.Position.X
        y = Player.Position.Y
        if last_x is None or abs(x - last_x) + abs(y - last_y) >= INTERVAL:
            pts.append([x, y])
            last_x, last_y = x, y
            with open(output_path, 'w') as fh:
                json.dump(pts, fh, indent=2)
            _log('Point %d: (%d, %d)' % (len(pts), x, y))
        Misc.Pause(250)

    _log('Done. Saved %d points to %s' % (len(pts), output_path), 68)


main()
