#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Event-driven Messaging System Server"""

from __future__ import print_function
import sys
import socket
import struct
import select
import server_utils as utils

__author__ = "João Francisco Martins and Victor Bernardo Jorge"

# QUESTIONS
# - Correct way to get server IP? - GETFQDN
# - Can I kill client after check identity fail? - YES
# - Should we change dest_id to each target in broadcast? - NO
# - Server need seq_id? - NO

# TODO
# - Add docstrings
# - Change how to get server address in final version
# - Implement extra -> except KeyboardInterrupt
# - Compile all the functions in the same server_utils.py file
# - Make serv_id a global constant

# WORK PLAN
# - Add CTRL-C treatment to both clients
# - Add comments to code 
# - GG WP

#====================================MAIN=====================================#

HOST = "127.0.0.1" #socket.gethostbyname(socket.getfqdn())
PORT = int(sys.argv[1])
ADDR = (HOST, PORT)

# Creates socket that will manage connections to the server
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Prevents "Address already in use" error
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 

# Set socket server to listen at given address
server.bind(ADDR)
server.listen(1)

print("[LOG] Server is now running at address ", HOST, " and port ", PORT, ".",
      sep = "")

conn_socks = [server]  # Connected Sockets. Server is "connected" to itself
id_to_sock = {}  # Dictionary that maps client ids to (socket, type)
emi_to_exh = {}  # Dictionary that maps emitters to exhibitors

while True:
  try:
    readable, writable, exceptional = select.select(conn_socks, [], [])
    for s in readable:  
      if s is server:
        # A client has requested a connection
        client_socket, client_address = s.accept()
        conn_socks.append(client_socket)
        print("[LOG] Client", client_address, "is now connected.")
      else:
        msg = utils.receive_msg(s)
        if msg:
          # Process received message according to its type
          utils.process_msg(msg, s, conn_socks, id_to_sock, emi_to_exh)
        else:
          # A client has closed the connection.
          utils.kill_client(s, "con_dead", conn_socks, id_to_sock, emi_to_exh)
  except KeyboardInterrupt:
    # Send FLW to every connected client, wait for OK and close all connections
    utils.broadcast_FLW(conn_socks, id_to_sock, emi_to_exh)

    # Close connection handling socket
    server.close()

    # End program
    sys.exit()