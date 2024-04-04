#brailleDisplayDrivers/pactos_old.py
#A part of NonVisual Desktop Access (NVDA)
#This file is covered by the GNU General Public License.
#See the file COPYING for more details.
#Copyright (C) 2012-2015 NV Access Limited

# -*-coding: utf-8 -*-

import os
import itertools
import serial
import hwPortUtils
import braille
import inputCore
from logHandler import log
from baseObject import ScriptableObject
import brailleInput
import brailleTables
import hwIo
from hwIo import intToByte
import config
import codecs
#import ast 
#import win32api
import winUser 
import threading
import time
from ctypes import *
import ctypes.util
import struct
import operator
import speech
import globalVars
import shutil
from sys import path as syspath
from os import path as ospath

#Addon consts
ADDON_NAME = "pactos"
PLUGIN_DIR = os.path.abspath(os.path.join(globalVars.appArgs.configPath, "addons",ADDON_NAME))

syspath.append(ospath.join(PLUGIN_DIR, r"bjSettings\lib.win32-3.7"))
syspath.append(ospath.join(PLUGIN_DIR, r"bjSettings"))

import bluetooth
import paGlobals

try:
	pactosLib = cdll.LoadLibrary(os.path.join(PLUGIN_DIR,"bjSettings","PactosBD.dll"))
except:
	pactosLib = None

user32=windll.user32

TIMEOUT = 0.2
BAUD_RATE = 115200
PARITY = serial.PARITY_NONE

# Serial
HEADER = "\x1b"
MSG_INIT = "\x00"
MSG_INIT_RESP = "\x01"
MSG_DISPLAY = "\x02"
MSG_KEY_DOWN = "\x05"
MSG_KEY_UP = "\x06"

# HID
HR_CAPS = "\x01"
HR_KEYS = "\x04"
HR_BRAILLE = "\x05"
HR_POWEROFF = "\x07"

BUFFER_SIZE_CDC = 32
BUFFER_SIZE_HID = 64

IDEN_REQ_HID ="\x00"*BUFFER_SIZE_HID + "\x82"
RESET_REQ ="\x00"*56 + "\x26" + "\x00"*8

IDEN_REQ_CDC ="\x00"*(BUFFER_SIZE_CDC-1) + "\x82"

KEY_NAMES = {
	# Braille keyboard.
	2: "dot1",
	3: "dot2",
	4: "dot3",
	5: "dot4",
	6: "dot5",
	7: "dot6",
	8: "space",
	# Command keys.
	9: "BackSpace",
	10: "Up",
	11: "Down",
	12: "LeftScroll",
	13: "RightScroll",
	14: "Enter",
	15: "Left",
	16: "Right",
	17: "LSpace",

}

FIRST_ROUTING_KEY = 100
DOT1_KEY = 2
DOT6_KEY = 7

SPACE_KEY1 = 8
SPACE_KEY2 = 17

pac_curr_lang = "en"

#### copy tables into nvda path  ###
table_names = ["ar-fa.utb", "en-us-g1.ctb", "ar-ar-g1.utb", "fa-ir-g1.utb", "braille-patterns.cti", "chardefs.cti"]

dst1 = "C:\\Program Files(x86)\\NVDA\\louis\\tables\\ar-fa.utb"
dst = "C:\\Program Files (x86)\\NVDA\\louis\\tables"


for table in table_names:
	try: 
		shutil.copy2(os.path.join(PLUGIN_DIR,"bjSettings",table), dst)
	except:
		log.info("pactos driver : can not copy tables!")


