#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Messaging System Client Messages Emitter"""

from __future__ import print_function
import sys
import socket
import struct
import client_utils as utils

__author__ = "João F. Martins, Victor B. Jorge and Alexandre A. Pereira"

#====================================MAIN=====================================# 

# Set up socket address
HOST = (sys.argv[1].split(":"))[0]
PORT = int((sys.argv[1].split(":"))[1])
ADDR = (HOST, PORT)

# Create socket and connect to server
emitter = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
emitter.connect(ADDR)

seq_id = 1  # Sequence number for messages. Starts at 1 because OI is executed.
this_id = 0  # The id for this client in the system
oi_id = 1  # id used in OI message for setup

if len(sys.argv) == 3:
  # If an exhibitor number has been given
  oi_id = int(sys.argv[2])

this_id = utils.execute_OI(emitter, oi_id)

# Format to send messages
print("\nThere are three types of messages. Their formats are as follows:\n\n"
      " 1. > (id) MESSAGE\n"
      " 2. > (CREQ) id\n"
      " 3. > (FLW)\n\n"
      "The first one sends MESSAGE to the specified exhibitor id(or emitter in"
      " the case of associated pairs). The second one sends a CLIST message to"
      " id. The third and last disconnects the client from the server. In the "
      "first two, use 0 as id to execute a broadcast.\n")

while True:
  try:
    # Send message
    msg = raw_input("> ")
    parameter = msg[msg.find("(")+1:msg.find(")")]

    if parameter == 'FLW':
      utils.execute_FLW(emitter, this_id, seq_id)

    elif parameter == 'CREQ':
      dest_id = msg[msg.find(")")+1:]
      if utils.represents_int(dest_id):
        # Sends message to server
        msg, seq_id = utils.create_msg('CREQ', this_id, int(dest_id), seq_id)
        emitter.send(msg)

        # Process server response
        response = utils.receive_msg(emitter)
        utils.process_msg(response, emitter, this_id, seq_id)
      else:
        print("Invalid CREQ message id.")
    elif utils.represents_int(parameter):
      # Message has type MSG. parameter contains dest_id.
      msg = msg[msg.find(")")+1:]  # Gets typed data

      # Sends message to server
      msg, seq_id = utils.create_msg('MSG', this_id, int(parameter), seq_id,
                                     msg)
      emitter.send(msg)
      
      # Process server response
      response = utils.receive_msg(emitter)
      utils.process_msg(response, emitter, this_id, seq_id)
    else:
      print("Invalid message entered.")
  except KeyboardInterrupt:
    utils.execute_FLW(emitter, this_id, seq_id)
