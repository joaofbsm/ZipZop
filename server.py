#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Event-driven Messaging System Server"""

import sys
import socket
import struct
import select

__author__ = "João Francisco Martins and Victor Bernardo Jorge"

# ANSWERED QUESTIONS
# - Do we need to pack the MSG message in network byte order? - ONLY C
# - OI message adds to Number Sequence? - YES
# - What happens if the exhibitor doesn't answer with OK? - NOTHING
# - What happens on error when setting emitter? Try again? - DIE
# - Show error on emitter's screen? - SIM 
# QUESTIONS
# - Can I kill client after check identity fail?
# - What should I do in OK and ERROR messages?
# - Should we change target_id to each target in broadcast?

# TODO
# - Test if blocking sockets works
# - Test simultaneous connection close
# - Add docstrings
# - Treat error on MSG sending in emitter: Show on screen
# - Send OK as reply to every arriving message
# - Add print log to OK and ERRO received messages
# - Use delete client function to remove from dicts
# - Get server IP in another way

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
  msg_type = struct.unpack("!H", s.recv(2))[0]
  source_id = struct.unpack("!H", s.recv(2))[0]
  target_id = struct.unpack("!H", s.recv(2))[0]
  msg_id = struct.unpack("!H", s.recv(2))[0]
  msg = None

  if msg_type == 5:
    # Message is of type MSG and has content. Get size of content.
    content_size = struct.unpack("!H", s.recv(2))[0] 
    msg = server.recv(content_size)

  return msg_type, source_id, target_id, msg_id, msg

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

def add_client(s, target_id, id_to_socket, emit_to_exhibit):
  client_type = ""

  if target_id == 0:
    client_type = "exhibitor"
  else:
    client_type = "emitter"

  client_id = get_free_id(client_type, id_to_socket)

  if client_id == -1:
    # Couldn't find a free id for that client
    return None, id_to_socket, emit_to_exhibit

  id_to_socket[target_id] = (s, client_type)  # Maps id to socket

  if 2 ** 12 <= target_id < 2 ** 13:
    # Emitter(client_id) wants to be associated to an exhibitor(target_id)
    if target_id in id_to_socket and target_id not in emit_to_exhibit.values():
      emit_to_exhibit[client_id] = target_id 
    else:
      return None, id_to_socket, emit_to_exhibit

  print "[LOG] New", client_type, "with id", client_id, "has been assigned."
  return client_id, id_to_socket, emit_to_exhibit

def delete_client(client_id, id_to_socket, emit_to_exhibit):
  pass

def check_identity(client_id, s, id_to_socket):
  return id_to_socket[client_id][0] == s

def is_emitter(client_id, id_to_socket):
  return id_to_socket[client_id][2] == "emitter"

def is_exhibitor(client_id, id_to_socket):
  return id_to_socket[client_id][2] == "exhibitor" 

def has_exhibitor(client_id, emit_to_exhibit):
  return client_id in emit_to_exhibit

def get_clist_payload(id_to_socket):
  n = 0  # Number of connected clients
  clients = "" 

  for client_id in id_to_socket:
    clients += struct.pack("!H", client_id)
    n += 1

  return struct.pack("!H", n) + clients


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

