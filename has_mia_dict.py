import subprocess
import os
from os.path import join, dirname

import Pyperclip
import pynput.keyboard as keyboard
import pynput.mouse as mouse

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

    - capturing screenshots (handleImageExport on left click release [wouldn't work for dragging])


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
        self.autoExportFinished = conf['auto-export-finished']

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


class AutoCardsThread(QObject):
    keyPressed = pyqtSignal(list)
    keyReleased = pyqtSignal(list)
    mouseReleased = pyqtSignal(int)
    mousePressed = pyqtSignal(int)

    def __init__(self, mw):
        if isMac:
            import ssl
            ssl._create_default_https_context = ssl._create_unverified_context
            sys.path.insert(0, join(dirname(__file__), 'keyboardMac'))
        elif isLin:
            sys.path.insert(1, join(dirname(__file__), 'linux'))
        sys.path.insert(0, join(dirname(__file__)))
        from pynput import keyboard
        super(AutoCardsThread, self).__init__(mw)
        self.keyboard = keyboard
        self.mouse = mouse
        self.mw = mw
        self.config = self.mw.addonManager.getConfig(__name__)


    def on_press(self,key):
        self.keyPressed.emit([key]) 
    
    def on_release(self, key):
        self.keyReleased.emit([key])
        return True

    def on_click(self, x, y, button, pressed):
        # if 'released' then handle screenshotexport
        if button == mouse.Button.left:
            if pressed:
                self.mousePressed.emit(1)
            else:
                self.mouseReleased.emit(1)
                


    def run(self):
        if isWin:
            self.keyboardListener = self.keyboard.Listener(
                on_press =self.on_press, on_release= self.on_release, mia = self.mw, suppress= True)
            self.mouseListener = self.mouse.Listener(
                on_click= self.on_click
            )
        else:
            self.keyboardlistener = self.keyboard.Listener(
                on_press =self.on_press, on_release= self.on_release)
        self.keyboardListener.start()
        self.mouseListener.start()

class AutoCards(QObject):
    imageExport = pyqtSignal(int)
    sentenceExport = pyqtSignal(int)
    imageCapture = pyqtSignal(int)
    audioCapture = pyqtSignal(int)
    test = pyqtSignal(int)
    imageCaptured = pyqtSignal(int)

    def __init__(self):
        super(AutoCards, self).__init__()
        self.started = False
        self.selectingScreenshot = False
        self.capturingScreenshot = False
        self.selectingAudio = False
        self.capturingAudio = False
        self.autoExportFinished = config.autoExportFinished
    
    def capture_audio(self):
        #start capturing
        p = subprocess.run([config.sharex_exe,"-workflow",config.capture_audio])
        self.selectingAudio = True

    def stop_audio(self):
        p = subprocess.run([config.sharex_exe,"-workflow",config.capture_audio])
        self.capturingAudio = False
        QTimer.singleShot(300 , self.handleAudioExport)

    def handleAudioExport(self):
        mw.pressedKeys = []
        mw.hkThread.handleImageExport()
        if self.autoExportFinished:
            QTimer(200,mw.hkThread.attemptAddCard)
        self.started = False

    def handleScreenshotExport(self):
        mw.pressedKeys = []
        mw.hkThread.handleImageExport()
        self.capturingScreenshot = False
        QTimer.singleShot(200 , self.capture_audio)

    def capture_screenshot(self):
        p = subprocess.run([config.sharex_exe,"-workflow",config.capture_screenshot])
        self.capturingScreenshot = True

    def start_combo(self):
        mw.pressedKeys = []
        mw.hkThread.handleSentenceExport()
        QTimer.singleShot(200 , self.capture_screenshot)

mw.pressedKeys = []

def on_key_press(keyList):
    key = keyList[0]
    char = str(key)
    if char not in mw.pressedKeys:
        mw.pressedKeys.append(char)
    
    if not mw.auto_cards.started:
        if 'Key.f4' in mw.pressedKeys:
            mw.auto_cards.started = True
            mw.auto_cards.start_combo()

    elif mw.auto_cards.started:
        if 'Key.esc' in mw.pressedKeys:
            #cancel the process
            #reinitialise the object
            mw.auto_cards = AutoCards()
            mw.pressedKeys = []
            return
            
        if mw.auto_cards.capturingAudio:
            if 'Key.f4' in mw.pressedKeys:
                mw.auto_cards.stop_audio()

            

def on_key_release(keyList):
    key = keyList[0]
    try:
        mw.pressedKeys.remove(str(key))
    except:
        return

def on_mouse_release():
    if mw.auto_cards.started:
        if mw.auto_cards.capturingScreenshot:
            QTimer.singleShot(200,mw.auto_cards.handleScreenshotExport)

        elif mw.auto_cards.selectingAudio:
            mw.auto_cards.capturingAudio = True


mw.auto_cards = AutoCards()
mw.auto_cards.sentenceExport.connect(mw.auto_cards.capture_screenshot)
mw.auto_cards.imageCapture.connect(mw.auto_cards.capture_audio)

mw.autoCardsThread = AutoCardsThread(mw)
mw.autoCardsThread.run()
mw.autoCardsThread.keyPressed.connect(on_key_press)
mw.autoCardsThread.keyReleased.connect(on_key_release)
mw.autoCardsThread.mouseReleased.connect(on_mouse_release)