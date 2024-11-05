import xml.etree.ElementTree as xml
import sys, os, subprocess
from datetime import datetime
import pickle
from ctypes import *
import imp
import sys
import re
import math
import time
from collections import OrderedDict
from common.utils import *

print('Loading shared library: librwreg.so')
lib = CDLL("librwreg.so")
rReg = lib.getReg
rReg.restype = c_uint
rReg.argtypes = [c_uint]
wReg = lib.putReg
wReg.restype = c_uint
wReg.argtypes = [c_uint, c_uint]
regInitExists = False
try:
    regInit = lib.rwreg_init
    regInit.argtypes = [c_char_p, c_uint]
    regInitExists = True
except:
    print("WARNING: rwreg_init() function does not exist.. if you're running on CTP7, you can safely ignore this warning.")

DEBUG = True
nodes = OrderedDict()
val_cache = {}

boardType = os.environ.get('BOARD_TYPE')
boardIdx = int(os.environ.get('BOARD_IDX'))
DEVICE = get_config("CONFIG_RWREG")[boardType][boardIdx]['DEVICE']
if sys.version_info[0] == 3:
    DEVICE = get_config("CONFIG_RWREG")[boardType][boardIdx]['DEVICE'].encode()
BASE_ADDR = get_config("CONFIG_RWREG")[boardType][boardIdx]['BASE_ADDR']

class Node:
    name = ''
    local_name = ''
    description = ''
    vhdlname = ''
    local_address = 0x0
    address = 0x0
    permission = ''
    mask = 0x0
    mask_start_bit_pos = None
    isModule = False
    parent = None
    level = 0
    fw_signal = None
    fw_write_pulse_signal = None
    fw_read_pulse_signal = None
    fw_default = None
    sw_enum = None
    sw_val_good = None
    sw_val_bad = None
    sw_val_warn = None
    sw_val_neutral = None
    sw_units = None
    sw_to_string = None

    def __init__(self):
        self.children = []

    def add_child(self, child):
        self.children.append(child)

    def get_vhdl_name(self):
        return self.name.replace(TOP_NODE_NAME + '.', '').replace('.', '_')

    def print_info(self):
        print('Name: ' + self.name)
        print('Description: ' + self.description)
        print('Local Address: ' + '{0:#010x}'.format(self.local_address))
        print('Address: ' + '{0:#010x}'.format(self.address))
        print('Permission: ' + self.permission)
        print('Mask: ' + hex32(self.mask))
        print('Module: %r' % self.isModule)
        print('Parent: ' + self.parent.name)
        if self.fw_signal is not None:
            print("Firmware signal: %s" % self.fw_signal)
        if self.fw_write_pulse_signal is not None:
            print("Firmware write pulse signal: %s" % self.fw_write_pulse_signal)
        if self.fw_read_pulse_signal is not None:
            print("Firmware read pulse signal: %s" % self.fw_read_pulse_signal)
        if self.fw_default is not None:
            print("Firmware default: %s" % self.fw_default)

