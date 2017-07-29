#!/usr/bin/env python3

import socket
import atexit
import _thread
from message import Message
from thruster_controller import ThrusterController

# It is possible for a host to have multiple IP addresses. Using 0.0.0.0
# will listen on all network interfaces on this host
HOST = "0.0.0.0"
PORT = 9999

# These will eventually be set from the command-line
SIMULATE = True
CALIBRATE = True

controller = ThrusterController(SIMULATE)


def on_calibration_server(controller):
    import os
    from bottle import put, request, route, run, static_file

    script_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "calibration")
    css_dir = os.path.join(script_dir, "css")
    js_dir = os.path.join(script_dir, "js")

    @route('/')
    def index():
        return static_file('index.html', root=script_dir)

    @route('/css/<filename>')
    def serve_css(filename):
        return static_file(filename, root=css_dir)

    @route('/js/<filename>')
    def server_js(filename):
        return static_file(filename, root=js_dir)

    @route('/api/settings')
    def api_settings():
        return controller.get_settings()

    @put('/api/settings')
    def put_settings():
        controller.set_settings(request.json)
        return {'status': 'OK'}

    run(host='localhost', port=8080)


def on_new_client(controller, clientsocket, addr):
    '''
    This function is responsible for communicating with an active socket
    connection. All input is passed directly to the thruster controller making
    this very lightweight. If we get an empty message from the client, this
    indicates that the conection needs to be shutdown

    NOTE: The functionality in here is bare bones. It would be wise to
    introduce a handshake upon initial connection with the client. This
    handshake should confirm that the version of this server and the version of
    the client are compatible. This implies that our responses need to grow in
    complexity.
    '''
    while True:
        msg = clientsocket.recv(1024)

        if msg == b'':
            print("disconnecting client")
            break
        else:
            m = Message(msg)
            if m.input_type == 0:
                controller.update_axis(m.input_index, m.input_value)
            elif m.input_type == 1:
                controller.update_button(m.input_index, m.input_value)

        # this is a simple confirmation to the client that we have received its
        # message and have processed it correctly. Ideally, this would be more
        # formalized allowing for error responses and such.
        clientsocket.send("OK".encode())

    clientsocket.close()


def close_socket():
    '''
    This function is called when the script shuts down. We need to make sure
    that we cleanly close all sockets we opened in this script. Simply close
    the socket to free any system level resources we are using.
    '''
    s.close()


if CALIBRATE:
    _thread.start_new_thread(on_calibration_server, (controller,))

# make sure to close our socket when the script exits
atexit.register(close_socket)

# Create a socket to listen for incoming connections
s = socket.socket()

# listen for connections on the specified IP address and port
s.bind((HOST, PORT))

# Begin listening for incoming connections allowing up to 5 unconnected
# requests to queue up before we start refusing connections
s.listen(5)

print("Thruster server bound to {}:{}".format(HOST, PORT))

while True:
    # wait for an incoming connection
    c, addr = s.accept()

    # show some feedback on who connected
    print('Got connection from', addr)

    # start a new thread to handle the connection. This prevents this thread
    # from hanging so it can process any other new connections that might
    # come in
    _thread.start_new_thread(on_new_client, (controller, c, addr))
