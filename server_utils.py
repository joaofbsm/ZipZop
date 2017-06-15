#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Messaging System Server Utility Functions"""

from __future__ import print_function
import socket
import struct

__author__ = "João Francisco Martins and Victor Bernardo Jorge"

#==================================CONSTANTS==================================#

serv_id = (2 ** 16) - 1 # Server id to use as source on messages

#===================================METHODS===================================#

# Create and pack a message with the parameters
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

# Generate and return the payload for the CLIST message
def create_clist_payload(id_to_sock):
  n = 0  # Number of connected clients
  client_ids = [] 

  for client_id in id_to_sock:
    client_ids.append(client_id)
    n += 1

  client_ids.sort()
  clients = ""
  for client in client_ids:
    clients += struct.pack("!H", client)

  return struct.pack("!H", n) + clients

# Send message and process the received response
def deliver_msg(msg, s, conn_socks, id_to_sock, emi_to_exh):
  s.send(msg)
  # Receive confirmation
  response = receive_msg(s)
  process_msg(response, s, conn_socks, id_to_sock, emi_to_exh)

# Send message to every exhibitor connected and process the received response
def deliver_broadcast(msg, s, conn_socks, id_to_sock, emi_to_exh):
  for client_id in id_to_sock:
    if id_to_sock[client_id][1] == "exhibitor":
      exhibitor_socket = id_to_sock[client_id][0]
      deliver_msg(msg, exhibitor_socket, conn_socks, id_to_sock, emi_to_exh)

# Send OK message to given socket and print LOG
def send_OK(s, orig_id, dest_id, msg_id):
  print("[LOG] Sending OK message to client ", dest_id, ".", sep = "")
  s.send(create_msg('OK', orig_id, dest_id, msg_id)[0])

# Send ERRO message to given socket and print LOG
def send_ERRO(s, orig_id, dest_id, msg_id):
  print("[LOG] Sending ERRO message to client ", dest_id, ".", sep = "")
  s.send(create_msg('ERRO', orig_id, dest_id, msg_id)[0])

# Send message to id. In case of emitter, if possible, redirects to exhibitor.
def send_to_id(msg, s, orig_msg, conn_socks, id_to_sock, emi_to_exh):
  if orig_msg['dest_id'] == 0:
    # Broadcast message
    deliver_broadcast(msg, s, conn_socks, id_to_sock, emi_to_exh)
    return True

  elif orig_msg['dest_id'] in id_to_sock:
    # Target client exists
    if is_exhibitor(orig_msg['dest_id'], id_to_sock):
      # Target is an exhibitor

      # Send message to exhibitor
      exhibitor_socket = id_to_sock[orig_msg['dest_id']][0]
      deliver_msg(msg, exhibitor_socket, conn_socks, id_to_sock, emi_to_exh)
      return True

    elif has_exhibitor(orig_msg['dest_id'], emi_to_exh):
      # Target is emitter but have an exhibitor associated

      # Redirects message to associated exhibitor
      exhibitor_id = emi_to_exh[orig_msg['dest_id']]
      exhibitor_socket = id_to_sock[exhibitor_id][0]
      deliver_msg(msg, exhibitor_socket, conn_socks, id_to_sock, emi_to_exh)
      return True

    else:
      # Target is an emitter with no associated exhibitor
      print("[ERROR] Target is an emitter with no associated exhibitor.")
      return False

  else:
    # Target is not a client
    print("[ERROR] Target is not a client.")
    return False

# Receives and split message, saving it to a dictionary 
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

    return msg

  else:
    # Empty message has been received. Client has disconnected.
    return None

# Tries to add new client and maybe link two of them
def add_client(s, orig_id, id_to_sock, emi_to_exh):
  client_type = ""
  associated_id = None

  if orig_id == 0:
    client_type = "exhibitor"
  else:
    client_type = "emitter"

  client_id = get_free_id(client_type, id_to_sock)

  if client_id == -1:
    # Couldn't find a free id for that client
    print("[ERROR] Couldn't accept new client: All ids are occupied.")
    return None

  id_to_sock[client_id] = (s, client_type)  # Maps id to socket

  if 2 ** 12 <= orig_id < 2 ** 13:
    # Emitter(client_id) wants to be associated to an exhibitor(orig_id)
    if orig_id in id_to_sock and orig_id not in emi_to_exh.values():
      # Exhibitor exists and is not associated to anyone yet
      emi_to_exh[client_id] = orig_id 
      associated_id = orig_id
    else:
      print("[ERROR] Couldn't accept new client: Emitter tried to link with an"
             " invalid exhibitor.")
      return None

  print("[LOG] New", client_type, "with id", client_id, "has been assigned.")
  if associated_id:
    print("[LOG] Exhibitor ", associated_id, " is now associated with emitter "
          , client_id, ".", sep = "") 
  return client_id

