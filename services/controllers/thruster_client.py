#!/usr/bin/env python3

import sys
import socket
import atexit
import pygame
from input_types import AXIS, BUTTON
from message import Message
import platform


# Each game controller axis returns a value in the closed interval [-1, 1]. We
# limit the number of decimal places we use with the PRECISION constant. This is
# done for a few reasons: 1) it makes the numbers more human-friendly (easier to
# read) and 2) it reduces the number of thruster updates.
#
# To elaborate on this last point, I was seeing a lot of very small fluctations
# with the values coming from my PS4 controller. The change in values were so
# small, they effectively would not change the current thruster value. By
# reducing the precision, these very small fluctuations get filtered out,
# resulting in fewer thruster updates. Also, I found that when I let go of a
# joystick, the value would hover around 0.0 but would never actually become
# zero. This means the thrusters would always be active, consuming battery power
# unnecessarily. Again, by limiting the precision, these small fluctuations were
# filtered out resulting in consistent zero values when then joysticks were in
# their resting positions.
#
# Using three digits of precisions was an arbitrary choice that just happened to
# work the first time. If we find that we need more fine control of the
# thrusters, we may need to increase this value.
PRECISION = 3

# Boolean to check if controller exists
controller_exists = 0

# NOTE: For some reason the same controller does not return the same axes
# numbers on macOS and Raspian, so we adjust these constants per OS so that the
# server will get consistent axis numbers. This has only been tested on macOS
# and Raspian 
# Additional NOTE: Same controller doesn't return same button on kenel 4.10+
AXIS_MAP = None
BUTTON_MAP = None

# Variable to hold index of found supported joycon
supported_joycon = 0

# Set of supported controller names (right now only PS4 Controller, Mac/Windows: Wireless Controller, Linux: Sony Computer...)
valid_names = set(["Sony Computer Entertainment Wireless Controller", "Wireless Controller"])

# Try/Except is used as a "hack" solution to check that the user has 4.10+ or higher
# For the linux kernel, so instead of trying to convert platform.release() into a 
# number and try to do less than conditionals, I know that converting the string
# when it is 4.10 is of length 4, but anything lower is valid only of length 3 (ex: 4.4.)
# Because if I try to convert "4.4." to float I get an error, but not with "4.10"
if platform.system() == "Linux":
    try:
        release = float(platform.release()[0:4])
        AXIS_MAP = [0, 1, 4, 3, 2, 5]
        BUTTON_MAP = [1, 2, 3, 0, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
    except:
        AXIS_MAP = [0, 1, 2, 4, 5, 3]
elif platform.system() == "Windows":
    AXIS_MAP = [0, 1, 2, 3, 5, 4]
else:
    print(platform.system() + " is not supported")
    exit(1)
# TO DO: Need Mac OS Elif before this else statement! Help from Kevin?

# NOTE that Darwin comes in, in the expected order

# This is the IP address and port of the server we will connect to. We send
# controller values to that machine over the network.
#host = "192.168.2.1"
host = "192.168.0.207"
port = 9999

# process command line args
for i in range(1, len(sys.argv)):
    arg = sys.argv[i]

    if arg == "-h" or arg == "--host":
        host = sys.argv[i + 1]

# create a socket object and connect to specified host/port
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((host, port))
print("Connected to server")


def close_socket():
    '''
    This function is called when the script shuts down. We need to make sure
    that we cleanly close all sockets we opened in this script. Simply close
    the socket to free any system level resources we are using.
    '''
    s.close()


def send_message(controller, type, index, value):
    '''
    Send a message to the server

    controller indicates which controller this message comes from
    type indicates what kind of input we got from the controller
    index indicates which input of the given type is sending the message
    value indicates the value of the input
    '''

    # Create an instance of a helper class that will pack and unpack our message
    # data for us.
    m = Message()

    # set all of the values on our helper class
    m.controller_index = controller
    m.input_type = type
    m.input_index = index
    m.input_value = value

    # convert the message to a byte array and send it to the server
    s.send(m.byte_convert())

    # We wait for a response from the server to acknowledge it was received.
    # Note that in order to make this code more robust, we should use some sort
    # of timeout here so our code does not hang upon failure to receive a
    # response
    response = s.recv(1024)

    # We expect a plaintext reponse, so convert the response to ASCII
    decoded_response = response.decode('ascii')

    # if the response is 'OK', then all is good. Note that we are not handling
    # non 'OK' responses. This code needs to be improved for better error
    # handling. For now we just print 'OK' to give some feedback to us humans
    # that communication appears to be working.
    if decoded_response != "OK":
        print(decoded_response)


# make sure to close our socket when the script exits
atexit.register(close_socket)

# We're using PyGame in order to get data from the PS4 controller. Here we
# initialize the game engine and the joystick handling code. We grab a
# reference to the first controller and initialize it for reading.
pygame.init()
pygame.joystick.init()

# Enumerate through joysticks to make sure we are using PS4 Controller
for i in range(0, pygame.joystick.get_count()):
    if pygame.joystick.Joystick(i).get_name() in valid_names:
        stick = pygame.joystick.Joystick(i)
        stick.init()
        supported_joycon = i
        controller_exists = 1

if (not controller_exists):
    print("No Supported Controller Connected")
    exit(1)
else:
    print(pygame.joystick.Joystick(supported_joycon).get_name() + " Connected")

# The following flag is used to exit our infinite control reading loop.
done = False

# For now, we assume we have only one controller. We hard code this constant to
# make it clear which controller is sending data the server. It's much easier
# to understand what "controller" refers to in later code as opposed to the
# magic number 0. This number must be a value in the closed interval [0,3].
controller = 0

# There are different types of input that can be generated from a controller:
# axis data, buttons, etc. We only care about joystick data (axis data) for the
# moment and we represent that as type zero. However, it is likely that we'll
# want to use buttons as inputs as well. The type value will need to change to
# indicate that we are sending a button value versus an axis value. Ideally, we
# should have a set of constants (an enumeration) of the values we can use here.
# This number must be a value in the closed interval [0,3].
type = 0

# Process controller input until we're told to quit
while done is False:
    # Wait until we get some input from a controller
    for event in pygame.event.get():
        value = None

        if event.type == pygame.QUIT:
            # We've been told to quit, so set our done flag to true. This will
            # cause our infitinite loop to exit
            done = True
        elif event.type == pygame.JOYAXISMOTION:
            # We have a joystick event. Grab which axis this is and the axis'
            # current value
            type = AXIS
            if AXIS_MAP is not None and 0 <= event.axis and event.axis < len(AXIS_MAP):
                index = AXIS_MAP[event.axis]
            else:
                index = event.axis
            value = round(event.value, PRECISION)
        elif event.type == pygame.JOYBUTTONDOWN:
            type = BUTTON
            value = 1
            if BUTTON_MAP is not None:
                index = BUTTON_MAP[event.button]
            else:
                index = event.button
        elif event.type == pygame.JOYBUTTONUP:
            type = BUTTON
            value = 0
            if BUTTON_MAP is not None:
                index = BUTTON_MAP[event.button]
            else:
                index = event.button

        # if we got a new value, then send it to the server
        if value is not None:
            send_message(controller, type, index, value)
