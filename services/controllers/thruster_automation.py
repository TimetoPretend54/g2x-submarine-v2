#!/usr/bin/env python3

import sys
import socket
import time
from message import Message


JL_H = 0  # left joystick horizontal axis
JL_V = 1  # left joystick vertical axis
JR_H = 2  # right joystick horizontal axis
JR_V = 3  # right joystick vertical axis

controller = 0
AXIS = 0
BUTTON = 1

HOST = "192.168.0.1"
PORT = 9999

# process command line args
for i in range(1, len(sys.argv)):
    arg = sys.argv[i]

    if arg == "-h" or arg == "--host":
        HOST = sys.argv[i + 1]


def send_message(controller, type, index, value):
    m = Message()

    m.controller_index = controller
    m.input_type = type
    m.input_index = index
    m.input_value = value

    if type == AXIS:
        print("Setting axis {} to {}".format(index, value))
    elif type == BUTTON:
        print("Setting button {} to {}".format(index, value))

    s.send(bytes(m))

    response = s.recv(1024)
    decoded_response = response.decode('ascii')

    if decoded_response != "OK":
        print(decoded_response)


s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))
print("Connected to server")

# send 50% forward for 1 second
send_message(controller, AXIS, JL_V, 0.5)
time.sleep(1)
send_message(controller, AXIS, JL_V, 0.0)

s.close()
