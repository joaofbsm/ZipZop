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

#===================================METHODS===================================#

def create_msg(msg_type, orig_id, dest_id, msg_id, payload=None):
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
  orig_id = struct.pack("!H", orig_id)
  dest_id = struct.pack("!H", dest_id)
  msg_id = struct.pack("!H", msg_id)

  msg = converted_type + orig_id + dest_id + msg_id

  if msg_type == 'MSG':
    c = struct.pack("!H", len(payload))
    msg += c + payload
  elif msg_type == 'CLIST':
    msg += payload

  return msg, next_msg_id

def send_msg(s, msg):
  s.sendall(msg)

def send_OK(s, orig_id, dest_id, msg_id):
  s.send(create_msg('OK', orig_id, dest_id, msg_id)[0])

def receive_msg(s):
  msg = {}
  msg_type = s.recv(2)

  if msg_type:
    msg['type'] = struct.unpack("!H", msg_type)[0]
    msg['orig_id'] = struct.unpack("!H", s.recv(2))[0]
    msg['dest_id'] = struct.unpack("!H", s.recv(2))[0]
    msg['id'] = struct.unpack("!H", s.recv(2))[0]
    msg['msg'] = None

    if msg['type'] == 5:
      # Message has type MSG and has content. Get size of content.
      content_size = struct.unpack("!H", s.recv(2))[0] 
      msg['msg'] = s.recv(content_size)

    elif msg['type'] == 7:
      # Message has type CLIST
      clist_size = struct.unpack("!H", s.recv(2))[0]
      clist = ""
      for i in range(clist_size):
        clist += str(struct.unpack("!H", s.recv(2))[0])
        if i != clist_size - 1:
          # If not last element
          clist += ", "
      msg['msg'] = [clist_size, clist]

    return msg

  else:
    # Empty message has been received. Client has disconnected.
    return None
  
#====================================MAIN=====================================#

# Set up socket address
HOST = (sys.argv[1].split(":"))[0]
PORT = int((sys.argv[1].split(":"))[1])
ADDR = (HOST, PORT)

# Create socket and connect to server
exhibitor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
exhibitor.connect(ADDR)

server_id = (2 ** 16) - 1
seq_id = 0  # Sequence number for messages
this_id = 0  # The id for this client in the system

# Sends the OI message after connection to server
msg, seq_id = create_msg('OI', this_id, 0, seq_id)
send_msg(exhibitor, msg)

# Receives server response with the client id
msg = receive_msg(exhibitor)
if msg['type'] == 1:
  # Server returned OK message
  this_id = msg['dest_id']
  print("The id assigned to this exhibitor is", str(this_id) + ".")
else:
  # Server returned with error
  exhibitor.close()
  sys.exit("Couldn't estabilish a proper connection.")

while True:
  msg = receive_msg(exhibitor)

  if msg['type'] == 4:  # FLW message
    # Send OK acknowledgement
    send_OK(exhibitor, this_id, server_id, msg['id'])

    print("Received a FLW message. Shutting down now.")
    
    # Close connection
    exhibitor.close()

    # End script
    break

  if msg['type'] == 5:  # MSG message
    print("Message from", str(msg['orig_id']) + ":", msg['msg'])

    send_OK(exhibitor, this_id, msg['orig_id'], msg['id'])

  elif msg['type'] == 7:  # CLIST message
    print("There are", msg['msg'][0], "clients connected to the server. These are the"
          "ir ids:", msg['msg'][1])

    send_OK(exhibitor, this_id, msg['orig_id'], msg['id'])

