# Copyright 2013 BrewPi
# This file is part of BrewPi.

# BrewPi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# BrewPi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with BrewPi.  If not, see <http://www.gnu.org/licenses/>.

import simplejson as json
import sys
import time
from distutils.version import LooseVersion
from BrewPiUtil import asciiToUnicode
from serial import SerialException
import re

def getVersionFromSerial(bg_ser):
    version = None
    retries = 0
    startTime = time.time()    
    bg_ser.writeln('n')  # request version info
    while retries < 10:
        retry = True
        while True: # read all lines from serial
            line = bg_ser.read_line()
            if line:
                if line[0] == 'N':
                    data = line.strip('\n')[2:]
                    version_parsed = AvrInfo(data)
                    if version_parsed and version_parsed.version != "0.0.0":
                        retry = False
                        version = version_parsed
                        break
            else:
                break
        if time.time() - startTime >= 30:
            # try max 30 seconds
            retry = False
        if retry:
            bg_ser.writeln('n')  # request version info
            retries += 1
            time.sleep(1)
        else:
            break
    return version


class AvrInfo:
    """ Parses and stores the version and other compile-time details reported by the controller """
    version = "v"
    build = "n"
    simulator = "y"
    board = "b"
    shield = "s"
    log = "l"
    commit = "c"

    shield_revA = "revA"
    shield_revC = "revC"
    spark_shield_v1 = "V1"
    spark_shield_v2 = "V2"
    spark_shield_v3 = "V3"

    shields = {1: shield_revA, 2: shield_revC, 3: spark_shield_v1, 4: spark_shield_v2, 5: spark_shield_v3}

    board_leonardo = "leonardo"
    board_standard = "uno"
    board_mega = "mega"
    board_spark_core = "core"
    board_photon = "photon"
    board_p1 = "p1"

    boards = {'l': board_leonardo, 's': board_standard, 'm': board_mega, 'x': board_spark_core, 'y': board_photon, 'p': board_p1}

    family_arduino = "Arduino"
    family_spark = "Particle"

    families = { board_leonardo: family_arduino,
                board_standard: family_arduino,
                board_mega: family_arduino,
                board_spark_core: family_spark,
                board_photon: family_spark,
                board_p1: family_spark}

    board_names = { board_leonardo: "Leonardo",
                board_standard: "Uno",
                board_mega: "Mega",
                board_spark_core: "Core",
                board_photon: "Photon",
                board_p1: "p1"}

    def __init__(self, s=None):
        self.version = LooseVersion("0.0.0")
        self.build = 0
        self.commit = None
        self.simulator = False
        self.board = None
        self.shield = None
        self.log = 0
        self.parse(s)

    def parse(self, s):
        if s is None or len(s) == 0:
            pass
        else:
            s = s.strip()
            if s[0] == '{':
                self.parseJsonVersion(s)
            else:
                self.parseStringVersion(s)

    def parseJsonVersion(self, s):
        j = None
        try:
            j = json.loads(s)
        except json.decoder.JSONDecodeError, e:
            print >> sys.stderr, "JSON decode error: %s" % str(e)
            print >> sys.stderr, "Could not parse version number: " + s
        except UnicodeDecodeError, e:
            print >> sys.stderr, "Unicode decode error: %s" % str(e)
            print >> sys.stderr, "Could not parse version number: " + s
        except TypeError, e:
            print >> sys.stderr, "TypeError: %s" % str(e)
            print >> sys.stderr, "Could not parse version number: " + s

        self.family = None
        self.board_name = None
        if not j:
            return
        if AvrInfo.version in j:
            self.parseStringVersion(j[AvrInfo.version])
        if AvrInfo.simulator in j:
            self.simulator = j[AvrInfo.simulator] == 1
        if AvrInfo.board in j:
            self.board = AvrInfo.boards.get(j[AvrInfo.board])
            self.family = AvrInfo.families.get(self.board)
            self.board_name = AvrInfo.board_names.get(self.board)
        if AvrInfo.shield in j:
            self.shield = AvrInfo.shields.get(j[AvrInfo.shield])
        if AvrInfo.log in j:
            self.log = j[AvrInfo.log]
        if AvrInfo.build in j:
            self.build = j[AvrInfo.build]
        if AvrInfo.commit in j:
            self.commit = j[AvrInfo.commit]

    def parseStringVersion(self, s):
        pattern = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+.*")
        if pattern.match(s): # check for valid string
            self.version = LooseVersion(s)

    def toString(self):
        if self.version:
            return str(self.version)
        else:
            return "0.0.0"

    def article(self, word):
        if not word:
            return "a" # in case word is not valid
        firstLetter = word[0]
        if firstLetter.lower() in 'aeiou':
            return "an"
        else:
            return "a"

    def toExtendedString(self):
        string = "BrewPi v" + self.toString()
        if self.commit:
            string += ", running commit " + str(self.commit)
        if self.build:
            string += " build " + str(self.build)
        if self.board:
            string += ", running on "+ self.articleFullName()
        if self.shield:
            string += " with a " + str(self.shield) + " shield"
        if(self.simulator):
           string += ", running as simulator"
        return string

    def isNewer(self, versionString):
        return self.version < LooseVersion(versionString)

    def isEqual(self, versionString):
        return self.version == LooseVersion(versionString)

    def familyName(self):
        family = AvrInfo.families.get(self.board)
        if family == None:
            family = "????"
        return family

    def boardName(self):
        board = AvrInfo.board_names.get(self.board)
        if board == None:
            board = "????"
        return board

    def fullName(self):
        return self.familyName() + " " + self.boardName()

    def articleFullName(self):
        return self.article(self.family) + " " + self.fullName()