class BrailleDisplayDriver(braille.BrailleDisplayDriver,ScriptableObject):
	"""pactos_old driver.
	"""
	name = "pactos_old"
	# Translators: The name of a series of braille displays.
	description = _("Pactos_old")
	isThreadSafe = True
	
	@classmethod
	def check(cls):
		return bool(pactosLib)

	def mdev_read(self):
			
		multiOR = lambda a,b: map(operator.or_,a,b)
		multiAND = lambda a,b: map(operator.and_,a,b)
		is_20 = (self.numCells == 20)
		base_buf = [0xff,0x14,0,0,0,0,0,1] if is_20 else [0xff,0x28,0,0,0,0,0,1]
		null_buf = [0xff,0,0,0,0,0,0,0]
		counterr = 3
		while not self.stop_event.isSet():
			read_count = pactosLib.BrdReadData(0,8,self.in_buff)
			input = [ord(n) for n in self.in_buff]
			#base_bus = [n for n in base_buf]
			#finalBuff = str1 
			#log.info("*******************   str1 = %r " % str1)
			#log.info("*******************   str2 = %r " % str2)
			if input == base_buf or input == null_buf or input[1] != base_buf[1] or input[7] != 1:
				continue
				
			time.sleep(0.02)
			read_count = pactosLib.BrdReadData(0,8,self.in_buff)
			log.info("OMGOMGOGMGOGMGO -=-=-=-=- MESSAGE RECIVED == %r " % self.in_buff.raw)
			input = [ord(n) for n in self.in_buff]
			if input == base_buf or input == null_buf or input[1] != base_buf[1] or input[7] != 1:
				continue
			#finalBuff = list(multiAND(finalBuff[:2],str1[:2])) + list(multiOR(finalBuff[2:],str1[2:]))
			log.info("////////////////////////// %r " % input)
			self._hidOnReceive(input)
			
			time.sleep(0.2)
			#log.info("OMGOMGOGMGOGMGO -=-=-=-=- MESSAGE RECIVED == %r " % self.bt_buff)
			#log.info("bluetooth data ----->>>>> %r" % self.in_buff)

	def sync_keyboards(self):
		w = user32.GetForegroundWindow() 
		tid = user32.GetWindowThreadProcessId(w, 0) 
		lid = user32.GetKeyboardLayout(tid)
		log.info("-----------> Lang ID1 == %r" %  lid)
		#langId = hex(win32api.GetKeyboardLayout(0))
		log.info("-----------> Lang ID2 == %r" % langId)
		if lid == 69796905 or lid == -255851479:
			log.info("**** TABLE CHANGED TO FA!")
			config.conf["braille"]["inputTable"]="ar-fa.utb"
			config.conf["braille"]["translationTable"]="ar-fa.utb"
			braille.handler.update()
			paGlobals.pac_curr_lang = "fa"
		else:
			log.info("**** TABLE CHANGED TO EN!")
			config.conf["braille"]["inputTable"]="en-gb-g1.utb"
			config.conf["braille"]["translationTable"]="en-gb-g1.utb"
			braille.handler.update()
			paGlobals.pac_curr_lang = "en"


	def __init__(self):
		super(BrailleDisplayDriver, self).__init__()
		self.numCells = 20
		self.mdev_read_thread = threading.Thread(target=self.mdev_read)
		self.stop_event = threading.Event()
		self.reorder = False
		self.is_B8 = False
		self.isMod78 = False
		self.in_buff = create_string_buffer(8)

		paGlobals.search_bluetooth = False
		iniFilePath = os.path.join(PLUGIN_DIR,"bjSettings","configs.ini")
		iniFile = open(iniFilePath,"r")
		for line in iniFile:
			if line.startswith(codecs.BOM_UTF8.decode()):
				line = line[3:]
			#line = line[:-1]
			vals = str.split(line,"=")
			#log.info("VALS ----------->")
			#print vals
			#log.info("VALS <-----------")
			if "reorder" in vals[0]:
				if vals[1]=="" or vals[1].startswith('0'):
					self.reorder = False
				else:
					self.reorder = True
			if "bt_name" in vals[0]:
				if vals[1]=="" or vals[1].startswith('0'):
					paGlobals.search_bluetooth = False
				else:
					paGlobals.search_bluetooth = True
					paGlobals.bluetooth_device_name = vals[1].rstrip()
			if "lang1" in vals[0]:
				if vals[1]=="" or vals[1].startswith('0'):
					paGlobals.lang1 = "fa-ir-g1.utb"
				else:
					paGlobals.lang1 = vals[1].rstrip()
			if "lang2" in vals[0]:
				if vals[1]=="" or vals[1].startswith('0'):
					paGlobals.lang2 = "en-us-g1.ctb"
				else:
					paGlobals.lang2 = vals[1].rstrip()

		iniFile.close()
		
		#self.sync_keyboards()
		if pactosLib is None:
			log.info("++++++++++++++   Metec Lib not found!")
			return
		devs = create_string_buffer(1300)
		nOfDevices = pactosLib.BrdEnumDevice(devs, sizeof(devs))
		if nOfDevices > 0  :
			log.info("_+_+_+_+_+_+_+_+_+_+_   METEC METEC +++++ found %r devices ++++++ " % nOfDevices)
			log.info("+_+_+_+_+_+_+_+_+_+  %r +_+_+_+_+_+_+_+_+_" % devs.raw.decode('ascii'))
			if "B8" in devs.raw.decode('ascii'):
				self.is_B8 = True 
			devtype = c_int()
			if pactosLib.BrdInitDevice(0,byref(devtype)) >= 0 :
				log.info("_+_+_+_+_+_+_+_+_+_+ PACMEC initialization done.")
				read_count = pactosLib.BrdReadData(0,8,self.in_buff)
				if read_count >=8:
					log.info("_+_+_+_+_+_+_+_+_+_+ data : %r" % self.in_buff.raw)
					self.numCells = ord(self.in_buff[1])
				else:
					log.info("Can't read from device!")
				self.mdev_read_thread.start()
			else:
				raise RuntimeError("Can't init device!")
		else:
			raise RuntimeError("No display found")

		if self.numCells == 20:
			paGlobals.gestures_file = "gestures_bj3.ini"
			paGlobals.commands_file = "commands_bj3.ini"
		else:
			paGlobals.gestures_file = "gestures_bj2.ini"
			paGlobals.commands_file = "commands_bj2.ini"
			
		self.read_gestures()
		self.read_commands()
		
		self._keysDown = set()
		self._ignoreKeyReleases = False

	def terminate(self):
		try:
			super(BrailleDisplayDriver, self).terminate()
			self.stop_event.set()
			self.mdev_read_thread.join()
		finally:
			# Make sure the device gets closed.
			# If it doesn't, we may not be able to re-open it later.
			#self._dev.write(RESET_REQ)
			pactosLib.BrdCloseDevice(0)

	def define_dotUni_map(self, required_keys):
		d1 = required_keys[0];
		d2 = required_keys[1];
		d3 = required_keys[2];
		d4 = required_keys[3];
		d5 = required_keys[4];
		d6 = required_keys[5];
		d7 = required_keys[6];
		d8 = required_keys[7];
		Enter = required_keys[8];
		BackSpace = required_keys[9];
		Control = required_keys[10];
		Space = required_keys[11];

		maps = {
			(d3|d6|d7): u'\u2212',
			(d5|d7): u'\u0022',
			(d1|d2|d3|d4|d6|d8): u'\u0026',
			(d2|d3|d5|d6|d8): u'\u0029',
			(d2|d3|d5|d6|d7): u'\u0028',
			(d1|d4|d6|d8): u'\u0025',
			(d2|d3|d5|d8): u'\u002b',
			(d2|d3|d6|d8): u'\u002a',
			(d3|d4|d8): u'\u002f',
			(d1|d2|d4|d6|d7|d8): u'\u0024',
			(d1|d3|d5|d7|d8): u'\u003e',
			(d2|d4|d6|d7|d8): u'\u003c',
			(d1|d2|d5|d6|d8): u'\u005c',
			(d1|d2|d3|d7|d8): u'\u00a3',
			(d1|d3|d4|d5|d6|d7|d8): u'\u00a5',
			(d1|d3|d4|d6|d7|d8): u'\u00a9',
			(d3|d4|d5|d6|d8): u'\u00b0',
			(d1|d3|d4|d5|d7|d8): u'\u00ac',
			(d2|d3|d4|d5|d7|d8): u'\u00ae',
			(d4|d5|d6|d7|d8): u'\u00b6',
			(d2|d4|d6|d8): u'\u2022',
			(d4|d6|d8): u'\u2026',
			(d2|d7): u'\u064e',
			(d2|d5|d7): u'\u0652',
			(d4|d5|d6|d8): u'\u007c',
			(d3|d4|d6|d8): u'\u005e',
			(d4|d8): u'\u0048',
			(d1|d2|d3|d5|d6|d7): u'\u005b',
			(d2|d3|d4|d5|d6|d8): u'\u005d',
			(d2|d3|d6|d7): u'\u00ab',
			(d3|d5|d6|d8): u'\u00bb',
			(d3|d6|d8): u'\u201c',
			(d6|d7|d8): u'\u201d',
			(d3|d5|d8): u'\u25e6',
			(d2|d3|d7): u'\u061b',
			(d3|d4|d7): u'\u0625',
			(d1|d3|d6|d7|d8): u'\u20ac',
		}

		return maps

			
	def _hidOnReceive(self, data):
		
		#self.sync_keyboards()
		byte1 = data[0]
		byte2 = data[1]
		byte3 = data[2]
		byte4 = data[3]

		is_20 = (self.numCells == 20)

		log.info("#################### byte1 == %r ##############" % byte1)

		d1 = 0x0002; d2 = 0x0008; d3 = 0x0020; d4 = 0x0001; d5 = 0x0004; d6 = 0x0010; 
		Enter = 0x0080; BackSpace = 0x0040; Control = 0x0400; Space = 0x0100;
		
		if is_20:
			d7 = 0x0200
			d8 = 0x0100
			d9 = 0x0800
			d10 = 0x0400
			InputGesture.d7 = 8
			InputGesture.d8 = 9
		else:
			d7 = 0x0100
			d8 = 0x0400
			d9 = 0x0080
			d10 = 0x0040 
			InputGesture.d7 = 17
			InputGesture.d8 = 8

		required_keys = [d1, d2, d3, d4, d5, d6, d7, d8, Enter, BackSpace, Control, Space]
		key2uni_map = self.define_dotUni_map(required_keys)

		keys = byte4 | (byte3 << 8)
		log.info("#################### keys == %r ##############" % keys)
		
		change_lang_keys = (d7 | d8 | d10) if is_20 else (d8 | d9 | d10)
		activate_mod78 = (d7 | d3) 
		deactivate_mod78 = (d8 | d6)
		
		if keys == change_lang_keys:
			self.change_keyboard_lang()
			return

		if not self.isMod78  and keys == activate_mod78:
			self.isMod78 = True
			speech.speakMessage(u"ورود به حالت ۸ نقطه",2)
			return
		if self.isMod78  and keys == deactivate_mod78:
			self.isMod78 = False
			speech.speakMessage(u"خروج از حالت ۸ نقطه",2)
			return

		if self.isMod78 and (keys in key2uni_map):
			brailleInput.handler.sendChars(key2uni_map[keys])
			return
			
		if keys == (d7 | d2):
			brailleInput.handler.sendChars(u'\u060c')
			return
		if keys == (d7 | d2 | d5):
			brailleInput.handler.sendChars(u'\u003a')
			return
		if keys == (d7 | d4):
			brailleInput.handler.sendChars(u'\u0040')
			return
		if keys == (d7 | d2 | d3):
			brailleInput.handler.sendChars(u'\u003b')
			return
		#if keys == (d7 | d2 | d5 | d6):
		#	brailleInput.handler.sendChars(u'\u0024')
		#	return
		#if keys == (d7 | d8 | d2 | d5):
		#	brailleInput.handler.sendChars(u'\u0025')
		#	return
		#if keys == (d8 | d3 | d4 | d6):
		#	brailleInput.handler.sendChars(u'\u005e')
		#	return
		if keys == (d7 | d4 | d5 | d6):
			brailleInput.handler.sendChars(u'\u005f')
			return
		#if keys == (d8 | d1 | d2 | d3 | d4 | d6):
		#	brailleInput.handler.sendChars(u'\u0026')
		#	return
		#if keys == (d7 | d3 | d5):
		#	brailleInput.handler.sendChars(u'\u002a')
		#	return
		if keys == (d8 | d2 | d3 | d6):
			brailleInput.handler.sendChars(u'\u00d7')
			return
		#if keys == (d8 | d2 | d3 | d5):
		#	brailleInput.handler.sendChars(u'\u002b')
		#	return
		if keys == (d8 | d3 | d6):
			brailleInput.handler.sendChars(u'\u002d')
			return
		#if keys == (d8 | d3 | d4):
		#	brailleInput.handler.sendChars(u'\u002f')
		#	return
		#if keys == (d8 | d2):
		#	if config.conf["braille"]["inputTable"]=="ar-fa.utb":
		#		brailleInput.handler.sendChars(u'\u002f')
		#		return 
		if keys == (d8 | d2 | d3 | d5 | d6):
			brailleInput.handler.sendChars(u'\u003d')
			return
		#if keys == (d7 | d3 | d6):
		#	brailleInput.handler.sendChars(u'\u200c')
		#	return
		if keys == (d7 | d8 | d6):
			brailleInput.handler.sendChars(u'\u2013')
			return
		if keys == (d7 | d8 | d5 | d6):
			brailleInput.handler.sendChars(u'\u2014')
			return
		if keys == (d8 | d1 | d4 | d6):
			brailleInput.handler.sendChars(u'\u221a')
			return
		#if keys == (d8 | d1 | d2 | d6):
		#	brailleInput.handler.sendChars(u'\u0028')
		#	return
		#if keys == (d10 | d2 | d4 | d6):
		#	brailleInput.handler.sendChars(u'\u003c')
		#	return
		#if keys == (d10 | d1 | d3 | d5):
		#	brailleInput.handler.sendChars(u'\u003e')
		#	return
		#if keys == (d8 | d3 | d4 | d5):
		#	brailleInput.handler.sendChars(u'\u0029')
		#	return
		#if keys == (d10 | d4 | d5):
		#	brailleInput.handler.sendChars(u'\u00a9')
		#	return
		#if keys == (d7 | d2 | d3 | d6):
		#	brailleInput.handler.sendChars(u'\u00ab')
		#	return
		#if keys == (d8 | d3 | d5 | d6):
		#	brailleInput.handler.sendChars(u'\u00b0')
		#	return
		#if keys == (d7 | d3 | d5 | d6):
		#	brailleInput.handler.sendChars(u'\u00bb')
		#	return
		#if keys == (d8 | d1 | d2 | d3 | d5 | d6):
		#	brailleInput.handler.sendChars(u'\u005b')
		#	return
		#if keys == (d7 | d1 | d6):
		#	brailleInput.handler.sendChars(u'\u005c')
		#	return
		#if keys == (d8 | d4 | d2 | d3 | d5 | d6):
		#	brailleInput.handler.sendChars(u'\u005d')
		#	return
		if keys == (d8 | d2 | d4 | d6):
			brailleInput.handler.sendChars(u'\u007b')
			return
		if keys == (d8 | d1 | d3 | d5):
			brailleInput.handler.sendChars(u'\u007d')
			return
		if keys == (d8 | d2 | d5 | d6):
			brailleInput.handler.sendChars(u'\u00f7')
			return
		if keys == (d8 | d2 | d4 | d5):
			if config.conf["braille"]["inputTable"]=="ar-fa.utb":
				brailleInput.handler.sendChars(u'\u06f0')
				return
			else:
				brailleInput.handler.sendChars(u'\u0030')
				return
		if keys == (d8 | d1):
			if config.conf["braille"]["inputTable"]=="ar-fa.utb":
				brailleInput.handler.sendChars(u'\u06f1')
				return
			else:
				brailleInput.handler.sendChars(u'\u0031')
				return
		if keys == (d8 | d1 | d2):
			if config.conf["braille"]["inputTable"]=="ar-fa.utb":
				brailleInput.handler.sendChars(u'\u06f2')
				return
			else:
				brailleInput.handler.sendChars(u'\u0032')
				return
		if keys == (d8 |d1 | d4):
			if config.conf["braille"]["inputTable"]=="ar-fa.utb":
				brailleInput.handler.sendChars(u'\u06f3')
				return
			else:
				brailleInput.handler.sendChars(u'\u0033')
				return
		if keys == (d8 | d1 | d4 | d5):
			if config.conf["braille"]["inputTable"]=="ar-fa.utb":
				brailleInput.handler.sendChars(u'\u06f4')
				return
			else:
				brailleInput.handler.sendChars(u'\u0034')
				return
		if keys == (d8 | d1 | d5):
			if config.conf["braille"]["inputTable"]=="ar-fa.utb":
				brailleInput.handler.sendChars(u'\u06f5')
				return
			else:
				brailleInput.handler.sendChars(u'\u0035')
				return
		if keys == (d8 | d1 | d2 | d4):
			if config.conf["braille"]["inputTable"]=="ar-fa.utb":
				brailleInput.handler.sendChars(u'\u06f6')
				return
			else:
				brailleInput.handler.sendChars(u'\u0036')
				return
		if keys == (d8 | d1 | d2 | d4 | d5):
			if config.conf["braille"]["inputTable"]=="ar-fa.utb":
				brailleInput.handler.sendChars(u'\u06f7')
				return
			else:
				brailleInput.handler.sendChars(u'\u0037')
				return
		if keys == (d8 | d1 | d2 | d5):
			if config.conf["braille"]["inputTable"]=="ar-fa.utb":
				brailleInput.handler.sendChars(u'\u06f8')
				return
			else:
				brailleInput.handler.sendChars(u'\u0038')
				return
		if keys == (d8 | d2 | d4):
			if config.conf["braille"]["inputTable"]=="ar-fa.utb":
				brailleInput.handler.sendChars(u'\u06f9')
				return
			else:
				brailleInput.handler.sendChars(u'\u0039')
				return

		tmpSet = set()
		if byte1 != 255:
			tmpSet.add(FIRST_ROUTING_KEY+byte1)
		#log.info("The keys value == %r" % keys)
		if keys & 0x0002:
			tmpSet.add(2)
		if keys & 0x0008:
			tmpSet.add(3)
		if keys & 0x0020:
			tmpSet.add(4)
		if keys & 0x0001:
			tmpSet.add(5)
		if keys & 0x0004:
			tmpSet.add(6)
		if keys & 0x0010:
			tmpSet.add(7)
		if keys & 0x0200:
			tmpSet.add(8 if is_20 else 15)
		if keys & 0x0100:
			tmpSet.add(9 if is_20 else 17)
		if keys & 0x0800:
			tmpSet.add(10 if is_20 else 16)
		if keys & 0x0400:
			tmpSet.add(11 if is_20 else 8)
		if keys & 0x2000:
			tmpSet.add(12 if is_20 else 11)
		if keys & 0x1000:
			tmpSet.add(13)
		if keys & 0x0040:
			tmpSet.add(9)
		if keys & 0x8000:
			tmpSet.add(10)
		if keys & 0x4000:
			tmpSet.add(12)
		if keys & 0x0080:
			tmpSet.add(14)

		self._keysDown = tmpSet
		log.info("keysDown --->>>> %r " % tmpSet)

		try:
			inputCore.manager.executeGesture(InputGesture(self._keysDown, self.isMod78))
		except inputCore.NoInputGestureAction:
			pass

		self._ignoreKeyReleases = True

	def _handleKeyRelease(self):
		if self._ignoreKeyReleases or not self._keysDown:
			return
		try:
			inputCore.manager.executeGesture(InputGesture(self._keysDown))
		except inputCore.NoInputGestureAction:
			pass
		# Any further releases are just the rest of the keys in the combination being released,
		# so they should be ignored.
		self._ignoreKeyReleases = True

	def swap_bits(self,bits,i,j,n):
		x = ((bits >> i) ^ (bits >> j)) & ((1 << n) - 1)
		r = bits ^ ((x << i) | (x << j));
		return r

	def reorder_cells(self,true_cells):
		#reordered_cells = struct.unpack('B',true_cells)
		reordered_cells = []
		for cell in true_cells:
			cell = self.swap_bits(cell,0,4,1)
			cell = self.swap_bits(cell,1,5,1)
			cell = self.swap_bits(cell,6,2,1)
			cell = self.swap_bits(cell,3,2,1)
			cell = self.swap_bits(cell,2,1,1)
			cell = self.swap_bits(cell,1,0,1)
			reordered_cells.append(cell)

		return "".join(chr(c) for c in reordered_cells)

	def display(self, cells):
		# cells will already be padded up to numCells.
		print(cells)
		if self.is_B8:
			cells = self.reorder_cells(cells)
		else:
			#Reverse the bit order of cells 
			#cells = b"".join(chr(int('{:08b}'.format(cell)[::-1],2)) for cell in cells)
			cells = b"".join(intToByte(int('{:08b}'.format(cell)[::-1], 2)) for cell in cells)
			#cells = ''.join(format(ord(x), 'b') for x in cells)
			log.info("+_+_+_+_+_+_+_   cells : %r +_+_+_+_+_+_+_+" % cells)
			#cells = b"".join([intToByte(x) for x in cells])
		pactosLib.BrdWriteData(0,len(cells),cells)

	def change_keyboard_lang(self):
		if(paGlobals.pac_curr_lang == "lang2"):
			#print win32api.GetKeyboardLayout(0)
			log.info(" +_+_+_+_+_+_+_+_+_+  ==> lang : %r <== +_+_+_+_+_+_+_+_+_+_+", paGlobals.lang1)
			config.conf["braille"]["inputTable"] = paGlobals.lang1 #brailleTables.RENAMED_TABLES["ar-fa.utb"]
			config.conf["braille"]["translationTable"] = paGlobals.lang1 #brailleTables.RENAMED_TABLES["ar-fa.utb"]
			brailleInput.handler.table = brailleTables.getTable(paGlobals.lang1)#brailleTables.RENAMED_TABLES["ar-fa.utb"])