# Remove client from mappings(id_to_sock and emi_to_exh)
def remove_client(client_id, id_to_sock, emi_to_exh):
  del id_to_sock[client_id]

  if client_id in emi_to_exh:
    # Client had an exhibitor assigned to it
    del emi_to_exh[client_id]

  elif client_id in emi_to_exh.values():
    # Client had an emitter assigned to it. Get emitter key and remove entry.
    key = emi_to_exh.keys()[emi_to_exh.values().index(client_id)]
    del emi_to_exh[key]

# Finds and return a free id to assign to a new client
def get_free_id(client_type, id_to_sock):
  free_id = -1

  if client_type == "emitter":
    for i in range(1, 2 ** 12):
      if i not in id_to_sock:
        free_id = i
        break

  elif client_type == "exhibitor":
    for i in range(2 ** 12, 2 ** 13):
      if i not in id_to_sock:
        free_id = i
        break

  return free_id

# Get the client id for a given socket object
def get_socket_id(s, id_to_sock):
  for client_id, client_info in id_to_sock.iteritems():
    if client_info[0] == s:
      return client_id
  return None

# Returns True if client is an emitter
def is_emitter(client_id, id_to_sock):
  return id_to_sock[client_id][1] == "emitter"

# Returns True if client is an exhibitor
def is_exhibitor(client_id, id_to_sock):
  return id_to_sock[client_id][1] == "exhibitor" 

# Returns True if client is an emitter with an associated exhibitor
def has_exhibitor(client_id, emi_to_exh):
  return client_id in emi_to_exh

# Check if a socket object and an id point to the same client
def check_identity(client_id, s, id_to_sock):
  return id_to_sock[client_id][0] == s

# Process every message received by the server by calling sub process functions
def process_msg(msg, s, conn_socks, id_to_sock, emi_to_exh):
  process = {
    1: process_OK,
    2: process_ERRO,
    3: process_OI,
    4: process_FLW,
    5: process_MSG,
    6: process_CREQ
  }

  args = (msg, s, conn_socks, id_to_sock, emi_to_exh)

  if msg['type'] == 3:  # OI msg
    # Client will request an id, thus we can't check for identity yet
    process[msg['type']](*args)
  else:
    if check_identity(msg['orig_id'], s, id_to_sock):
      process[msg['type']](*args)
    else:
      send_ERRO(s, serv_id, orig_id, msg_id)
      kill_client(s, "bad_id", conn_socks, id_to_sock, emi_to_exh)

def process_OK(msg, s, conn_socks, id_to_sock, emi_to_exh):
  print("[LOG] Received OK message with id ", msg['id'], " from client ", 
        msg['orig_id'], ".", sep = "")

def process_ERRO(msg, s, conn_socks, id_to_sock, emi_to_exh):
  print("[LOG] Received ERRO message with id ", msg['id'], " from client ", 
        msg['orig_id'], ".", sep = "")

def process_OI(msg, s, conn_socks, id_to_sock, emi_to_exh):
  client_id = add_client(s, msg['orig_id'], id_to_sock, emi_to_exh)
  if client_id:
    # Client was successfully added
    send_OK(s, serv_id, client_id, msg['id'])

  else:
    # Some error ocurred when trying to add client
    send_ERRO(s, serv_id, 0, msg['id'])
    kill_client(s, "oi_fail", conn_socks, id_to_sock, emi_to_exh)

def process_FLW(msg, s, conn_socks, id_to_sock, emi_to_exh):
  # Sends OK to emitter
  send_OK(s, serv_id, msg['orig_id'], msg['id'])

  if has_exhibitor(msg['orig_id'], emi_to_exh):
    # If is emitter and had an exhibitor assigned, request it to die
    exhibitor_id = emi_to_exh[msg['orig_id']]
    exhibitor_socket = id_to_sock[exhibitor_id][0]

    # Sends FLW to exhibitor
    msg = create_msg('FLW', serv_id, exhibitor_id, 0)[0]
    deliver_msg(msg, exhibitor_socket, conn_socks, id_to_sock, emi_to_exh)

    # Closes connection to associated exhibitor
    kill_client(exhibitor_socket, 
                "flw_msg", 
                conn_socks, 
                id_to_sock, 
                emi_to_exh)

  # Close connection to client(emitter or exhibitor)
  kill_client(s, "flw_msg", conn_socks, id_to_sock, emi_to_exh)