class RegVal(int):
    STATE_NEUTRAL = "NEUTRAL"
    STATE_GOOD = Colors.GREEN
    STATE_WARN = Colors.ORANGE
    STATE_BAD = Colors.RED

    reg = None

    # returns the state of the value based on sw_val_neutral, sw_val_bad, sw_val_good, and sw_val_warn attributes
    # neutral takes precedence above all others (can be a handy way to ignore the value when some configs indicate it's not relevant)
    # the rest are treated in this order: bad, warn, good (so if the value is determined bad or warn, it won't check the good expression)
    # note that if only sw_val_good is defined (sw_val_bad is not defined) and sw_val_good evaluates to False, BAD is returned (opposite of GOOD)
    # same goes if only sw_val_bad is defined (and sw_val_good is not defined) -- if sw_val_bad evals to False, GOOD is returned
    # if both sw_val_bad and sw_val_good are defined and both evaluate to False, NEUTRAL is returned
    def get_state(self):
        if self.reg.sw_val_neutral is not None and eval(self.reg.sw_val_neutral):
            return self.STATE_NEUTRAL
        elif self.reg.sw_val_bad is not None and eval(self.reg.sw_val_bad):
            return self.STATE_BAD
        elif self.reg.sw_val_warn is not None and eval(self.reg.sw_val_warn):
            return self.STATE_WARN
        elif self.reg.sw_val_good is not None and eval(self.reg.sw_val_good):
            return self.STATE_GOOD
        elif self.reg.sw_val_good is not None and self.reg.sw_val_bad is None:
            return self.STATE_BAD
        elif self.reg.sw_val_bad is not None and self.reg.sw_val_good is None:
            return self.STATE_GOOD
        elif self.reg.sw_val_warn is not None and self.reg.sw_val_good is None:
            return self.STATE_GOOD
        else:
            return self.STATE_NEUTRAL

    def to_string(self, hex=False, hex_padded32=True, use_color=True, bool_use_yesno=True):
        if self == 0xdeaddead:
            if use_color:
                return Colors.RED + "Bus Error" + Colors.ENDC
            else:
                return "Bus Error"

        val = ""
        if hex:
            if hex_padded32:
                val = "0x%08x" % self
            else:
                val = "0x%x" % self

        if self.reg.sw_to_string is not None:
            to_string_eval = eval(self.reg.sw_to_string)
            if hex:
                val += " (%s)" % to_string_eval
            else:
                val = to_string_eval
        elif self.reg.sw_enum is not None:
            enum_val = "UNKNOWN" if self >= len(self.reg.sw_enum) else self.reg.sw_enum[self]
            if hex:
                val += " (%s)" % enum_val
            else:
                val = enum_val
        elif self.reg.sw_units is not None:
            if len(self.reg.sw_units) == 0:
                if hex:
                    val += " (%d)" % self
                else:
                    val = "%d" % self
            elif "bool" == self.reg.sw_units.lower():
                if bool_use_yesno:
                    bool_val = "NO" if self == 0 else "YES"
                else:
                    bool_val = "FALSE" if self == 0 else "TRUE"

                if hex:
                    val += " (%s)" % bool_val
                else:
                    val = bool_val
            else:
                modifier = self.reg.sw_units[0]
                val_pretty = None
                if modifier == "G":
                    val_pretty = self / 1000000000.0
                elif modifier == "M":
                    val_pretty = self / 1000000.0
                elif modifier == "K":
                    val_pretty = self / 1000.0

                if val_pretty is None:
                    if hex:
                        val += " (%d%s)" % (self, self.reg.sw_units)
                    else:
                        val = "%d%s" % (self, self.reg.sw_units)
                else:
                    if hex:
                        val += " (%.3f%s)" % (val_pretty, self.reg.sw_units)
                    else:
                        val = "%.3f%s" % (val_pretty, self.reg.sw_units)
        elif not hex:
            val = "%d" % self

        if use_color:
            col = self.get_state()
            if col is not None and col != self.STATE_NEUTRAL:
                val = col + val + Colors.ENDC

        return val

    def __str__(self):
        return self.to_string()

def parse_xml():
    if regInitExists:
        regInit(DEVICE, BASE_ADDR)
    addressTable = os.environ.get('ADDRESS_TABLE')
    if addressTable is None:
        print_red("Environment variable ADDRESS_TABLE is not defined, exiting.. Please source the env.sh")
        exit()

    xml_modify_time = os.path.getmtime(addressTable)
    scripts_dir = os.environ.get("BEFE_SCRIPT_DIR")
    if scripts_dir is None:
        print_red("Environment variable BEFE_SCRIPT_DIR is not defined, exiting.. Please source the env.sh")
        exit()
    befe_flavor = os.environ.get("BEFE_FLAVOR")
    if befe_flavor is None:
        print_red("Environment variable BEFE_FLAVOR is not defined, exiting.. Please source the env.sh")
        exit()
    befe_board = os.environ.get("BOARD_TYPE")
    if befe_board is None:
        print_red("Environment variable BOARD_TYPE is not defined, exiting.. Please source the env.sh")
        exit()

    pickle_fname = scripts_dir + "/resources/" + befe_flavor + "_" + befe_board + "_address_table.pickle"
    pickle_exists = os.path.exists(pickle_fname)
    pickle_modify_time = os.path.getmtime(pickle_fname) if pickle_exists else 0

    global nodes

    t1 = time.time()

    if (not pickle_exists) or xml_modify_time > pickle_modify_time:
        if not pickle_exists:
            print("Address table pickle file doesn't exist, creating one..")
        else:
            print("XML modification time (UTC): %s" % datetime.utcfromtimestamp(xml_modify_time).strftime('%Y-%m-%d %H:%M:%S'))
            print("Pickle modification time (UTC): %s" % datetime.utcfromtimestamp(pickle_modify_time).strftime('%Y-%m-%d %H:%M:%S'))
            print("Address table pickle file is out of date, re-creating..")

        print('Parsing XML: ' + addressTable + '...')
        tree = None
        lxmlExists = False
        try:
            imp.find_module('lxml')
            import lxml.etree
            lxmlExists = True
        except:
            print("WARNING: lxml python module was not found, so xinclude won't work.. Also will not create a pickle file..")

        if lxmlExists:
            tree = lxml.etree.parse(addressTable)
            try:
                tree.xinclude()
            except Exception as e:
                print(e)
                exit()
        else:
            tree = xml.parse(addressTable)

        root = tree.getroot()
        vars = {}
        make_tree(root, '', 0x0, nodes, None, vars, False)

        # pickle the nodes
        pickle_file = open(pickle_fname, 'wb')
        pickle.dump(nodes, pickle_file)
        pickle_file.close()
        print("Pickle file created: %s" % pickle_fname)

    else:
        print("Loading address table pickle file: %s" % pickle_fname)
        pickle_file = open(pickle_fname, 'rb')
        nodes = pickle.load(pickle_file)
        pickle_file.close()

    t2 = time.time()
    print("Parsing done, took %fs. Total num register nodes: %d" % ((t2 - t1), len(nodes)))