#			braille.handler.update()
			#log.info("XXXXXXXXXXXX    before any keysym XXXXXXXXXXXXX")
			#winUser.keybd_event(0x12, 0xb8, 0x0000, 0)
			#log.info("XXXXXXXXXXXX    after alt press XXXXXXXXXXXXX")
			#winUser.keybd_event(0x10, 0x2a, 0x0000, 0)
			#log.info("XXXXXXXXXXXX    after shift press XXXXXXXXXXXXX")
			#winUser.keybd_event(0x10, 0x2a, 0x0002, 0)
			#log.info("XXXXXXXXXXXX    after shift release XXXXXXXXXXXXX")
			#winUser.keybd_event(0x12, 0xb8, 0x0002, 0)
			#log.info("XXXXXXXXXXXX    after alt release XXXXXXXXXXXXX")

			paGlobals.pac_curr_lang = "lang1"

			log.info("@@@@@@@@@@@@@@@@@@@@@@@ lang2 BOOD!!! @@@@@@@@@@@@@@@@")
			return
		#print win32api.GetKeyboardLayout(0)
		log.info(" +_+_+_+_+_+_+_+_+_+  ==> lang : %r <== +_+_+_+_+_+_+_+_+_+_+", paGlobals.lang2)
		config.conf["braille"]["inputTable"] = paGlobals.lang2 #"en-us-g1.ctb"
		config.conf["braille"]["translationTable"] = paGlobals.lang2 #"en-us-g1.ctb"
		brailleInput.handler.table = brailleTables.getTable(paGlobals.lang2) #"en-us-g1.ctb")
