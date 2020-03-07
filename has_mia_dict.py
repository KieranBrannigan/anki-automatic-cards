import subprocess
import os
from os.path import join, dirname

import Pyperclip
import pynput.keyboard as keyboard

from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo
from anki.utils import isMac, isWin, isLin

'''
- check if MIA dictionary is installed, if it is we can add everything to the card exporter,
that way can easily check everything is correct and add definitions etc before adding.

When press keybind:
    - take a screenshot
    - save screenshot (make sure screenshot is saved)
    - try upload to MIA dictionary
    - start recording audio (press sharex keybinding)
    - wait for audio to finish (with exit code or anything?)
    - To stop audio either press original capture hotkey or our hotkey 
        -(if they press our hotkey send cmd subprocess again to stop.)
    


    - connect to collection and upload the card
'''

class Config:
    def __init__(self):
        self.get_config()
        self.get_sharex_exe()

    def get_config(self):
        conf = mw.addonManager.getConfig(__name__)
        self.audio = conf['capture-audio']
        self.screenshot = conf['capture-screenshot']
        self.capture_audio = conf['workflows']['name-of-audio-capture-workflow']
        self.capture_screenshot = conf['workflows']['name-of-screenshot-capture-workflow']
        self.start_key = conf['keybinds']['start']
        self.sharex_folder = conf['path-to-sharex-installation-folder']

    def get_sharex_exe(self):
        if not self.sharex_folder == "":
            folder = self.sharex_folder
            try:
                files = os.listdir(folder)
            except FileNotFoundError as e:
                # Maybe open a dialog box and tell them to 
                # fix their config. 
                raise e
            if "ShareX.exe" in files:
                self.sharex_exe = os.path.join(folder,"ShareX.exe")
            else:
                raise ValueError("COULDN'T FIND ShareX.exe in your ShareX INSTALLATION FOLDER mate. PLEASE CHECK CONFIG FILE.")

        else:   
            #find the sharex executable on their system. 
            # check start menu?
            # check desktop
            raise ValueError("Please supply a shareX installation folder")

config = Config()


class HotKeyListener(QObject):
    keyPressed = pyqtSignal(list)
    keyReleased = pyqtSignal(list)

    def __init__(self, mw):
        if isMac:
            import ssl
            ssl._create_default_https_context = ssl._create_unverified_context
            sys.path.insert(0, join(dirname(__file__), 'keyboardMac'))
        elif isLin:
            sys.path.insert(1, join(dirname(__file__), 'linux'))
        sys.path.insert(0, join(dirname(__file__)))
        from pynput import keyboard
        super(HotKeyListener, self).__init__(mw)
        self.keyboard = keyboard
        self.mw = mw
        self.config = self.mw.addonManager.getConfig(__name__)


    def on_press(self,key):
        self.keyPressed.emit([key]) 
    
    def on_release(self, key):
        self.keyReleased.emit([key])
        return True

    def run(self):
        if isWin:
            self.listener = self.keyboard.Listener(
                on_press =self.on_press, on_release= self.on_release, mia = self.mw, suppress= True)
        else:
            self.listener = self.keyboard.Listener(
                on_press =self.on_press, on_release= self.on_release)
        self.listener.start()

class AutoCards(QObject):
    imageExport = pyqtSignal(int)
    sentenceExport = pyqtSignal(int)
    imageCapture = pyqtSignal(int)
    audioCapture = pyqtSignal(int)
    test = pyqtSignal(int)
    imageCaptured = pyqtSignal(int)
    
    def capture_audio(self):
        #start capturing
        p = subprocess.run([config.sharex_exe,"-workflow",config.capture_audio])

    def stop_audio(self):
        p = subprocess.run([config.sharex_exe,"-workflow",config.capture_audio])
        QTimer.singleShot(500,self.handleAudioExport)

    def handleAudioExport(self):
        mw.capturing_audio = False
        mw.pressedKeys = []
        mw.hkThread.handleImageExport()

    def handleImageExport(self):
        mw.pressedKeys = []
        mw.hkThread.handleImageExport()
        QTimer.singleShot(1000 , self.capture_audio)
        

    def capture_screenshot(self):
        p = subprocess.run([config.sharex_exe,"-workflow",config.capture_screenshot])
        QTimer.singleShot(2500, self.handleImageExport)
        
        

    def start_combo(self):
        mw.pressedKeys = []
        mw.hkThread.handleSentenceExport()
        QTimer.singleShot(500 , self.capture_screenshot)

mw.pressedKeys = []

def on_key_press(keyList):
    key = keyList[0]
    char = str(key)
    if char not in mw.pressedKeys:
        mw.pressedKeys.append(char)
    
    if not mw.capturing_audio:
        if 'Key.f4' in mw.pressedKeys:
            mw.capturing_audio = True
            mw.auto_cards.start_combo()

    elif mw.capturing_audio:
        if 'Key.f4' in mw.pressedKeys:
            mw.auto_cards.stop_audio()
            

def on_key_release(keyList):
    key = keyList[0]
    try:
        mw.pressedKeys.remove(str(key))
    except:
        return


mw.capturing_audio = False

mw.auto_cards = AutoCards()
mw.auto_cards.sentenceExport.connect(mw.auto_cards.capture_screenshot)
mw.auto_cards.imageCapture.connect(mw.auto_cards.capture_audio)



mw.autoCardsThread = HotKeyListener(mw)
mw.autoCardsThread.run()
mw.autoCardsThread.keyPressed.connect(on_key_press)
mw.autoCardsThread.keyReleased.connect(on_key_release)