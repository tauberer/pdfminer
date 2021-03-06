#!/usr/bin/env python2
""" Python implementation of Arcfour encryption algorithm.

This code is in the public domain.

"""


class Arcfour(object):
    """Python implementation of Arcfour encryption algorithm.

    Example:

        Arcfour('Key').process('Plaintext').encode('hex')

    """

    def __init__(self, key):
        s = list(range(256))
        j = 0
        klen = len(key)
        for i in range(256):
            j = (j + s[i] + ord(key[i % klen])) % 256
            (s[i], s[j]) = (s[j], s[i])
        self.s = s
        (self.i, self.j) = (0, 0)

    def process(self, data):
        (i, j) = (self.i, self.j)
        s = self.s
        r = ''
        for c in data:
            i = (i + 1) % 256
            j = (j + s[i]) % 256
            (s[i], s[j]) = (s[j], s[i])
            k = s[(s[i] + s[j]) % 256]
            r += chr(ord(c) ^ k)
        (self.i, self.j) = (i, j)
        return r