# returns the position of the first set bit
def find_first_set_bit_pos(n):
    return int(math.log(n & -n, 2))

def make_tree(node, baseName, baseAddress, nodes, parentNode, vars, isGenerated):

    if node.get('id') is None or (node.get('ignore') is not None and eval(node.get('ignore')) == True):
        return

    if (isGenerated is None or isGenerated == False) and node.get('generate') is not None and node.get('generate') == 'true':
        generateSize = parse_int(node.get('generate_size'))
        generateAddressStep = parse_int(node.get('generate_address_step'))
        generateIdxVar = node.get('generate_idx_var')
        for i in range(0, generateSize):
            vars[generateIdxVar] = i
            make_tree(node, baseName, baseAddress + generateAddressStep * i, nodes, parentNode, vars, True)
        return
    newNode = Node()
    newNode.local_name = substitute_vars(node.get('id'), vars)
    name = baseName
    if baseName != '':
        name += '.'
    name += node.get('id')
    name = substitute_vars(name, vars)
    newNode.name = name
    if node.get('description') is not None:
        newNode.description = node.get('description')
    address = baseAddress
    if node.get('address') is not None:
        address = baseAddress + parse_int(node.get('address'))
    newNode.local_address = address
    newNode.address = (address << 2)
    newNode.permission = node.get('permission')
    if newNode.permission is None:
        newNode.permission = ""
    newNode.mask = parse_int(node.get('mask'))
    if newNode.mask is not None:
        newNode.mask_start_bit_pos = find_first_set_bit_pos(newNode.mask)
    newNode.isModule = node.get('fw_is_module') is not None and node.get('fw_is_module') == 'true'
    if node.get('fw_signal') is not None:
        newNode.fw_signal = substitute_vars(node.get('fw_signal'), vars)
    if node.get('fw_default') is not None:
        newNode.fw_default = substitute_vars(node.get('fw_default'), vars)
    if node.get('fw_write_pulse_signal') is not None:
        newNode.fw_write_pulse_signal = substitute_vars(node.get('fw_write_pulse_signal'), vars)
    if node.get('fw_read_pulse_signal') is not None:
        newNode.fw_read_pulse_signal = substitute_vars(node.get('fw_read_pulse_signal'), vars)
    if node.get('sw_enum') is not None:
        newNode.sw_enum = eval(node.get('sw_enum'))
    if node.get('sw_val_good') is not None:
        newNode.sw_val_good = substitute_vars(node.get('sw_val_good'), vars)
    if node.get('sw_val_bad') is not None:
        newNode.sw_val_bad = substitute_vars(node.get('sw_val_bad'), vars)
    if node.get('sw_val_warn') is not None:
        newNode.sw_val_warn = substitute_vars(node.get('sw_val_warn'), vars)
    if node.get('sw_val_neutral') is not None:
        newNode.sw_val_neutral = substitute_vars(node.get('sw_val_neutral'), vars)
    if node.get('sw_units') is not None:
        newNode.sw_units = node.get('sw_units')
    if node.get('sw_to_string') is not None:
        newNode.sw_to_string = substitute_vars(node.get('sw_to_string'), vars)
    nodes[newNode.name] = newNode
    if parentNode is not None:
        parentNode.add_child(newNode)
        newNode.parent = parentNode
        newNode.level = parentNode.level + 1
    for child in node:
        make_tree(child, name, address, nodes, newNode, vars, False)


def get_all_children(node, kids=[]):
    if node.children == []:
        kids.append(node)
        return kids
    else:
        for child in node.children:
            get_all_children(child, kids)

def get_node(nodeName):
    thisnode = None
    if nodeName in nodes:
        thisnode = nodes[nodeName]
    if (thisnode is None):
        print_red("ERROR: %s does not exist" % nodeName)
    return thisnode

def get_node_from_address(nodeAddress):
    return next((nodes[nodename] for nodename in nodes if nodes[nodename].address == nodeAddress), None)

