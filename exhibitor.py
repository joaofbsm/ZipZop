#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Messaging System Client Messages Exhibitor"""

from __future__ import print_function
import sys
import socket
import struct

__author__ = "João Francisco Martins and Victor Bernardo Jorge"

# TODO
# - Remove seq_id if it is not used in the code anymore
# - Answer every message with ok

#===================================METHODS===================================#

def create_msg(msg_type, source_id, target_id, msg_id, payload=None):
  type_to_int = {
    'OK': 1, 
    'ERRO': 2, 
    'OI': 3, 
    'FLW': 4, 
    'MSG': 5, 
    'CREQ': 6,
    'CLIST': 7, 
  }

  next_msg_id = msg_id

  if msg_type != 'OK' and msg_type != 'ERRO':
    next_msg_id += 1

  converted_type = struct.pack("!H", type_to_int[msg_type])
  source_id = struct.pack("!H", source_id)
  target_id = struct.pack("!H", target_id)
  msg_id = struct.pack("!H", msg_id)

  msg = converted_type + source_id + target_id + msg_id

  if msg_type == 'MSG':
    c = struct.pack("!H", len(payload))
    msg += c + payload
  elif msg_type == 'CLIST':
    msg += payload

  return msg, next_msg_id

def send_msg(s, msg):
  s.sendall(msg)

def receive_msg(s):
  msg_type = struct.unpack("!H", s.recv(2))[0]
  source_id = struct.unpack("!H", s.recv(2))[0]
  target_id = struct.unpack("!H", s.recv(2))[0]
  msg_id = struct.unpack("!H", s.recv(2))[0]
  msg = None

  if msg_type == 5:
    # Message is of type MSG and has content. Get size of content.
    msg_size = struct.unpack("!H", s.recv(2))[0] 
    msg = s.recv(msg_size)

  elif msg_type == 7:
    msg_size = struct.unpack("!H", s.recv(2))[0]
    msg = ""
    for i in range(msg_size):
      msg += str(struct.unpack("!H", s.recv(2))[0])
      if i != msg_size - 1:
        # If not last element
        msg += ", "

    msg = [msg_size, msg]

  return msg_type, source_id, target_id, msg_id, msg
  
#====================================MAIN=====================================#

# Set up socket address
HOST = (sys.argv[1].split(":"))[0]
PORT = int((sys.argv[1].split(":"))[1])
ADDR = (HOST, PORT)

# Create socket and connect to server
exhibitor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
exhibitor.connect(ADDR)

server_id = (2 ** 16) - 1
seq_id = 0  # Sequence number for messages begins at 0
this_id = 0  # The id for this client in the system

# Sends the OI message after connection to server
msg, seq_id = create_msg('OI', this_id, 0, seq_id)
send_msg(exhibitor, msg)

# Receives server response with the client id
msg_type, source_id, target_id, msg_id, msg = receive_msg(exhibitor)
if msg_type == 1:
  # Server returned OK message
  this_id = target_id
  print("The id assigned to this exhibitor is", this_id)
else:
  # Server returned with error
  emmiter.close()
  sys.exit("Couldn't estabilish a proper connection.")

while True:
  msg_type, source_id, target_id, msg_id, msg = receive_msg(exhibitor)

  if msg_type == 4:  # FLW message
    # Send OK acknowledgement
    msg = create_msg('OK', this_id, server_id, msg_id)[0]
    send_msg(exhibitor, msg)
    
    # Close connection
    exhibitor.close()
    # End program
    sys.exit()

  if msg_type == 5:  # MSG message
    print("Message from", str(source_id) + ":", msg)

  elif msg_type == 7:  # CLIST message
    print("There are", msg[0], "clients connected to the server. These are the"
          "ir ids:", msg[1])