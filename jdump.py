#!/usr/bin/env python

from actions import loadConfig, logError, showConfig, showMenu
from constants import BColors


def main():
    while True:
        config = loadConfig()
        if not config:
            logError('Configuration was not intialized correctly, make sure your configuration is correct')
            raise Exception()
        print()
        choice = showMenu(config)
        if choice:
            choice.function(config)
        else:
            break

if __name__ == '__main__':
    main()
