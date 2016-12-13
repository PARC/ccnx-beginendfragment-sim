#
# Copyright (c) 2016, Xerox Corporation (Xerox) and Palo Alto Research Center, Inc (PARC)
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL XEROX OR PARC BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
################################################################################
#
# PATENT NOTICE
#
# This software is distributed under the BSD 2-clause License (see LICENSE
# file).  This BSD License does not make any patent claims and as such, does
# not act as a patent grant.  The purpose of this section is for each contributor
# to define their intentions with respect to intellectual property.
#
# Each contributor to this source code is encouraged to state their patent
# claims and licensing mechanisms for any contributions made. At the end of
# this section contributors may each make their own statements.  Contributor's
# claims and grants only apply to the pieces (source code, programs, text,
# media, etc) that they have contributed directly to this software.
#
# There is no guarantee that this section is complete, up to date or accurate. It
# is up to the contributors to maintain their portion of this section and up to
# the user of the software to verify any claims herein.
#
# Do not remove this header notification.  The contents of this section must be
# present in all distributions of the software.  You may only modify your own
# intellectual property statements.  Please provide contact information.
#
# - Palo Alto Research Center, Inc
# This software distribution does not grant any rights to patents owned by Palo
# Alto Research Center, Inc (PARC). Rights to these patents are available via
# various mechanisms. As of January 2016 PARC has committed to FRAND licensing any
# intellectual property used by its contributions to this software. You may
# contact PARC at cipo@parc.com for more information or visit http://www.ccnx.org

from event import Event
from simulator import Simulator
from channel import Channel
from message import Fragment
from message import FragReset
from message import FragResetAck
import random
import sys


