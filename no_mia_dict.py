

class HotKeyListener(QWidget):
    keyPressed = QtCore.pyqtSignal(int)

    def keyPressEvent(self, event):
        super(HotKeyListener, self).keyPressEvent(event)
        self.keyPressed.emit(event.key())