#		braille.handler.update()
		#log.info("XXXXXXXXXXXX    before any keysym (else) XXXXXXXXXXXXX")
		#winUser.keybd_event(0x12, 0xb8, 0x0000, 0)
		#log.info("XXXXXXXXXXXX    after alt press (else) XXXXXXXXXXXXX")
		#winUser.keybd_event(0x10, 0x2a, 0x0000, 0)
		#log.info("XXXXXXXXXXXX    after shift press (else) XXXXXXXXXXXXX")
		#winUser.keybd_event(0x10, 0x2a, 0x0002, 0)
		#log.info("XXXXXXXXXXXX    after shift release (else) XXXXXXXXXXXXX")
		#winUser.keybd_event(0x12, 0xb8, 0x0002, 0)
		#log.info("XXXXXXXXXXXX    after alt release (else) XXXXXXXXXXXXX")

		log.info("@@@@@@@@@@@@@@@@@@@@@@@ lang1 BOOD!!! @@@@@@@@@@@@@@@@")
		paGlobals.pac_curr_lang = "lang2"



	def script_changeInputTable(self, gesture):
		log.info("|||||||||||||||||||||||||||||---->> script_changeInputTable begins <<----|||||||||||||||||||||||||||||||||||")
		w = user32.GetForegroundWindow() 
		tid = user32.GetWindowThreadProcessId(w, 0) 
		print(hex(user32.GetKeyboardLayout(tid)))
		#global pac_curr_lang 
		if(paGlobals.pac_curr_lang == "en"):
			#print win32api.GetKeyboardLayout(0)
			config.conf["braille"]["inputTable"]="ar-fa.utb"
			config.conf["braille"]["translationTable"]="ar-fa.utb"
			winUser.keybd_event(0x12, 0xb8, 0x0000, 0)
			winUser.keybd_event(0x10, 0x2a, 0x0000, 0)
			winUser.keybd_event(0x10, 0x2a, 0x0002, 0)
			winUser.keybd_event(0x12, 0xb8, 0x0002, 0)

			paGlobals.pac_curr_lang = "fa"
			
			log.info("@@@@@@@@@@@@@@@@@@@@@@@ EN BOOD!!! @@@@@@@@@@@@@@@@")
			return
		#print win32api.GetKeyboardLayout(0)
		config.conf["braille"]["inputTable"]="en-gb-g1.utb"
		config.conf["braille"]["translationTable"]="en-gb-g1.utb"
		winUser.keybd_event(0x12, 0xb8, 0x0000, 0)
		winUser.keybd_event(0x10, 0x2a, 0x0000, 0)
		winUser.keybd_event(0x10, 0x2a, 0x0002, 0)
		winUser.keybd_event(0x12, 0xb8, 0x0002, 0)
		log.info("@@@@@@@@@@@@@@@@@@@@@@@ FA BOOD!!! @@@@@@@@@@@@@@@@")
		paGlobals.pac_curr_lang = "en"

	# Translators: Describes a command11.
	def read_gestures(self):
		iniFile = open(os.path.join(PLUGIN_DIR,"bjSettings",paGlobals.gestures_file),"r")
		tmpDic = dict()
		for line in iniFile:
			if line.startswith(codecs.BOM_UTF8.decode()):
				line = line[3:]
			#line = line[:-1]
			dic_els = str.split(line,":=")
			secEl = str.split(dic_els[1],",")
			secMap = list()
			for i in range(0,len(secEl)):
				secMap.append("br(pactos_old):"+''.join(str.split(secEl[i])[0])[3:])

			tmpDic[''.join(str(e) for e in secMap)] = str.split(dic_els[0])[0]

		self.__gestures = tmpDic
		
		iniFile.close()


	def read_commands(self):
		iniFile = open(os.path.join(PLUGIN_DIR,"bjSettings",paGlobals.commands_file),"r")
		tmpDic = dict()
		for line in iniFile:
			if line.startswith(codecs.BOM_UTF8.decode()):
				line = line[3:]
			line = line[:-1]
			dic_els = str.split(line,":=")
			log.info("^^^^^^^^^^^^^^^^^^^^ %r ^^^^^^^^^^^^^^^^" % dic_els)
			secEl = str.split(dic_els[1],",")
			secMap = list()
			for i in range(0,len(secEl)):
				secMap.append("br(pactos_old):"+''.join(str.split(secEl[i])[0]))

			tmpDic[str.split(dic_els[0])[0]] = tuple(secMap)

		commands = dict()
		commands["globalCommands.GlobalCommands"] = tmpDic

		iniFile.close()

		self.gestureMap = inputCore.GlobalGestureMap(commands)
		log.info(self.gestureMap._map)


