import sys
import logging
import getopt

from fdtparser import FDTParser

# En mode simulation, on interroge FDT mais on n'effectue pas l'action
SIMULATION = True

# Surtout pour le logging
DEBUG = True

log = logging.getLogger()

fdt_parser = ""

# Actions

def PunchIn(fdt_parser):
    state = fdt_parser.getCurrentState()
    log.info("Current state: " + state)

    if state == '60':
        fdt_parser.punchInDayStart()
    elif state == '20':
        fdt_parser.punchInBackFromLunch()
    else:
        log.error('Unrecognized state: ' + state + '. Already punched in?')


def PunchOut(fdt_parser):
    log.info("Punching out ...")
    state = fdt_parser.getCurrentState()
    log.info("Current state: " + state)
    if state == '1':
        fdt_parser.punchOutLunch()
    elif state == '30':
        fdt_parser.punchOutDayEnd()
    else:
        log.error('Unrecognized state: ' + state + '. Already punched out?')
    state = fdt_parser.getCurrentState()
    log.info("New state: " + state)


def InitLogging():
    log.setLevel(logging.DEBUG)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    log.addHandler(ch)

def main(argv):
    action = ''
    username = ''
    password = ''

    usage = 'zerodt.py -u <username> -p <password> -a <action>'
    try:
        opts, args = getopt.getopt(argv, "hu:p:a:", ["username=", "password=", "action="])
    except getopt.GetoptError:
        print(usage)
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print(usage)
            sys.exit()
        elif opt in ("-u", "--username"):
            username = arg
        elif opt in ("-p", "--password"):
            password = arg
        elif opt in ("-a", "--action"):
            action = arg

    InitLogging()

    if SIMULATION:
        log.warning('**** SIMULATION *** SIMULATION ***')

    fdt_parser = FDTParser("ccq", username, password, simulation=SIMULATION )
   
    if action.lower() == 'punchin':
        PunchIn(fdt_parser)
    elif action.lower() == 'punchout':
        PunchOut(fdt_parser)

if __name__ == '__main__':
    main(sys.argv[1:])
