#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Messaging System Client Utility Functions"""

from __future__ import print_function
import socket
import struct

__author__ = "João Francisco Martins and Victor Bernardo Jorge"

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

def represents_int(s):
  try:
    int(s)
    return True
  except ValueError:
    return False