class InputGesture(braille.BrailleDisplayGesture, brailleInput.BrailleInputGesture):

	source = BrailleDisplayDriver.name

	def __init__(self, keys, isMod78):
		super(InputGesture, self).__init__()
		self.keyCodes = set(keys)

		self.keyNames = names = set()
		isBrailleInput = True
		
		log.info("dddddddddddddddddddd77777777 = %r ddddddddddddddddddddddd7777777777" % self.d7)
		log.info("dddddddddddddddddddd88888888 = %r ddddddddddddddddddddddd8888888888" % self.d8)

		for key in self.keyCodes:
			if isBrailleInput:
				if (DOT1_KEY <= key <= DOT6_KEY) or \
				(isMod78 and (len(self.keyCodes) > 1) and (key==self.d7 or key==self.d8)):
					log.info("MMMMMOOOOOODDDDDD77778888 --------------->> ** This key == %r ** <<---------" % key)
					tmp_key = key
					if isMod78:
						if tmp_key == self.d7:
							tmp_key = 8
						elif tmp_key == self.d8:
							tmp_key = 9
							
					self.dots |= 1 << (tmp_key - DOT1_KEY)
				elif ((key == SPACE_KEY1) | (key == SPACE_KEY2)):
					self.space = True
				else:
					# This is not braille input.
					isBrailleInput = False
					self.dots = 0
					self.space = False
			if key >= FIRST_ROUTING_KEY:
				names.add("routing")
				self.routingIndex = key - FIRST_ROUTING_KEY
				log.info("#################### routingIndex == %r ##############" % self.routingIndex)
			else:
				try:
					names.add(KEY_NAMES[key])
				except KeyError:
					log.debugWarning("Unknown key with id %d" % key)

		self.id = "+".join(names)
