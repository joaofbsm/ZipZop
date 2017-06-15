#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Messaging System Client Utility Functions"""

from __future__ import print_function
import sys
import socket
import struct

__author__ = "João Francisco Martins and Victor Bernardo Jorge"

#==================================CONSTANTS==================================#

serv_id = (2 ** 16) - 1  # Server id

#===================================METHODS===================================#

def create_msg(msg_type, orig_id, dest_id, msg_id, payload=None):
  type_to_int = {
    'OK': 1, 
    'ERRO': 2, 
    'OI': 3, 
    'FLW': 4, 
    'MSG': 5, 
    'CREQ': 6,
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

def send_OK(s, orig_id, dest_id, msg_id):
  s.send(create_msg('OK', orig_id, dest_id, msg_id)[0])

def send_FLW(s, orig_id, dest_id, msg_id):
  s.send(create_msg('FLW', orig_id, dest_id, msg_id)[0])

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

def process_msg(msg, s, this_id, seq_id):
  if msg['type'] == 1 and msg['id'] == (seq_id - 1):  # OK msg
    return 
  elif msg['type'] == 2 and msg['id'] == (seq_id - 1):  # ERRO msg
    print("Couldn't deliver message to that id.")

  elif msg['type'] == 4:  # FLW msg
    # Server has died, answer with OK
    msg = utils.create_msg('OK', this_id, serv_id, msg['id'])[0]
    s.send(msg)

    print("Message server has been shutdown.")

    # Close connection
    s.close()
    
    # End script
    sys.exit()
  else:
    # An error has occurred
    print("Messages have not been delivered.")

def execute_OI(s, oi_id):
  # Sends the OI message after connection to server
  msg, seq_id = create_msg('OI', oi_id, serv_id, 0)
  s.send(msg)

  # Receives server response with the client id
  msg = receive_msg(s)
  if msg['type'] == 1:
    # Server returned OK message
    this_id = msg['dest_id']
    print("The id assigned to this client is", str(this_id) + ".")

    if oi_id != 0 and oi_id != 1:
      # A real exhibitor number has been passed and accepted by the server
      print("The exhibitor id associated with this emitter is", str(oi_id) 
            + ".")

    return this_id
  else:
    # Server returned with error
    s.close()
    sys.exit("Couldn't estabilish a proper connection.")

def execute_FLW(s, orig_id, msg_id):
    # Send FLW message
    send_FLW(s, orig_id, serv_id, msg_id)

    # Wait for server OK. No treatment needed.
    receive_msg(s)

    # Close connection
    s.close()
    # End program
    sys.exit()

def represents_int(s):
  try:
    int(s)
    return True
  except ValueError:
    return False