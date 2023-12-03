#!/usr/bin/env bash

# Reset game statistics.
sqlite3 $1 "UPDATE users SET gold = msg_count, gambles = 0, gambles_won = 0, button_press = 0, monsters = 0, kills = 0, exp = 0, locations = 1, c_location = 1, deaths = 0, weapon = '', c_floor = 1;"
sqlite3 $1 "DROP TABLE items; DROP TABLE inventories;"
