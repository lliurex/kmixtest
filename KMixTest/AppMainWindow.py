from PySide2.QtCore import *
from PySide2.QtWidgets import *
from PySide2.QtGui import *
from PySide2.QtPrintSupport import *
from PySide2.QtUiTools import *

from .Helper import Helper
from .Config import ICONS, UI, NATIVE_THREADS
from .TableHelper import tableHelper
from .GridHelper import gridHelper
from .HelperPDF import helperPDF
from .Persistence import Persistence

from os.path import expanduser
class MenuItem():
    def __init__(self):
        self.children = {}
        self.name = None
        self.action = None
        self.menu = None
        self.parent = None
    def _get_names(self):
        if self.name:
            l = [ self.name ]
        else:
            l = []
        for c in self.children:
            l.extend(self.children[c]._get_names())
        return l
# Main class of application
class AppMainWindow(QApplication):    
    def __init__(self):
        super().__init__([])
        try:
            self.window = self.loadUi()
            self.menu = MenuItem()
            self.menu.name = 'ROOT'
            self.menu.menu = self.window.menubar

            self.window.show()
            self.bind_toolbar_actions()
            self.tableQuestions = tableHelper(self.window.tableWidgetQuestions, self)
            self.tableQuestions.editingQuestion.connect(self.editingQuestion)
            self.window.scrollAreaAnswers.setVerticalScrollBarPolicy( Qt.ScrollBarAlwaysOn )
            self.scroll = gridHelper(self.window.gridEdition, self)
            self.window.previewButton.clicked.connect(self.clickedPreview)
            self.tableQuestions.rowSelection.connect(self.scroll.showQuestion)
            self.sheet = None
            self.aboutToQuit.connect(self.exitting)
            self.persistence = Persistence(debug=True)
            self.addMenuItem([{"Exam":["New","-","Load Exam","-","Save","Save as"]},{"Mixer":["Generate Mix"]},{"Print":["Print Exam"]},"Exit"])
            self.tableQuestions.pool.start_threads()
        except Exception as e:
            print("Exception when initializing, {}".format(e))
            self.exitting()
    @Slot()
    def exitting(self):
        global NATIVE_THREADS
        qDebug("Exitting")
        if self.tableQuestions:
            if self.tableQuestions.pool:
                self.tableQuestions.pool.terminate = True
                self.tableQuestions.pool.abort()
                if NATIVE_THREADS:
                    self.tableQuestions.pool.threadpool.clear()
        self.quit()

    @Slot(int)
    def editingQuestion(self, row):
        qDebug("Editing {}".format(row))

    @Slot(bool)
    def clickedPreview(self,checked):
        qDebug("Preview clicked!")
        if not self.sheet:
            self.sheet = helperPDF(parent=self)
        self.sheet.openWidget()

    def loadUi(self):
        global UI
        ui_file = QFile(UI)
        ui_file.open(QFile.ReadOnly)
        ui_loader = QUiLoader(self)
        window = ui_loader.load(ui_file)
        ui_file.close()
        return window

    def bind_toolbar_actions(self):
        for action in dir(self.window):
            action_obj = getattr(self.window,action)
            if isinstance(action_obj,QAction):
                action_obj.setData(action_obj.text())
                action_obj.triggered.connect(self.newQuestion)

    @Slot()
    def newQuestion(self):
        data = self.sender().data()
        qDebug("senderData:{}".format(data))
        self.window.statusbar.showMessage("Action from '{}' triggered".format(data),10*1000)
        self.tableQuestions.addItem(data)

    def calculate_default_menubar_shortcut(self,name):
        used = []
        print('names: {}'.format(self.menu._get_names()))
        for item in self.menu._get_names():
            for character in item:
                if character in used:
                    continue
                else:
                    used.append(character)
                    break
        newname = ""
        done = False
        for character in name:
            if done or character in used:
                newname += character
            else:
                newname += "&" + character
                done = True

        return newname

    def openfiledialog(self):
        f = QFileDialog().getOpenFileName(None,self.tr("Open Exam"),expanduser("~"),self.tr("Exam files (*.kmt)"))
        return f[0] if f else None

    def savefiledialog(self):
        f = QFileDialog().getSaveFileName(None,self.tr("Save Exam"),expanduser("~"),self.tr("Exam files (*.kmt)"))
        return f[0] if f else None

    def buildExamData(self):
        model = self.tableQuestions.dumpTableModel()
        i = 0
        for row in model:
            row.insert(0,i)
            i+=1
        return model

    def useExamData(self,examData):
        model = {}
        if not examData:
            raise ValueError()
        for row in examData:
            model.setdefault(row[0],(row[3],(row[1],row[2])))
        for x in sorted(model.keys()):
            name, states = model.get(x)
            fixed,linked = states
            self.tableQuestions.addItemWithState(name,bool(fixed),bool(linked))
        return None

    def menuController(self,*args,**kwargs):
        data = self.sender().data()
        print('Menu "{}" click'.format(data))
        if data == 'Exit':
            self.exitting()
        elif data == 'Load':
            filename = self.openfiledialog()
            if filename:
                self.tableQuestions.clearTable()
                self.persistence.newExam()
                examData = self.persistence.loadExam(filename)
                self.useExamData(examData)
        elif data == 'New':
            self.tableQuestions.clearTable()
            self.persistence.newExam()
        elif data == 'Save as':
            filename = self.savefiledialog()
            if filename:
                examData = self.buildExamData()
                result = self.persistence.saveExam(filename,examData)
        elif data == 'Print Exam':
            self.clickedPreview(True)
        else:
            qDebug("No action declared for '{}' menuaction".format(data))

    def addMenuItem(self, *args, **kwargs):
        if bool(args) == bool(kwargs):
            raise ValueError()
        if args:
            on = self.menu
            what = args
        elif kwargs:
            on = kwargs.get('on',None)
            what = kwargs.get('what',None)
            if on is None or what is None:
                raise ValueError()
        if not isinstance(on,MenuItem):
            raise ValueError()
        
        if isinstance(what,(list,tuple)):
            for x in what:
                self.addMenuItem(what=x,on=on)
        elif isinstance(what,dict):
            for k in what:
                if k not in on.children:
                    menuname_with_shortcut = self.calculate_default_menubar_shortcut(k)
                    menu = on.menu.addMenu(menuname_with_shortcut)
                    item = MenuItem()
                    item.name = k
                    item.menu = menu
                    item.parent = on
                    on.children.setdefault(item.name,item)
                else:
                    item = on.children.get(k)
                v = what[k]
                self.addMenuItem(what=v,on=item)
        elif isinstance(what,str):
            if on.menu:
                if what in ['-','_']:
                    on.menu.addSeparator()
                else:
                    # icon = ICONS['option']
                    # if on is self.menu:
                    #     icon = None
                    if on.menu == self.window.menubar:
                        icon = None
                    else:
                        icon = QIcon(' ')
                    action = Helper.genAction(name=what,fn=self.menuController,icon=icon,tip=what,parent=on.menu,data=what)
                    on.action = action
                    on.menu.addAction(action)
        else:
            raise ValueError()