class Node(object):
    """
    Represents a node (a peer) in the fragmentation protocol.  We only support one peer per none as the
    protocol executes independently for each pair of nodes.
    """
    EXTRA_VERBOSE = False
    VERBOSE = False

    TIMEOUT_MIN = 0.050
    TIMEOUT_MAX = 4.0

    # These are the only allowed states as per the state machine
    _STATE_REBOOT = 0
    _STATE_INIT_INIT = 1
    _STATE_INIT_OK = 2
    _STATE_SYNC_OK = 3
    _STATE_SYNC_INIT = 4
    _STATE_OK_INIT = 5
    _STATE_OK_OK = 6

    _state_strings = {_STATE_REBOOT: "Reboot",
                      _STATE_INIT_INIT: "Init, Init",
                      _STATE_INIT_OK: "Init, OK",
                      _STATE_SYNC_OK: "Sync, OK",
                      _STATE_SYNC_INIT: "Sync, Init",
                      _STATE_OK_INIT: "OK, Init",
                      _STATE_OK_OK: "OK, OK"}

    # a little additive jitter at the end of the timeout
    TIMEOUT_JITTER = 0.005

    class State(object):
        """
        Maintains the state for a single peer, as per draft-mosko-icnrg-beginendfragment-01 section 2.1
        """
        def __init__(self):
            self.set_initial_state()

            # stats
            self.cnt_data_recv = 0
            self.cnt_data_sent = 0
            self.cnt_data_not_ok = 0
            self.cnt_reset_recv = 0
            self.cnt_reset_sent = 0
            self.cnt_resetack_recv = 0
            self.cnt_resetack_sent = 0
            self.cnt_reboots = 0

        def __repr__(self):
            return "{{State: s ({}), n ({}, {}), fsn ({}, {})}}".format(
                Node._state_strings[self.STATE],
                self.N_LOCAL, self.N_REMOTE,
                self.FSN_LOCAL, self.FSN_REMOTE)

        def set_initial_state(self):
            # reset state (INIT or SYNC or OK)
            self.STATE = Node._STATE_REBOOT

            # sequence number for reset
            self.N_LOCAL = 0
            self.N_REMOTE = 0

            # Fragment sequence number
            self.FSN_LOCAL = 0
            self.FSN_REMOTE = 0

            self.timeout = Node.TIMEOUT_MIN
            self.timeout_pending = False
            self.timeout_event = None

        def stats(self):
            return "{{Stats: {{data: recv {} sent {} not_ok {}}}, {{reset: recv {} sent {}}}, {{ack: recv {} sent {}}}, {{reboots: {}}}".format(
                self.cnt_data_recv, self.cnt_data_sent, self.cnt_data_not_ok,
                self.cnt_reset_recv, self.cnt_reset_sent,
                self.cnt_resetack_recv, self.cnt_resetack_sent,
                self.cnt_reboots)

    def __init__(self, sim, name, channel):
        if not isinstance(sim, Simulator): raise TypeError("sim must be Simulator")
        if not isinstance(channel, Channel): raise TypeError("channel must be Channel")

        self._sim = sim
        self._name = name
        self._peer = None
        self._state = Node.State()
        self._channel = channel

        self._use_reboot = False
        self._reboot_after = 0
        self._reboot_delay = 0
        self._reboot_recurring = False

        self._ready = True

        if Node.VERBOSE:
            print "{:>12.9f} Created {}".format(self._sim.now, self)

        # start at a random time between 1 and 2 seconds from now
        delay = random.uniform(1, 2)
        self._reboot_after = delay
        self._use_reboot = True
        self._schedule_reboot()

    def __repr__(self):
        return "{{Node: name {} state {}}}".format(self._name, self._state)

    def set_peer(self, peer):
        """Sets the node to send our messages to"""
        self._peer = peer

    @property
    def name(self):
        return self._name

    @property
    def data_ready(self):
        """Returns true if node is ready to send/receive data"""
        return self._state.STATE == Node._STATE_OK_OK

    def print_stats(self):
        print "{:>12.9f} NODE {} {}".format(self._sim.now, self._name, self._state.stats())

    def receive(self, message):
        if not isinstance(message, Fragment): raise TypeError("message must be a fragment")
        if not self.is_ready: return

        if message.is_reset:
            self._receive_reset(message)
        elif message.is_resetack:
            self._receive_resetack(message)
        else:
            self._receive_data(message)

    def reboot_after(self, reboot_after, reboot_delay, recurring=False):
        """
        Schedule the node to reboot a certain amount of time after it goes in to (OK, OK) state.

        :param reboot_after: The time after going in to (OK, OK) to reboot
        :param reboot_delay: The time it takes to reboot
        :param recurring: Will repeat the reboots every time in (OK, OK)
        :return:
        """
        self._use_reboot = True
        self._reboot_after = reboot_after
        self._reboot_delay = reboot_delay
        self._reboot_recurring = recurring

        if self.data_ready:
            # If we're already in (OK, OK) schedule the reboot immediately
            self._schedule_reboot()

    @property
    def is_ready(self):
        """Determines if the node is ready to process messages"""
        return self._ready

    #########################
    # Private API

    def _schedule_reboot(self):
        if self._use_reboot:
            if Node.VERBOSE:
                print "{:>12.9f} NODE {} schedule reboot delay {}".format(self._sim.now, self._name, self._reboot_after)

            event = Event(self._reboot_after, self._reboot_start_callback, None)
            self._sim.schedule(event)
            # only do it once unless recurring reboot
            self._use_reboot = self._reboot_recurring

    def _reboot_start_callback(self, data):
        self._ready = False
        self._channel.clear()
        self._cancel_timer()

        if Node.VERBOSE:
            print "{:>12.9f} NODE {} rebooting {}".format(self._sim.now, self._name, self)

        event = Event(self._reboot_delay, self._reboot_finished_callback, None)
        self._sim.schedule(event)

    ########################################
    # State machine operations

    def _send_reset(self):
        if not self.is_ready: raise RuntimeError("Cannot send while not ready")

        self._state.cnt_reset_sent += 1
        message = FragReset(self, self._state.N_LOCAL)
        if Node.EXTRA_VERBOSE:
            print "{:>12.9f} NODE {} send RESET    {}".format(self._sim.now, self._name, self._state.N_LOCAL)

        self._channel.send(self._peer, message)

    def _send_resetack(self):
        if not self.is_ready: raise RuntimeError("Cannot send while not ready")

        self._state.cnt_resetack_sent += 1
        message = FragResetAck(self, self._state.N_LOCAL, self._state.N_REMOTE)
        if Node.EXTRA_VERBOSE:
            print "{:>12.9f} NODE {} send RESETACK {}, {}".format(
                self._sim.now, self._name, self._state.N_LOCAL, self._state.N_REMOTE)

        self._channel.send(self._peer, message)

    def _reset_timeout(self):
        self._state.timeout = Node.TIMEOUT_MIN

    def _increase_timeout(self):
        """Exponential backoff of timeout"""
        if self._state.timeout < Node.TIMEOUT_MAX:
            self._state.timeout *= 2
            if self._state.timeout > Node.TIMEOUT_MAX:
                self._state.timeout = Node.TIMEOUT_MAX

    def _get_timeout(self):
        """ The current timeout plus some random jitter """
        t = self._state.timeout
        jitter = random.uniform(0, Node.TIMEOUT_JITTER)
        return t + jitter

    def _cancel_timer(self):
        if self._state.timeout_event:
            self._state.timeout_event.set_inactive()
        self._state.timeout_event = None
        self._state.timeout_pending = False

        if Node.EXTRA_VERBOSE:
            print "{:>12.9f} NODE {} cancel_timer  {}".format(self._sim.now, self._name, self._state)

    def _start_timer(self):
        if not self.is_ready: raise RuntimeError("Cannot start a time while not ready")

        if self._state.timeout_pending: raise RuntimeError("Trying to start a timer when one already running")
        delay = self._get_timeout()

        if Node.EXTRA_VERBOSE:
            print "{:>12.9f} NODE {} timeout delay {} {}".format(self._sim.now, self._name, delay, self)

        event = Event(delay, self._timeout_callback, None)
        self._state.timeout_pending = True
        self._state.timeout_event = event
        self._sim.schedule(event)

    def _start_data_queue(self):
        sys.stdout.flush()
        if Node.VERBOSE:
            print "{:>12.9f} NODE {} start data queue {}".format(self._sim.now, self._name, self)
        # this may be a no-op if not setup to reboot node
        self._schedule_reboot()

    ########################################
    # State machine

    def _reboot_finished_callback(self, data):
        self._state.set_initial_state()
        self._state.cnt_reboots += 1

        self._ready = True

        if Node.VERBOSE:
            print "{:>12.9f} NODE {} reboot finished {}".format(self._sim.now, self._name, self)

        self._master_start(None)

    def _master_start(self, data):
        self._state.STATE = Node._STATE_INIT_INIT
        self._state.N_LOCAL = random.randint(1, 0xFFFF)
        self._reset_timeout()

        if Node.VERBOSE:
            print "{:>12.9f} NODE {} master_start {}".format(self._sim.now, self._name, self)

        self._send_reset()
        self._start_timer()
        self._state.STATE = Node._STATE_SYNC_INIT

    def _timeout_callback(self, data):
        """Callback for the timeout timer

        If we are still in the INIT state, then try again. If we are in the OK state,
        then ignore.
        :param data: ignored
        """
        if not self.is_ready: return

        self._state.timeout_pending = False
        self._state.timeout_event = None

        if Node.EXTRA_VERBOSE:
            print "{:>12.9f} NODE {} timeout {}".format(self._sim.now, self._name, self._state)

        if self._state.STATE == Node._STATE_REBOOT:
            raise RuntimeError("Unexpected event state: {}", self._state)

        elif self._state.STATE == Node._STATE_INIT_INIT:
            raise RuntimeError("Unexpected event state: {}", self._state)

        elif self._state.STATE == Node._STATE_INIT_OK:
            raise RuntimeError("Unexpected event state: {}", self._state)

        elif self._state.STATE == Node._STATE_SYNC_OK:
            self._increase_timeout()
            self._send_reset()
            self._start_timer()

        elif self._state.STATE == Node._STATE_SYNC_INIT:
            self._increase_timeout()
            self._send_reset()
            self._start_timer()

        elif self._state.STATE == Node._STATE_OK_INIT:
            raise RuntimeError("Unexpected event state: {}", self._state)

        elif self._state.STATE == Node._STATE_OK_OK:
            raise RuntimeError("Unexpected event state: {}", self._state)

        else:
            raise RuntimeError("Invalid state: ", self._state.STATE)

        if Node.EXTRA_VERBOSE:
            print "{:>12.9f} NODE {} finished {}".format(self._sim.now, self._name, self._state)

    def _receive_data_not_ok(self):
        if Node.VERBOSE:
            print "{:>12.9f} NODE {} error received data not OK mode {}".format(self._sim.now, self._name, self)
        self._state.cnt_data_not_ok += 1

    def _receive_data_ok(self):
        if Node.VERBOSE:
            print "{:>12.9f} NODE {} receive data {}".format(self._sim.now, self._name, self)
        # Do something

    def _receive_data(self, message):
        self._state.cnt_data_recv += 1

        if self._state.STATE == Node._STATE_REBOOT:
            self._receive_data_not_ok()

        elif self._state.STATE == Node._STATE_INIT_INIT:
            self._receive_data_not_ok()

        elif self._state.STATE == Node._STATE_INIT_OK:
            self._receive_data_ok()

        elif self._state.STATE == Node._STATE_SYNC_OK:
            self._receive_data_ok()

        elif self._state.STATE == Node._STATE_SYNC_INIT:
            self._receive_data_not_ok()

        elif self._state.STATE == Node._STATE_OK_INIT:
            self._receive_data_not_ok()

        elif self._state.STATE == Node._STATE_OK_OK:
            self._receive_data_ok()

        else:
            raise RuntimeError("Invalid state: ", self._state.STATE)

    def _receive_reset(self, message):
        # used to detect the edge from data not ready to data ready
        prior_data_ready = self.data_ready

        reset_number = message.reset_number

        if Node.EXTRA_VERBOSE:
            print "{:>12.9f} NODE {} recv RESET    {} {}".format(self._sim.now, self._name, reset_number, self._state)

        if self._state.STATE == Node._STATE_REBOOT:
            # Drop
            pass

        elif self._state.STATE == Node._STATE_INIT_INIT:
            self._state.N_REMOTE = reset_number
            self._send_resetack()
            self._state.STATE = Node._STATE_INIT_OK

            self._send_reset()
            self._start_timer()
            self._state.STATE = Node._STATE_SYNC_OK

        elif self._state.STATE == Node._STATE_INIT_OK:
            self._state.N_REMOTE = reset_number
            self._send_resetack()

        elif self._state.STATE == Node._STATE_SYNC_OK:
            if reset_number == self._state.N_REMOTE:
                self._send_resetack()
            else:
                self._cancel_timer()
                self._state.N_REMOTE = reset_number
                self._state.S_LOCAL = 0
                self._state.S_REMOTE = 0
                self._send_resetack()
                self._state.STATE = Node._STATE_INIT_OK

                self._send_reset()
                self._start_timer()
                self._state.STATE = Node._STATE_SYNC_OK

        elif self._state.STATE == Node._STATE_SYNC_INIT:
            self._state.N_REMOTE = reset_number
            self._send_resetack()
            self._state.STATE = Node._STATE_SYNC_OK

        elif self._state.STATE == Node._STATE_OK_INIT:
            self._state.N_REMOTE = reset_number
            self._send_resetack()
            self._state.STATE = Node._STATE_OK_OK

        elif self._state.STATE == Node._STATE_OK_OK:
            if reset_number == self._state.N_REMOTE:
                self._send_resetack()
            else:
                self._state.N_REMOTE = reset_number
                self._state.S_LOCAL = 0
                self._state.S_REMOTE = 0
                self._send_resetack()
                self._state.STATE = Node._STATE_INIT_OK

                self._send_reset()
                self._start_timer()
                self._state.STATE = Node._STATE_SYNC_OK

        else:
            raise RuntimeError("Invalid state: ", self._state.STATE)

        if Node.EXTRA_VERBOSE:
            print "{:>12.9f} NODE {} finished      {}".format(self._sim.now, self._name, self._state)

        # Only trigger this on the frist edge from not prior_data_ready to current data_ready
        if not prior_data_ready and self.data_ready:
            self._start_data_queue()

    def _receive_resetack(self, message):
        self._state.cnt_resetack_recv += 1
        prior_data_ready = self.data_ready

        reset_number = message.reset_number
        ack_number = message.ack_number
        if Node.EXTRA_VERBOSE:
            print "{:>12.9f} NODE {} recv RESETACK {} {}".format(self._sim.now, self._name, (reset_number, ack_number), self._state)

        if self._state.STATE == Node._STATE_REBOOT:
            # Drop
            pass

        elif self._state.STATE == Node._STATE_INIT_INIT:
            raise RuntimeError("Unexpected event state: {}", self._state)

        elif self._state.STATE == Node._STATE_INIT_OK:
            raise RuntimeError("Unexpected event state: {}", self._state)

        elif self._state.STATE == Node._STATE_SYNC_OK:
            if ack_number == self._state.N_LOCAL:
                self._cancel_timer()
                self._reset_timeout()

                if reset_number == self._state.N_REMOTE:
                    self._state.STATE = Node._STATE_OK_OK
                else:
                    self._state.N_REMOTE = reset_number
                    self._state.S_LOCAL = 0
                    self._state.S_REMOTE = 0
                    self._send_resetack()
                    self._state.STATE = Node._STATE_INIT_OK

                    self._send_reset()
                    self._start_timer()
                    self._state.STATE = Node._STATE_SYNC_OK

        elif self._state.STATE == Node._STATE_SYNC_INIT:
            if ack_number == self._state.N_LOCAL:
                self._cancel_timer()
                self._reset_timeout()
                self._state.STATE = Node._STATE_OK_INIT

                self._state.N_REMOTE = reset_number
                self._send_resetack()
                self._state.STATE = Node._STATE_OK_OK

        elif self._state.STATE == Node._STATE_OK_INIT:
            pass

        elif self._state.STATE == Node._STATE_OK_OK:
            pass

        else:
            raise RuntimeError("Invalid state: ", self._state.STATE)

        if Node.EXTRA_VERBOSE:
            print "{:>12.9f} NODE {} finished      {}".format(self._sim.now, self._name, self._state)

        # detect the edge transition from not prior_data_ready to data_ready
        if not prior_data_ready and self.data_ready:
            self._start_data_queue()

