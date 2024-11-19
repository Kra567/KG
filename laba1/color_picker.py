import random
import sys

from PySide6.QtCore import Qt, Slot, Signal, QObject, SIGNAL, QSize
from PySide6.QtWidgets import (QMainWindow,QApplication, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget,QLineEdit, QHBoxLayout, QColorDialog)
from __feature__ import snake_case, true_property
from dataclasses import dataclass 
from PySide6.QtGui import QColor
from typing import Any,Callable,Type
from abc import ABC,abstractmethod


def get_dynamic(cls: type) -> list[str]:
    return [fld for fld in cls.__dict__['__annotations__'].keys() if not fld in cls.__dict__]

@dataclass(frozen=True)
class Bounds:
    bounder: Callable[[str], bool]
    converter: Callable[[str], Any]
    default: Any


class ColorModel(ABC):
    
    @staticmethod
    @abstractmethod
    def wrap_color(color: QColor) -> 'ColorModel':
        pass 

    @abstractmethod
    def get_color(self) -> QColor:
        pass


# int bounds 
def int_bounds(a: int, b: int) -> Callable[[str],bool]:
    def bounder(val: str) -> bool:
        try:
            value = int(val)
            return a <= value and value <= b 
        except:
            return False
    return bounder

# RGB
@dataclass(frozen=True)
class RGB(ColorModel):
    red: int 
    green: int 
    blue: int 

    rgb_bounds: Bounds = Bounds(int_bounds(0, 255), int, 0)
    red_bounds: Bounds = rgb_bounds
    green_bounds: Bounds = rgb_bounds
    blue_bounds: Bounds = rgb_bounds

    @staticmethod
    def wrap_color(color: QColor) -> 'RGB':
        return RGB(color.red(),color.green(),color.blue())
    
    def get_color(self) -> QColor:
        return QColor(self.red,self.green,self.blue)


# HSV
@dataclass(frozen=True)
class HSV(ColorModel):
    hue: int
    saturation: int 
    value: int

    hue_bounds: Bounds = Bounds(int_bounds(0,359), int, 0)
    saturation_bounds: Bounds = Bounds(int_bounds(0,255), int, 0)
    value_bounds: Bounds = Bounds(int_bounds(0,255), int, 0)

    @staticmethod
    def wrap_color(color: QColor) -> 'HSV':
        return HSV(color.hue() ,color.saturation(), color.value() )
    
    def get_color(self) -> QColor:
        color = QColor()
        color.set_hsv(self.hue , self.saturation , self.value)
        return color

# CMYK
@dataclass(frozen = True)
class CMYK(ColorModel):
    cyan: int
    magenta: int
    yellow: int
    black: int

    cyan_bounds: Bounds = Bounds(int_bounds(0,255), int, 0)
    magenta_bounds: Bounds = Bounds(int_bounds(0,255), int, 0)
    yellow_bounds: Bounds = Bounds(int_bounds(0,255), int, 0)
    black_bounds: Bounds = Bounds(int_bounds(0,255), int, 0)

    @staticmethod
    def wrap_color(color: QColor) -> 'CMYK':
        return CMYK(color.cyan(), color.magenta(), color.yellow(), color.black())
    
    def get_color(self) -> QColor:
        color = QColor()
        color.set_cmyk(self.cyan, self.magenta, self.yellow, self.black)
        return color




class BoundedLineEdit(QLineEdit):
    def __init__(self, bounds : Bounds):
        super().__init__()
        self.bounds = bounds 
        self.value = bounds.default
        self.bounded = True
        self.textChanged.connect(self.on_text_changed)
        self.editingFinished.connect(self.on_text_finished)
        self.text = str(bounds.default)

    @Slot(str)
    def on_text_changed(self, txt):
        self.bounded = self.bounds.bounder(txt)
        if self.bounded:
            self.value = self.bounds.converter(txt)
            self.style_sheet = "border: 2px solid black;"
        else:
            self.style_sheet = "border: 2px solid red;"
        
    
    @Slot()
    def on_text_finished(self):
        self.text = str(self.value)
        self.style_sheet = "border: 2px solid black;"
    
    @Slot()
    def on_timeout(self):
        if not self.bounded:
            self.text = str(self.value)
            self.style_sheet = "border: 2px solid black;"
    
    def get_value(self) -> Any:
        return self.value
    
    def set_value(self, val: Any) -> None:
        self.value = val
        self.text = str(val)



