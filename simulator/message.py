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

import abc


class Message(object):
    """
    Base class for messages exchnaged in the simulator
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        pass


class Fragment(Message):
    """
    A fragmentation unit.  Implements the abstract syntax in the RFC draft.
    """
    FLAG_B  = 1
    FLAG_E  = 2
    FLAG_BE = FLAG_B | FLAG_E
    FLAG_I  = 4

    def __init__(self, sender, flags, fragment_id, frag_length, frag_data):
        super(Fragment, self).__init__()
        self._sender = sender
        self._flags = flags
        self._fragment_id = fragment_id
        self._frag_length = frag_length
        self._frag_data = frag_data

    @property
    def is_idle(self):
        return self._flags & Fragment.FLAG_I == Fragment.FLAG_I

    @property
    def is_begin(self):
        return self._flags & Fragment.FLAG_B == Fragment.FLAG_B

    @property
    def is_end(self):
        return self._flags & Fragment.FLAG_E == Fragment.FLAG_E

    @property
    def is_reset(self):
        return self.is_idle and isinstance(self, FragReset)

    @property
    def is_resetack(self):
        return self.is_idle and isinstance(self, FragResetAck)


class FragReset(Fragment):
    """
    A fragmentation reset message in a Fragment
    """
    def __init__(self, sender, reset_number):
        '''

        :param sender:
        :param reset_number: The number to advertise as our reset number
        '''
        super(FragReset, self).__init__(sender, Fragment.FLAG_I, 0, 0, reset_number)

    @property
    def reset_number(self):
        return self._frag_data


class FragResetAck(Fragment):
    """
    A fragmentation reset ACK message in a Fragment
    """
    def __init__(self, sender, reset_number, ack_number):
        """

        :param sender:
        :param reset_number: The number to advertise as our reset number
        :param ack_number: The number we are ACKing from the peer
        """
        super(FragResetAck, self).__init__(sender, Fragment.FLAG_I, 0, 0, (reset_number, ack_number))

    @property
    def reset_number(self):
        reset_number, ack_number = self._frag_data
        return reset_number

    @property
    def ack_number(self):
        reset_number, ack_number = self._frag_data
        return ack_number


Message.register(Fragment)
Fragment.register(FragReset)
Fragment.register(FragResetAck)