def process_MSG(msg, s, conn_socks, id_to_sock, emi_to_exh):
  # Overhead of recreating the received message
  fwd_msg = create_msg('MSG', 
                       msg['orig_id'], 
                       msg['dest_id'], 
                       msg['id'], 
                       msg['msg'])[0]

  if msg['dest_id'] == 0:
    print("[LOG] Client", msg['orig_id'], "has sent a broadcast message.")
  else:
    print("[LOG] Client ", msg['orig_id'], " has sent a message to client ", 
          msg['dest_id'], ".", sep = "")
  
  sent = send_to_id(fwd_msg, s, msg, conn_socks, id_to_sock, emi_to_exh)
  if not sent:
    # Answer emitter with ERRO
    send_ERRO(s, serv_id, msg['orig_id'], msg['id'])
  else:
    # Answer emitter with OK
    send_OK(s, serv_id, msg['orig_id'], msg['id'])

def process_CREQ(msg, s, conn_socks, id_to_sock, emi_to_exh):
  clist_payload = create_clist_payload(id_to_sock)
  clist_msg = create_msg('CLIST', 
                         msg['orig_id'], 
                         msg['dest_id'], 
                         msg['id'], 
                         clist_payload)[0]

  if msg['dest_id'] == 0:
    print("[LOG] Client", msg['orig_id'], "has sent a broadcast CLIST.")
  else:
    print("[LOG] Client ", msg['orig_id'], " has sent a CLIST to client ", 
          msg['dest_id'], ".", sep = "")

  sent = send_to_id(clist_msg, s, msg, conn_socks, id_to_sock, emi_to_exh)
  if not sent:
    # Answer emitter with ERRO
    send_ERRO(s, serv_id, msg['orig_id'], msg['id'])
  else:
    # Answer emitter with OK
    send_OK(s, serv_id, msg['orig_id'], msg['id'])

# Kill a client connection, removing it from mappings and printing LOG
def kill_client(s, log, conn_socks, id_to_sock, emi_to_exh):
  log_msg = {
    "bad_id": ("[ERROR] Client " + str(get_socket_id(s, id_to_sock)) + " has b"
               "een killed due to bad identity credentials."),
    "oi_fail": ("[ERROR] Client " + str(get_socket_id(s, id_to_sock)) + " has "
                "been disconnected due to fail on connection setup."),
    "flw_msg": ("[LOG] Client " + str(get_socket_id(s, id_to_sock)) + " has be"
                "en disconnected: FLW."),
    "con_dead": ("[LOG] Client " + str(get_socket_id(s, id_to_sock)) + " has b"
                 "een disconnected.")
  }
  
  print(log_msg[log])

  client_id = get_socket_id(s, id_to_sock)

  if has_exhibitor(client_id, emi_to_exh):
    # If is emitter and had an exhibitor assigned, request it to die
    exhibitor_id = emi_to_exh[client_id]
    exhibitor_socket = id_to_sock[exhibitor_id][0]

    kill_client(exhibitor_socket, log, conn_socks, id_to_sock, emi_to_exh)

  client_id = get_socket_id(s, id_to_sock)
  remove_client(client_id, id_to_sock, emi_to_exh)
  conn_socks.remove(s)
  s.close()

# If CTRL+C was received, sends FLW to every client and waits for OK response
def broadcast_FLW(conn_socks, id_to_sock, emi_to_exh):
  print("\n[ANNOUNCEMENT] SERVER IS SHUTTING DOWN.")
  for client_id in id_to_sock:
    client_socket = id_to_sock[client_id][0]

    print("[LOG] Sending FLW message to client ", client_id, ".", sep = "")
    msg = create_msg('FLW', serv_id, client_id, 0)[0]
    deliver_msg(msg, client_socket, conn_socks, id_to_sock, emi_to_exh)

    conn_socks.remove(client_socket)
    client_socket.close()