import sys


def warn(msg):
    print(f'WARNING: {msg}', file=sys.stderr)


def error(msg):
    print(f'ERROR: {msg}', file=sys.stderr)
