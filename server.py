#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Event-driven Messaging System Server"""

from __future__ import print_function
import sys
import socket
import struct
import select

__author__ = "João Francisco Martins and Victor Bernardo Jorge"

# QUESTIONS
# - Correct way to get server IP?
# - Can I kill client after check identity fail? - IT DOESNT MATTER.
# - What should I do in OK and ERROR messages?
# - Should we change target_id to each target in broadcast?

# TODO
# - Add docstrings
# - Get server IP in another way
# - LOG header of messages between clients
# - Remove list and dic receiving as return
# - Implement extra
# - Substitute all excessive parameters with client_maps
# - Maybe transform the elifs in server to a switch with dictionaries
# - Compile all the functions in the same socket_utils.py file
# - Make message a dictionary with labelled fields
# - When receiving zero byte messages not working properly

# WORK PLAN
# - Do all simple TODOs
# - Create module for unified methods
# - Simplify methods/mains

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

def send_broadcast(id_to_socket, msg):
  for client_id in id_to_socket:
    if id_to_socket[client_id][1] == "exhibitor":
      exhibitor_socket = id_to_socket[client_id][0]
      send_msg(exhibitor_socket, msg)

def receive_msg(s):
  msg_type = s.recv(2)

  if msg_type:
    msg_type = struct.unpack("!H", msg_type)[0]
    source_id = struct.unpack("!H", s.recv(2))[0]
    target_id = struct.unpack("!H", s.recv(2))[0]
    msg_id = struct.unpack("!H", s.recv(2))[0]
    msg = None

    if msg_type == 5:
      # Message is of type MSG and has content. Get size of content.
      content_size = struct.unpack("!H", s.recv(2))[0] 
      msg = s.recv(content_size)

    return msg_type, source_id, target_id, msg_id, msg

  else:
    return None, None, None, None, None

# TODO: Make associate clients a new function
def add_client(s, source_id, id_to_socket, emit_to_exhibit):
  client_type = ""
  associated_id = None

  if source_id == 0:
    client_type = "exhibitor"
  else:
    client_type = "emitter"

  client_id = get_free_id(client_type, id_to_socket)

  if client_id == -1:
    # Couldn't find a free id for that client
    print("[ERROR] Couldn't accept new client: All ids are occupied")
    return None

  id_to_socket[client_id] = (s, client_type)  # Maps id to socket

  if 2 ** 12 <= source_id < 2 ** 13:
    # Emitter(client_id) wants to be associated to an exhibitor(source_id)
    if source_id in id_to_socket and source_id not in emit_to_exhibit.values():
      # Exhibitor exists and is not associated to anyone yet
      emit_to_exhibit[client_id] = source_id 
      associated_id = source_id
    else:
      print("[ERROR] Couldn't accept new client: Emitter tried to link with an"
             " invalid exhibitor")
      return None

  print("[LOG] New", client_type, "with id", client_id, "has been assigned")
  if associated_id:
    print("[LOG] Exhibitor", associated_id, "is now associated with emitter",
          client_id) 
  return client_id

def remove_client(client_id, id_to_socket, emit_to_exhibit):
  del id_to_socket[client_id]

  if client_id in emit_to_exhibit:
    # Client had an exhibitor assigned to it
    del emit_to_exhibit[client_id]

  elif client_id in emit_to_exhibit.values():
    # Client had an emitter assigned to it. Get emitter key and remove entry.
    key = emit_to_exhibit.keys()[emit_to_exhibit.values().index(client_id)]
    del emit_to_exhibit[key]

def get_free_id(client_type, id_to_socket):
  free_id = -1

  if client_type == "emitter":
    for i in range(1, 2 ** 12):
      if i not in id_to_socket:
        free_id = i
        break

  elif client_type == "exhibitor":
    for i in range(2 ** 12, 2 ** 13):
      if i not in id_to_socket:
        free_id = i
        break

  return free_id

def get_socket_id(s, id_to_socket):
  for client_id, client_info in id_to_socket.iteritems():
    if client_info[0] == s:
      return client_id
  return None

def check_identity(client_id, s, id_to_socket):
  return id_to_socket[client_id][0] == s

def is_emitter(client_id, id_to_socket):
  return id_to_socket[client_id][1] == "emitter"

def is_exhibitor(client_id, id_to_socket):
  return id_to_socket[client_id][1] == "exhibitor" 

def has_exhibitor(client_id, emit_to_exhibit):
  return client_id in emit_to_exhibit