def get_nodes_containing(node_string):
    if "*" in node_string: # use regexp if it contains wildcards
        # escape dots, and replace * with .+ (match at least one random char)
        node_string = node_string.replace(".", "\\.")
        node_string = node_string.replace("*", ".+")
        # add wildcards to the beginning and the end
        node_string = ".*" + node_string + ".*"
        # match
        pattern = re.compile(node_string)
        nodelist = [nodes[nodename] for nodename in nodes if pattern.match(nodename)]
        # nodelist = [nodes[nodename] for nodename in nodes if re.match(node_string, nodename)]
    else:
        nodelist = [nodes[nodename] for nodename in nodes if node_string in nodename]

    if len(nodelist):
        return nodelist
    else:
        return None

def read_address(address):
    return rReg(address)

# returns RegVal, which is a subclass of int, so it can be used as regular int, but also contains a reference to the node, and when converted to string returns a string with a green/red/yellow color if sw_val_good/sw_val_bad/sw_val_warn is defined, and if it's an enum it will also display the enum value
def read_reg(reg, verbose=True):
    if isinstance(reg, str):
        reg = get_node(reg)

    if 'r' not in reg.permission:
        print_red("No read permission for register %s" % reg.name)
        return RegVal(0xdeaddead, reg)
    
    val = rReg(reg.address)

    if val == 0xdeaddead:
        if verbose:
            print_red("Bus error while reading %s" % reg.name)
    elif reg.mask is not None:
        val = (val & reg.mask) >> reg.mask_start_bit_pos
    #---
    val = RegVal(val)
    val.reg = reg
    
    return val

# this method reads the register if it doesn't exist in cache, but all subsequent calls will return the cached value -- use very cautiously, if in doubt always use the readReg function instead!
# this should only be used on regs that never change, like config regs
# it's mostly intended to speed up sw_val_good/sw_val_bad/sw_val_warn evals that require looking up configuration values
def read_reg_cache(reg):
    if isinstance(reg, Node):
        reg = reg.name
    if reg not in val_cache:
        val = read_reg(reg)
        val_cache[reg] = val
        return val

    return val_cache[reg]


def display_reg(reg, option=None):
    val = read_reg(reg, False)
    str_val = val.to_string(hex=True, hex_padded32=True)
    return hex32(reg.address).rstrip('L') + ' ' + reg.permission + '\t' + tab_pad(reg.name, 10) + str_val

def write_reg(reg, value):
    if isinstance(reg, str):
        reg = get_node(reg)
    if 'w' not in reg.permission:
        print_red("No write permission for register %s" % reg.name)
        return -1

    # Apply Mask if applicable
    val32 = value
    if reg.mask is not None:
        val_shifted = value << reg.mask_start_bit_pos
        val32 = rReg(reg.address)
        val32 = (val32 & ~reg.mask) | (val_shifted & reg.mask)
    ret = wReg(reg.address, val32)
    if ret < 0:
        print_red("Bus error while writing to %s" % reg.name)
        return -1
    return 0

def complete_reg(string):
    possibleNodes = []
    completions = []
    currentLevel = len([c for c in string if c == '.'])

    possibleNodes = [nodes[nodename] for nodename in nodes if nodename.startswith(string) and nodes[nodename].level == currentLevel]
    if len(possibleNodes) == 1:
        if possibleNodes[0].children == []:
            return [possibleNodes[0].name]
        for n in possibleNodes[0].children:
            completions.append(n.name)
    else:
        for n in possibleNodes:
            completions.append(n.name)
    return completions

def dump_regs(pattern, only_dump_bad_values=True, caption=None, caption_color=Colors.CYAN):
    if caption is not None:
        totalWidth = 100
        if len(caption) + 6 > totalWidth:
            totalWidth = len(caption) + 6
        print(caption_color + "=" * totalWidth + Colors.ENDC)
        padding1Size = int(((totalWidth - 2 - len(caption)) / 2))
        padding2Size = padding1Size if padding1Size * 2 + len(caption) == totalWidth - 2 else padding1Size + 1
        print(caption_color + "%s %s %s" % ("=" * padding1Size, caption, "=" * padding2Size) + Colors.ENDC)
        print(caption_color + "=" * totalWidth + Colors.ENDC)

    nodes = get_nodes_containing(pattern)
    for node in nodes:
        if node.permission is not None and 'r' in node.permission:
            val = read_reg(node)
            if not only_dump_bad_values or val.get_state() not in [RegVal.BAD, RegVal.WARN]:
                print(val.to_string(hex=True))

def substitute_vars(string, vars):
    if string is None:
        return string
    ret = string
    for varKey in vars.keys():
        ret = ret.replace('${' + varKey + '}', str(vars[varKey]))
    return ret

def tab_pad(s, maxlen):
    return s + "\t" * int((8 * maxlen - len(s) - 1) / 8 + 1)

if __name__ == '__main__':
    #parse_xml()
    pass
