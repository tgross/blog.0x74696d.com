import binascii
import sys

email_address = sys.argv[1]
print email_address
print ''.join(['&#{0};'.format(str(int(binascii.hexlify(char), 16)))
               for char in email_address])