def get_clist_payload(id_to_socket):
  n = 0  # Number of connected clients
  client_ids = [] 

  for client_id in id_to_socket:
    client_ids.append(client_id)
    n += 1

  client_ids.sort()
  clients = ""
  for client in client_ids:
    clients += struct.pack("!H", client)

  return struct.pack("!H", n) + clients

def kill_client(s, err, connected_sockets, id_to_socket, emit_to_exhibit):
  err_msg = {
    "bad_id": ("[ERROR] Client " + str(get_socket_id(s, id_to_socket)) + " has"
               " been killed due to bad identity credentials"),
    "con_dead": ("[LOG] Client " + str(get_socket_id(s, id_to_socket)) + " has"
                 " been disconnected"),
    "oi_fail": ("[ERROR] Client " + str(get_socket_id(s, id_to_socket)) + " ha"
                "s been disconnected due to fail on connection setup")
  }
  print(err_msg[err])
  client_id = get_socket_id(s, id_to_socket)
  remove_client(client_id, id_to_socket, emit_to_exhibit)
  connected_sockets.remove(s)
  s.close()

def send_OK(s, source_id, client_id, msg_id):
  send_msg(s, create_msg('OK', server_id, source_id, msg_id)[0])

def send_ERRO(s, source_id, client_id, msg_id):
  send_msg(s, create_msg('ERRO', server_id, source_id, msg_id)[0])

# NOT IMPLEMENTED. DIVIDE INTO SUBFUNCTIONS
def process_msg(msg_type, source_id, target_id, msg_id, msg, expected_id):
  if msg_type == 1 and msg_id == expected_id:  # OK msg
    return True
  if msg_type == 2 and msg_id == seq_id:  # ERRO msg
    return False

  elif msg_type == 4:  # FLW msg
    msg = create_msg('OK', this_id, server_id, msg_id)[0]
    send_msg(emitter, msg)

    # Close connection
    emitter.close()
    # End script
    #break
  elif msg_type != 1:  
    return False



#====================================MAIN=====================================#

HOST = "127.0.0.1"
PORT = int(sys.argv[1])
ADDR = (HOST, PORT)

# Creates socket that will manage connections to the server
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Prevents "Address already in use" error
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 

server.bind(ADDR)
server.listen(1)

server_id = (2 ** 16) - 1  # Server id to use as source on messages
seq_id = 0 # Sequence number for messages begins at 0
connected_sockets = [server]  # Server is "connected" to itself
id_to_socket = {}  # Dictionary that maps client ids to (socket, type)
emit_to_exhibit = {}  # Dictionary that maps emitters to exhibitors
client_maps = (id_to_socket, emit_to_exhibit)  # Aggregation of dictionaries