while True:
  readable, writable, exceptional = select.select(connected_sockets, [], [])
  for s in readable:  
    if s is server:
      # A client has requested a connection
      client_socket, client_address = s.accept()
      print "[LOG] Client", client_address, "is now connected."
      connected_sockets.append(client_socket)
    else:
      msg_type, source_id, target_id, msg_id, msg = receive_msg(s)

      if msg_type == 1:  # OK message
        if check_identity(source_id, s, id_to_socket):
          print "OK"
        else:
          # Identity check fail. Kill client.
          print ("[LOG] Client", s.getpeername(), "has been killed due to bad "
                 "identity credentials.")
          connected_sockets.remove(s)
          s.close()

      elif msg_type == 2:  # ERRO message
        if check_identity(source_id, s, id_to_socket):
          print "ERRO"
        else:
          # Identity check fail. Kill client.
          print ("[LOG] Client", s.getpeername(), "has been killed due to bad "
                 "identity credentials.")
          connected_sockets.remove(s)
          s.close()

      elif msg_type == 3:  # OI message
        client_id, id_to_socket, emit_to_exhibit = add_client(s, 
                                                              target_id, 
                                                              id_to_socket, 
                                                              emit_to_exhibit)
        if client_id:
          # Client was successfully added
          msg = create_msg('OK', server_id, client_id, msg_id)[0]
        else:
          # Some error ocurred when trying to add client
          msg = create_msg('ERRO', server_id, source_id, msg_id)[0]

        send_msg(s, msg)

      elif msg_type == 4:  # FLW message
        if check_identity(source_id, s, id_to_socket):
          msg = create_msg('OK', server_id, source_id, msg_id)[0]
          send_msg(s, msg)

          if is_emitter(source_id, id_to_socket):
            if has_exhibitor(source_id, emit_to_exhibit):
              # If emitter had an exhibitor assigned, request it to die
              exhibitor_id = emit_to_exhibit[source_id]
              exhibitor_socket = id_to_socket[exhibitor_id]

              # Sends FLW to exhibitor
              msg, seq_id = create_msg('FLW', server_id, source_id, seq_id)
              send_msg(exhibitor_socket, msg)

              # Receives OK from exhibitor. No treatment needed.
              receive_msg(exhibitor_socket) 

              # Closes connection to exhibitor
              connected_sockets.remove(exhibitor_socket)
              exhibitor_socket.close()

          # Closes connection to emitter
          connected_sockets.remove(s)
          s.close()

        else:
          # Identity check fail. Kill client.
          print ("[LOG] Client", s.getpeername(), "has been killed due to bad "
                 "identity credentials.")
          connected_sockets.remove(s)
          s.close()

      elif msg_type == 5:  # MSG message
        if check_identity(source_id, s, id_to_socket):
          msg = create_msg('MSG', source_id, target_id, msg_id, msg)[0]
          if target_id == 0:
            # Broadcast message. Overhead of recreating message.
            send_broadcast(id_to_socket, msg)

          elif target_id in id_to_socket:
            # Target client exists
            if is_exhibitor(target_id, id_to_socket):
              # Target is an exhibitor. Deliver message.
              exhibitor_socket = id_to_socket[target_id][0]

              send_msg(exhibitor_socket, msg)

            elif has_exhibitor(target_id, emit_to_exhibit):
              # Target is emitter but have an exhibitor associated
              exhibitor_id = emit_to_exhibit[target_id]
              exhibitor_socket = id_to_socket[exhibitor_id]

              # Redirects message to associated exhibitor
              send_msg(exhibitor_socket, msg)

            else:
              # Target is an emitter with no associated exhibitor
              msg = create_msg('ERRO', server_id, target_id, msg_id)[0]
              send_msg(s, msg)

          else:
            # Target is not a client
            msg = create_msg('ERRO', server_id, target_id, msg_id)[0]
            send_msg(s, msg)

        else:
          # Identity check fail. Kill client.
          print ("[LOG] Client", s.getpeername(), "has been killed due to bad "
                 "identity credentials.")
          connected_sockets.remove(s)
          s.close()

      elif msg_type == 6:  # CREQ message
        if check_identity(source_id, s, id_to_socket):
          clist_payload = get_clist_payload(id_to_socket)
          msg, seq_id = create_msg('CLIST', 
                                    server_id, 
                                    target_id, 
                                    seq_id, 
                                    clist_payload)
          if target_id == 0:
            # Broadcast message
            send_broadcast(id_to_socket, msg)

          elif target_id in id_to_socket:
            # Target client exists
            if is_exhibitor(target_id, id_to_socket):
              # Target is an exhibitor. Deliver message.
              exhibitor_socket = id_to_socket[target_id][0]

              send_msg(exhibitor_socket, msg)

            elif has_exhibitor(target_id, emit_to_exhibit):
              # Target is emitter but have an exhibitor associated
              exhibitor_id = emit_to_exhibit[target_id]
              exhibitor_socket = id_to_socket[exhibitor_id]

              # Redirects message to associated exhibitor
              send_msg(exhibitor_socket, msg)

            else:
              # Target is an emitter with no associated exhibitor
              msg = create_msg('ERRO', server_id, source_id, msg_id)[0]
              send_msg(s, msg)

          else:
            # Target is not a client
            msg = create_msg('ERRO', server_id, target_id, msg_id)[0]
            send_msg(s, msg)

        else:
          # Identity check fail. Kill client.
          print ("[LOG] Client", s.getpeername(), "has been killed due to bad "
                 "identity credentials.")
          connected_sockets.remove(s)
          s.close()

      else:
        # A client has closed the connection
        print "[LOG] Client", s.getpeername(), "has been disconnected."
        connected_sockets.remove(s)
        s.close()
