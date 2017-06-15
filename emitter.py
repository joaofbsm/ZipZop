#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Messaging System Client Messages Emitter"""

from __future__ import print_function
import sys
import socket
import struct

__author__ = "João Francisco Martins and Victor Bernardo Jorge"

# TODO
# - Make msg as dictionary
# - Separate files in server_utils, client_utils and system_utils
# - Maybe set socket to non blocking

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
msg, seq_id = create_msg('OI', oi_id, server_id, seq_id)
send_msg(emitter, msg)

# Receives server response with the client id
msg = receive_msg(emitter)
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
    msg, seq_id = create_msg('FLW', this_id, server_id, seq_id)
    send_msg(emitter, msg)

    # Wait for server OK. No treatment needed.
    receive_msg(emitter)

    # Close connection
    emitter.close()
    # End program
    sys.exit()

  elif parameter == 'CREQ':
    dest_id = msg[msg.find(")")+1:]
    if represents_int(dest_id):
      msg, seq_id = create_msg('CREQ', this_id, int(dest_id), seq_id)
      send_msg(emitter, msg)

      # Wait for server response
      msg = receive_msg(emitter)

      if msg['type'] == 1 and msg['id'] == (seq_id - 1):  # OK msg
        continue
      elif msg['type'] == 2 and msg['id'] == (seq_id - 1):  # ERRO msg
        print("Couldn't deliver message to that id.")
      elif msg['type'] == 4:  # FLW msg
        # Server has died, answer with OK
        msg = create_msg('OK', this_id, server_id, msg['id'])[0]
        send_msg(emitter, msg)

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

  elif represents_int(parameter):
    # Message is of type MSG. parameter contains dest_id
    msg = msg[msg.find(")")+1:]

    msg, seq_id = create_msg('MSG', this_id, int(parameter), seq_id, msg)
    send_msg(emitter, msg)

    # Wait for server response
    msg = receive_msg(emitter)

    if msg['type'] == 1 and msg['id'] == (seq_id - 1):  # OK msg
      continue
    elif msg['type'] == 2 and msg['id'] == (seq_id - 1):  # ERRO msg
      print("Couldn't deliver message to that id.")
    elif msg['type'] == 4:  # FLW msg
      # Server has died, answer with OK
      msg = create_msg('OK', this_id, server_id, msg['id'])[0]
      send_msg(emitter, msg)

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