class Valuer(QWidget):
    color_changed = Signal(QColor)

    def __init__(self, cls: Type[ColorModel]):
        self.cls: Type[ColorModel] = cls
        self.dct: dict[str, BoundedLineEdit] = {} 
        super().__init__()
        layout = QHBoxLayout()
        layout.add_widget(QLabel(self.cls.__name__))
        for key in get_dynamic(self.cls):
            edit = BoundedLineEdit(getattr(cls,key + "_bounds"))
            edit.textChanged.connect(self._on_text_changed)
            #edit.editingFinished.connect(self._on_editing_finished)
            edit.placeholder_text = key
            edit.max_length = 5
            self.dct[key] = edit
            layout.add_widget(edit)
        self.set_layout(layout)
        self.show()
    
    @Slot(str)
    def _on_text_changed(self, text: str):
        self.color_changed.emit(self.get_color())
        pass

    def get_color(self) -> QColor:
        kwargs = {k : v.get_value() for k, v in self.dct.items()}
        return self.cls(**kwargs).get_color()
    
    @Slot(QColor)
    def update_color(self, color: QColor) -> None:
        self.block_signals(True)
        model_color = self.cls.wrap_color(color)
        for key, edit in self.dct.items():
            edit.set_value(getattr(model_color,key))
        self.block_signals(False)


class Final(QWidget):
    color_changed = Signal(QColor)

    def __init__(self, *color_models: list[Type[ColorModel]]):
        super().__init__()
        self.window_title = "color picker"
        self.models: dict[str, Valuer] = {}
        self.color = QColor("magenta")
        for model_class in color_models:
            valuer = Valuer(model_class)
            self.models[model_class.__name__] = valuer
            self.block_signals(True)
            valuer.update_color(self.color)
            self.block_signals(False)
        self.connect_models()
        layout = QVBoxLayout()
        
        
        self.label = QLabel()
        self.label.set_fixed_size(200, 200)
        hwidget = QWidget()
        hlayout = QHBoxLayout()
        hwidget.set_layout(hlayout)
        hlayout.add_widget(self.label)
        button = QPushButton("pick")
        button.size_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        button.maximum_size = QSize(200,200)
        button.style_sheet = '''QPushButton {
               border: 2px solid black;
               background-color: lightgray;  
            }
            QPushButton:hover {
               border: 2px solid black;  
               background-color: gray;
            }
            QPushButton:pressed {
               background-color: darkgray;
            }'''
        button.clicked.connect(self.pick_color)
        hlayout.add_widget(button)

        layout.add_widget(hwidget)
        
        
        
        for key, valuer in self.models.items():
            layout.add_widget(valuer)
        self.set_layout(layout)
        self.change_label_color(self.color)
        self.set_fixed_size(QSize(360,400))
        print(self.size)
        self.show()        
    
    def connect_models(self):
        valuers = list(self.models.values())
        for i in range(len(valuers) - 1):
            valuers[i].color_changed.connect(valuers[i + 1].update_color)
            valuers[i + 1].color_changed.connect(valuers[i].update_color)
        valuers[-1].color_changed.connect(valuers[0].update_color)
        valuers[0].color_changed.connect(valuers[-1].update_color)
        
        for valuer in valuers:
            valuer.color_changed.connect(self.change_color_internally)
    
    def change_label_color(self, color: QColor):
        self.label.style_sheet = f"border: 2px solid black;background-color: rgb({color.red()}, {color.green()}, {color.blue()});"
    
    @Slot()
    def pick_color(self):
        color = QColorDialog().get_color()
        for valuer in list(self.models.values()):
            valuer.update_color(color)
        self.change_label_color(color)


    @Slot(str, QColor)
    def change_color_internally(self, color: QColor):
        self.color = color
        self.change_label_color(color)


app = QApplication(sys.argv)
widget = Final(RGB, HSV, CMYK)

app.exit(app.exec())
#print(QColor("blue").hue())