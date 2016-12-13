#!/usr/local/bin/python

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

import random
import os
import sys
import binascii
from simulator.simulator import Simulator
from simulator.node import Node
from simulator.delay import ExponentialDelay
from simulator.channel import Channel

# Set message printing level
Simulator.EXTRA_VERBOSE = False
Simulator.VERBOSE = False
Channel.VERBOSE = False
Node.VERBOSE = False
Node.EXTRA_VERBOSE = Node.VERBOSE


repeat_count = 5000
loss_rate = 0.60
min_delay = 0.000001  # 1 micro-second minimum delay
mean_dealy = 0.000020  # 20 micro-second delay

def run_trial(trial, alice_reboot_at=0.0, bob_reboot_at=0.0):
    sim = Simulator()

    delay_generator = ExponentialDelay(min_delay, mean_dealy)

    alice_output = Channel(sim, delay_generator, loss_rate)
    alice = Node(sim, "ALICE", alice_output)

    bob_output = Channel(sim, delay_generator, loss_rate)
    bob = Node(sim, "BOB  ", bob_output)

    alice.set_peer(bob)
    bob.set_peer(alice)

    # Alice will reboot 10 seconds after she goes in to (OK, OK) mode.
    if alice_reboot_at > 0:
        alice.reboot_after(alice_reboot_at, 2.0)

    if bob_reboot_at > 0:
        bob.reboot_after(bob_reboot_at, 2.0)

    sim.run_count(2000)

    alice.print_stats()
    bob.print_stats()

    print "trail {:6} Alice is {}, Bob is {}".format(
        trial,
        "OK" if alice.data_ready else "NOT OK",
        "OK" if bob.data_ready else "NOT OK",
    )

    sys.stdout.flush()
    print ""
    if not alice.data_ready or not bob.data_ready: raise RuntimeError("Terminated in failure mode")

def run_failure():
    # Failing simulation
    t=0
    seed = "\xe2\xbf\x20\x27"
    print "trail {:6} random.seed() = 0x{}".format(t, binascii.hexlify(seed))
    random.seed(seed)
    run_trial(t, alice_reboot_at=10.0, bob_reboot_at=10.1)
    exit()

#run_failure()

# Simulations with only Alice rebooting
print "+++ Alice Failures"
for t in range(1, repeat_count + 1):
    seed = os.urandom(4)
    print "trail {:6} random.seed() = 0x{}".format(t, binascii.hexlify(seed))
    random.seed(seed)
    run_trial(t, alice_reboot_at=10.0, bob_reboot_at=0.0)

# Simulations with only Bob rebooting
print "+++ Bob Failures"
for t in range(repeat_count, 2*repeat_count + 1):
    seed = os.urandom(4)
    print "trail {:6} random.seed() = 0x{}".format(t, binascii.hexlify(seed))
    random.seed(seed)
    run_trial(t, alice_reboot_at=0.0, bob_reboot_at=10.0)

# Simulations with Alice rebooting, then Bob rebooting during Alice's reboot
print "+++ Alice and Bob Failures"
for t in range(2*repeat_count, 3*repeat_count + 1):
    seed = os.urandom(4)
    print "trail {:6} random.seed() = 0x{}".format(t, binascii.hexlify(seed))
    random.seed(seed)
    run_trial(t, alice_reboot_at=10.0, bob_reboot_at=10.1)
