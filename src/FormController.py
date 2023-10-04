import asyncio
import logging
from typing import Callable

from telegram import *
from telegram.ext import *
from telegram._utils.types import ReplyMarkup

from FormPage import GameGPTFormPage

class GameGPTFormController:

    def __init__(self) -> None:        
        self.botCore = None    
        self.list_forms = []
        self.current:GameGPTFormPage = None
        self.onEnd: Callable[[Update, ContextTypes], None] = None
        self.user = None
        self.isCommited = False

    def reset(self):
        for form in self.list_forms:
            # skip none object
            if form == None:
                continue
            form.isDone = False

    def add(self, type, msg):
        # Create new form
        form = GameGPTFormPage()
        form.type = type
        form.msg = msg

        # Add new type to user data 
        self.user.data_list[type] = ""

        # Add new blank
        self.list_forms.append(form)

        # Remove duplicates
        #self.list_forms = list(dict.fromkeys(self.list_forms))
        
    def push(self, input):
        # Input is not empty we are set new data and mark is Done for form 
        if input != None or input != "":
            self.current.data = input
            self.current.isDone = True

    def dump(self):
        logging.log(logging.INFO, f"FormController {self.user.name} print forms...")
        for form in self.list_forms:
            # skip none object
            if form == None:
                continue

            logging.log(logging.INFO, f"{form.type} {form.data} {form.isDone}")

    def commit(self):
        logging.log(logging.INFO, f"FormController {self.user.name} commit forms")
        self.isCommited = True
        for form in self.list_forms:
            # skip none object
            if form == None:
                continue

            # set data by type 
            self.user.data_list[form.type] = form.data

    def next(self, update: Update, context: ContextTypes.DEFAULT_TYPE, reply_markup: ReplyMarkup = None):    
        logging.log(logging.INFO, f"FormController {self.user.name} next form")
        loop = asyncio.get_event_loop()

        for form in self.list_forms:
            # skip none object
            if form == None:
                continue
            # if blank exist but it's not a fineshed we are wait for the data 
            if form.isDone == False and self.current != form:
                loop.create_task(self.botCore.send(text=f"Напишите {form.msg}", update=update, reply_markup=reply_markup))    
 
                self.current = form
                break
        else:

            if self.onEnd != None:
                self.commit()
                loop.create_task(self.onEnd(update, context))
            else:
                logging.log(logging.CRITICAL, "Can't continue because callback is None!")  

