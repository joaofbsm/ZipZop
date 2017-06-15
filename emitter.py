#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Messaging System Client Messages Emitter"""

from __future__ import print_function
import sys
import socket
import struct
import client_utils as utils

__author__ = "João Francisco Martins and Victor Bernardo Jorge"

# TODO
# - Maybe set socket to non blocking to wait for FLW after any ENTER

#====================================MAIN=====================================# 

# Set up socket address
HOST = (sys.argv[1].split(":"))[0]
PORT = int((sys.argv[1].split(":"))[1])
ADDR = (HOST, PORT)

# Create socket and connect to server
emitter = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
emitter.connect(ADDR)

server_id = (2 ** 16) - 1
seq_id = 0  # Sequence number for messages
this_id = 0  # The id for this client in the system
oi_id = 1  # id used in OI message for setup

if len(sys.argv) == 3:
  # If an exhibitor number has been given
  oi_id = int(sys.argv[2])

# Sends the OI message after connection to server
msg, seq_id = utils.create_msg('OI', oi_id, server_id, seq_id)
emitter.send(msg)

# Receives server response with the client id
msg = utils.receive_msg(emitter)
if msg['type'] == 1:
  # Server returned OK message
  this_id = msg['dest_id']
  print("The id assigned to this emitter is", str(this_id) + ".")
  if oi_id != 1:
    print("The exhibitor id associated with this emitter is", str(oi_id) + ".")
else:
  # Server returned with error
  emitter.close()
  sys.exit("Couldn't estabilish a proper connection.")

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
  # Send message
  msg = raw_input("> ")
  parameter = msg[msg.find("(")+1:msg.find(")")]

  if parameter == 'FLW':
    # Send FLW message
    msg, seq_id = utils.create_msg('FLW', this_id, server_id, seq_id)
    emitter.send(msg)

    # Wait for server OK. No treatment needed.
    utils.receive_msg(emitter)

    # Close connection
    emitter.close()
    # End program
    sys.exit()

  elif parameter == 'CREQ':
    dest_id = msg[msg.find(")")+1:]
    if utils.represents_int(dest_id):
      msg, seq_id = utils.create_msg('CREQ', this_id, int(dest_id), seq_id)
      emitter.send(msg)

      # Wait for server response
      msg = utils.receive_msg(emitter)

      if msg['type'] == 1 and msg['id'] == (seq_id - 1):  # OK msg
        continue
      elif msg['type'] == 2 and msg['id'] == (seq_id - 1):  # ERRO msg
        print("Couldn't deliver message to that id.")
      elif msg['type'] == 4:  # FLW msg
        # Server has died, answer with OK
        msg = utils.create_msg('OK', this_id, server_id, msg['id'])[0]
        emitter.send(msg)

        print("Message server has been shutdown.")

        # Close connection
        emitter.close()
        
        # End script
        break
      else:
        # An error has occurred
        print("Messages have not been delivered.")

    else:
      print("Invalid CREQ message id.")

  elif utils.represents_int(parameter):
    # Message is of type MSG. parameter contains dest_id
    msg = msg[msg.find(")")+1:]

    msg, seq_id = utils.create_msg('MSG', this_id, int(parameter), seq_id, msg)
    emitter.send(msg)

    # Wait for server response
    msg = utils.receive_msg(emitter)

    if msg['type'] == 1 and msg['id'] == (seq_id - 1):  # OK msg
      continue
    elif msg['type'] == 2 and msg['id'] == (seq_id - 1):  # ERRO msg
      print("Couldn't deliver message to that id.")
    elif msg['type'] == 4:  # FLW msg
      # Server has died, answer with OK
      msg = utils.create_msg('OK', this_id, server_id, msg['id'])[0]
      emitter.send(msg)

      print("Message server has been shutdown.")

      # Close connection
      emitter.close()
      
      # End script
      break 
    else:
      # An error has occurred
      print("Messages have not been delivered.")

  else:
    print("Invalid message entered.")
    