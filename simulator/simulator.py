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

import heapq
import sys


class Simulator(object):
    """
    Discrete event simulator

    You schedule events with the schedule() function then run the
    simulator.  You can run until there are no more events or you can
    run until a particular simulated time.

    Simulation time is a float that represents seconds, though the scale
    is really irrelevant.
    """
    VERBOSE = False
    EXTRA_VERBOSE = False

    def __init__(self):
        self._time = 0
        self._priority_queue = []

        # total number of events executed
        self._event_count = 0

        # If we want to stop the simulator at a given time
        self._stop_time = 0
        self._use_stop_time = False

        # if we want to stop the simulator after a certain number of events
        self._use_stop_count = False
        self._stop_count_end = 0

        self._running = False

    @property
    def now(self):
        return self._time

    def schedule(self, event):
        expiry = self._time + event.delay
        heapq.heappush(self._priority_queue, (expiry, event))

    def run_until(self, stop_time):
        """
        Runs the simulator until the stopping time is reached or there
        are no more events.

        :param stop_time: The time to stop at, even if there are still events (float)
        :return:
        """
        if self._running: raise RuntimeError("Cannot call a run function while already running")

        self._use_stop_time = True
        self._stop_time = stop_time
        self.run()

    def run_count(self, stop_count):
        """
        Run for a specific number of events
        :param stop_count: The number of events to run
        :return:
        """
        self._use_stop_count = True
        self._stop_count_end = self._event_count + stop_count
        self.run()

    def run(self):
        """
        Runs the simulator until there are no more events.
        :return:
        """
        if self._running: raise RuntimeError("Cannot call a run function while already running")
        self._running = True

        try:
            while len(self._priority_queue) > 0:
                t, event = heapq.heappop(self._priority_queue)
                if Simulator.EXTRA_VERBOSE:
                    print "{:>12.9f} Stepping simulation time to {:>12.9f}".format(self._time, t)

                self._time = t

                # check for termination conditions
                if self._use_stop_time and self._stop_time <= self._time:
                    break

                if self._use_stop_count and self._stop_count_end <= self._event_count:
                    break

                if Simulator.EXTRA_VERBOSE:
                    print "{:>12.9f} Executing event {}".format(t, event)

                if event.active:
                    self._event_count += 1
                    event.callback(event.data)
        except Exception as e:
            sys.stdout.flush()
            print "FOO"
            print e
            raise

        print "{:>12.9f} simulation stopping ({} still in queue, {} events executed)".format(
            self._time, len(self._priority_queue), self._event_count)

        self._running = False
