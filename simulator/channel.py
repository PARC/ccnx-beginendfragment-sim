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

from delay import Delay
from simulator import Simulator
from event import Event
import random
import collections


class Channel(object):
    """
     Represents a nodes output queue.  Messages will be sent in FIFO order with a random delay
     drawn from a delay function and a given drop rate (drops happen after the delay).

     The output queue will have at most 1 timer running for the head-of-line message.
    """
    VERBOSE = False

    def __init__(self, sim, delay_generator, loss_rate):
        if not isinstance(sim, Simulator): raise TypeError("sim must be Simulator")
        if not isinstance(delay_generator, Delay): raise TypeError("delay_generator must be Delay")
        if not (0.0 <= loss_rate <= 1.0): raise ValueError("0.0 <= loss_rate <= 1.0")

        self._sim = sim
        self._delay = delay_generator
        self._loss_rate = loss_rate
        self._queue = collections.deque()
        self._pending_event = None

    def send(self, peer, message):
        """
        Sends the message to the peer.  Will call peer.receive(message).

        :param peer:
        :param message:
        :return:
        """
        if peer is None: raise RuntimeError("peer cannot be None")

        self._queue.append((peer, message))
        if len(self._queue) == 1:
            # enqueued first message, start a timer
            self._set_timer()

    def clear(self):
        """
        Clear the output queue
        :return:
        """
        self._queue.clear()
        if self._pending_event is not None:
            self._pending_event.set_inactive()
            self._pending_event = None

    def _set_timer(self):
        delay = self._delay.next()
        if Channel.VERBOSE:
            print "{:>12.9f} CHANNEL start timer delay {}".format(self._sim.now, delay)

        event = Event(delay, self._queue_timer, None)
        self._pending_event = event
        self._sim.schedule(event)

    def _queue_timer(self, data):
        if len(self._queue) == 0: raise RuntimeError("Queue timer fired with zero events in queue")
        self._pending_event = None

        peer, message = self._queue.pop()
        self._send_with_loss(peer, message)
        if len(self._queue) > 0:
            self._set_timer()

    def _send_with_loss(self, peer, message):
        r = random.random()
        if r < (1.0 - self._loss_rate):
            peer.receive(message)
        else:
            if Channel.VERBOSE:
                print "{:>12.9f} CHANNEL message dropped to peer {} message {}".format(self._sim.now, peer, message)