while True:
  readable, writable, exceptional = select.select(connected_sockets, [], [])
  for s in readable:  
    if s is server:
      # A client has requested a connection
      client_socket, client_address = s.accept()
      print("[LOG] Client", client_address, "is now connected")
      connected_sockets.append(client_socket)

    else:
      msg_type, source_id, target_id, msg_id, msg = receive_msg(s)

      if msg_type == 1:  # OK message
        if check_identity(source_id, s, id_to_socket):
          print("[LOG] Received OK message from id ", source_id)

        else:
          # Identity check fail. Kill client.
          kill_client(s, "bad_id", connected_sockets, *client_maps)

      elif msg_type == 2:  # ERRO message
        if check_identity(source_id, s, id_to_socket):
          print("ERRO")
        else:
          # Identity check fail. Kill client.
          kill_client(s, "bad_id", connected_sockets, *client_maps)

      elif msg_type == 3:  # OI message
        client_id = add_client(s, source_id, *client_maps)
        if client_id:
          # Client was successfully added
          send_OK(s, server_id, client_id, msg_id)

        else:
          # Some error ocurred when trying to add client
          send_ERRO(s, server_id, source_id, msg_id)
          kill_client(s, "oi_fail", connected_sockets, *client_maps)

      elif msg_type == 4:  # FLW message
        if check_identity(source_id, s, id_to_socket):
          # Sends OK to emitter
          send_ok(s, server_id, source_id, msg_id)

          if is_emitter(source_id, id_to_socket):
            if has_exhibitor(source_id, emit_to_exhibit):
              # If emitter had an exhibitor assigned, request it to die
              exhibitor_id = emit_to_exhibit[source_id]
              exhibitor_socket = id_to_socket[exhibitor_id][0]

              # Sends FLW to exhibitor
              msg, seq_id = create_msg('FLW', server_id, exhibitor_id, seq_id)
              send_msg(exhibitor_socket, msg)

              # Receives OK from exhibitor. No treatment needed.
              receive_msg(exhibitor_socket) 

              print("[LOG] Exhibitor", exhibitor_id, "has been disconnected: F"
                    "LW")
              # Closes connection to exhibitor
              remove_client(exhibitor_id, id_to_socket, emit_to_exhibit)
              connected_sockets.remove(exhibitor_socket)
              exhibitor_socket.close()

          print("[LOG] Emitter", source_id, "has been disconnected: FLW")
          # Closes connection to emitter
          remove_client(source_id, id_to_socket, emit_to_exhibit)
          connected_sockets.remove(s)
          s.close()

        else:
          # Identity check fail. Kill client.
          kill_client(s, "bad_id", connected_sockets, *client_maps)

      elif msg_type == 5:  # MSG message
        if check_identity(source_id, s, id_to_socket):
          msg = create_msg('MSG', source_id, target_id, msg_id, msg)[0]
          if target_id == 0:
            # Broadcast message. Overhead of recreating message.
            send_broadcast(id_to_socket, msg)
            send_OK(s, server_id, source_id, msg_id)

          elif target_id in id_to_socket:
            # Target client exists
            if is_exhibitor(target_id, id_to_socket):
              # Target is an exhibitor

              # Answer message with OK
              send_OK(s, server_id, source_id, msg_id)

              # Send message to exhibitor
              exhibitor_socket = id_to_socket[target_id][0]
              send_msg(exhibitor_socket, msg)

              # Wait for response
              response = receive_msg(exhibitor_socket)
              #process_msg(*response, msg_id)


            elif has_exhibitor(target_id, emit_to_exhibit):
              # Target is emitter but have an exhibitor associated

              # Answer message with OK
              send_OK(s, server_id, source_id, msg_id)

              # Redirects message to associated exhibitor
              exhibitor_id = emit_to_exhibit[target_id]
              exhibitor_socket = id_to_socket[exhibitor_id][0]
              send_msg(exhibitor_socket, msg)

              # Wait for response
              response = receive_msg(exhibitor_socket)

            else:
              # Target is an emitter with no associated exhibitor
              send_ERRO(s, server_id, source_id, msg_id)

          else:
            # Target is not a client
            send_ERRO(s, server_id, source_id, msg_id)

        else:
          # Identity check fail. Kill client.
          kill_client(s, "bad_id", connected_sockets, *client_maps)

      elif msg_type == 6:  # CREQ message
        if check_identity(source_id, s, id_to_socket):
          clist_payload = get_clist_payload(id_to_socket)
          msg, seq_id = create_msg('CLIST', 
                                    source_id, 
                                    target_id, 
                                    seq_id, 
                                    clist_payload)
          if target_id == 0:
            # Broadcast message
            send_broadcast(id_to_socket, msg)
            send_OK(s, server_id, source_id, msg_id)

          elif target_id in id_to_socket:
            # Target client exists
            if is_exhibitor(target_id, id_to_socket):
              # Target is an exhibitor

              # Answer message with OK
              send_OK(s, server_id, source_id, msg_id)

              # Send message to exhibitor
              exhibitor_socket = id_to_socket[target_id][0]
              send_msg(exhibitor_socket, msg)

              # Wait for response
              response = receive_msg(exhibitor_socket)

            elif has_exhibitor(target_id, emit_to_exhibit):
              # Target is emitter but have an exhibitor associated

              # Answer message with OK
              send_OK(s, server_id, source_id, msg_id)

              # Redirects message to associated exhibitor
              exhibitor_id = emit_to_exhibit[target_id]
              exhibitor_socket = id_to_socket[exhibitor_id][0]
              send_msg(exhibitor_socket, msg)

              # Wait for response
              response = receive_msg(exhibitor_socket)

            else:
              # Target is an emitter with no associated exhibitor
              send_ERRO(s, server_id, source_id, msg_id)

          else:
            # Target is not a client
            send_ERRO(s, server_id, source_id, msg_id)

        else:
          # Identity check fail. Kill client.
          kill_client(s, "bad_id", connected_sockets, *client_maps)

      else:
        # A client has closed the connection.
        kill_client(s, "con_dead", connected_sockets, *client_maps)
