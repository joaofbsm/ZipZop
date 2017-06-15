#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Messaging System Client Messages Exhibitor"""

from __future__ import print_function
import sys
import socket
import struct
import client_utils as utils

__author__ = "João Francisco Martins and Victor Bernardo Jorge"

# TODO
# 
  
#====================================MAIN=====================================#

# Set up socket address
HOST = (sys.argv[1].split(":"))[0]
PORT = int((sys.argv[1].split(":"))[1])
ADDR = (HOST, PORT)

# Create socket and connect to server
exhibitor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
exhibitor.connect(ADDR)

server_id = (2 ** 16) - 1
this_id = 0  # The id for this client in the system

# Sends the OI message after connection to server
msg = utils.create_msg('OI', this_id, 0, 0)[0]
exhibitor.send(msg)

# Receives server response with the client id
msg = utils.receive_msg(exhibitor)
if msg['type'] == 1:
  # Server returned OK message
  this_id = msg['dest_id']
  print("The id assigned to this exhibitor is", str(this_id) + ".")
else:
  # Server returned with error
  exhibitor.close()
  sys.exit("Couldn't estabilish a proper connection.")

while True:
  msg = utils.receive_msg(exhibitor)

  if msg['type'] == 4:  # FLW message
    # Send OK acknowledgement
    utils.send_OK(exhibitor, this_id, server_id, msg['id'])

    print("Received a FLW message. Shutting down now.")
    
    # Close connection
    exhibitor.close()

    # End script
    break

  if msg['type'] == 5:  # MSG message
    print("Message from", str(msg['orig_id']) + ":", msg['msg'])

    utils.send_OK(exhibitor, this_id, msg['orig_id'], msg['id'])

  elif msg['type'] == 7:  # CLIST message
    print("There are", msg['msg'][0], "clients connected to the server. These "
          "are their ids:", msg['msg'][1])

    utils.send_OK(exhibitor, this_id, msg['orig_id'], msg['id'])
