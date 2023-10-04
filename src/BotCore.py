import asyncio
import logging
import os 
import sys

from datetime import datetime

from telegram import *
from telegram.ext import *
from telegram._utils.types import ReplyMarkup

# GameGPT
from AICore import *
from FormController import GameGPTFormController
from User import GameGPTUser
from UserDataController import GameGPTUserDataController

class GameGPTBotCore:
    IS_ON_DEBUG_MODE = hasattr(sys, 'gettrace') and sys.gettrace()
    USE_DEV_BOT = True

    debug_turn_off_ai = False
    debug_turn_off_game_page = False

    # Bot token received from https://t.me/Botfather
    TOKEN: str = os.getenv("GAME_GPT_DEV_TG_TOKEN", "None") if IS_ON_DEBUG_MODE and USE_DEV_BOT else os.getenv("GAME_GPT_TG_TOKEN", "None") 
    BOT_VERSION: str = '0.6'

    application: Application = None 
    jobQueue: JobQueue = None 

    conversationHandler: ConversationHandler = None
    STATE_START, STATE_FORM_GAME_START = range(2)
    states: dict[int, list] = { }
    data_controller: GameGPTUserDataController = None

    # OpenAI struct
    ai: GameGPTAICore = None

    # save user to this list sorted by id's 
    users: dict[int, GameGPTUser] = { }

    message_handler = None

    def __init__(self):
        # Initialize logging format  
        self.init_logger()
        
        # Check token on exist 
        logging.log(logging.INFO, "Run bot core...")
        if self.TOKEN == "None":
            logging.log(logging.FATAL, "TG Bot Token is none, we can't continue!")
            return 

        self.data_controller = GameGPTUserDataController()
        self.data_controller.read_all_data_base(self.users)

        self.ai = GameGPTAICore()

        # Add token and build our app 
        self.application = ApplicationBuilder().token(self.TOKEN).build()

        # Create the ConversationHandler to handle events 
        self.conversationHandler = ConversationHandler(
            # Set entry point
            entry_points=[CommandHandler("start", self.on_start)],
            states = self.states,
            fallbacks=[],
        )

        self.jobQueue = self.application.job_queue

        # Add our handles  
        self.application.add_handler(self.conversationHandler)
        
        # Adding start command if we need to reset bot
        self.application.add_handler(CommandHandler("start", self.on_start))
        
        self.application.add_handler(CommandHandler("help", self.command_help))
        self.application.add_handler(CommandHandler("clear", self.command_clear))
        self.application.add_handler(CommandHandler("new", self.command_new))
        # Debug commands
        self.application.add_handler(CommandHandler("debug_show_save_data", self.debug_show_save_data))
        self.application.add_handler(CommandHandler("debug_print_all_users", self.debug_print_all_users))
        self.application.add_handler(CommandHandler("debug_show_message_history", self.debug_show_message_history))
        # Run bot 
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

    def init_logger(self):
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
        logging.getLogger("httpx").setLevel(logging.WARNING) # Remove "httpx" INFO messages

        LOG_FOLDER_NAME = "Logs"
        # Create folder if it not exist 
        if not os.path.exists(LOG_FOLDER_NAME):
            os.makedirs(LOG_FOLDER_NAME)

        # Create log file    
        LOG_FILE_NAME_ROOT = f"{LOG_FOLDER_NAME}\\root-{datetime.now().year}-{datetime.now().month}-{datetime.now().day}-{datetime.now().hour}-{datetime.now().minute}-{datetime.now().second}.log"

        f = open(os.path.join(os.getcwd(), LOG_FILE_NAME_ROOT) , 'w+') 
        f.write('gamebotgpt log file:\n')
        f.close()
        
        fh = logging.FileHandler(LOG_FILE_NAME_ROOT)
        fh.setLevel(logging.INFO)
        logging.getLogger("root").addHandler(fh)

    async def on_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:        
        # User is new ?
        if not update.effective_user.id in self.users:
            # Add new user by id 
            user = self.users[update.effective_user.id] = GameGPTUser()     
            user.name = update.effective_user.full_name
            user.id = update.effective_user.id
            logging.log(logging.INFO, f"{user.name} is added on database | OnStart stage")
            # First user save 
            self.data_controller.save(user=user)
            
            # Send welcome message to user  
            WELCOME_TEXT = f"Привет!\nЯ игровой бот основанный на OpenAI!\nЧтобы начать играть нужно пройти небольшую анкету,"  \
            "чтобы вы могли погрузиться в мир который вам больше интересен!"
            WELCOME_TEXT += f"\n\nВерсия бота: {self.BOT_VERSION}"
            await context.bot.send_message(chat_id=update.effective_chat.id, text = WELCOME_TEXT)
            
            replyKeyboardMarkup = ReplyKeyboardMarkup([["Начать", "Отмена"]], one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text("Чтобы начать играть, вам нужно пройти анкету.\nНажмите 'Начать' чтобы продолжить\nНажмите 'Отмена' чтобы выйти из бота", reply_markup=replyKeyboardMarkup)        
            self.states[self.STATE_START] = [MessageHandler(filters.Regex("^Начать$"), self.state_show_form), MessageHandler(filters.Regex("^Отмена$"), self.on_cancel)]
        else:
            user = self.users[update.effective_user.id]
            logging.log(logging.INFO, f"{user.name} is restarded bot or loaded again | OnStart stage")

            # Send welcome message to user
            if user.isReady == True:  
                WELCOME_TEXT = f"Привет!\nМы помним вас, вы можете продолжить сессию либо пройти анкету заново."
            else:
                WELCOME_TEXT = f"Привет!\nМы помним вас, но у вас не пройдена анкета, чтобы начать играть вам надо пройти анкету."

            WELCOME_TEXT += f"\n\nВерсия бота: {self.BOT_VERSION}"
            await context.bot.send_message(chat_id=update.effective_chat.id, text = WELCOME_TEXT)
            
            if user.isReady == True:  
                replyKeyboardMarkup = ReplyKeyboardMarkup([["Продолжить", "Снова", "Отмена"]], one_time_keyboard=True, resize_keyboard=True)
                await update.message.reply_text("Нажмите 'Продолжить' чтобы продолжить игровую сессию\nНажмите 'Снова' чтобы пройти анкету заного\nНажмите 'Отмена' чтобы выйти из бота", reply_markup=replyKeyboardMarkup)        
                self.states[self.STATE_START] = [MessageHandler(filters.Regex("^Продолжить$"), self.on_game_start),
                    MessageHandler(filters.Regex("^Снова$"), self.state_show_form), MessageHandler(filters.Regex("^Отмена$"), self.on_cancel)]
            else:
                replyKeyboardMarkup = ReplyKeyboardMarkup([["Начать", "Отмена"]], one_time_keyboard=True, resize_keyboard=True)
                await update.message.reply_text("Нажмите 'Начать' чтобы продолжить\nНажмите 'Отмена' чтобы выйти из бота", reply_markup=replyKeyboardMarkup)               
                self.states[self.STATE_START] = [MessageHandler(filters.Regex("^Начать$"), self.state_show_form), MessageHandler(filters.Regex("^Отмена$"), self.on_cancel)]

        # Create message handler 
        if self.message_handler == None:
            self.message_handler = MessageHandler(filters= filters.TEXT, callback=self.on_get_message)
            self.application.add_handler(self.message_handler)

        return self.STATE_START

    async def on_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await update.message.reply_text("Bye! If you want to back, type \start command.")
        return ConversationHandler.END

    async def state_show_form(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = self.users[update.effective_user.id]
        user.isReady = False
        user.ai_messages_history.clear()

        logging.log(logging.INFO, f"{user.name} is on StateShowForm stage.")

        # Clear previous data 
        if len(user.data_list) != 0:
            user.data_list.clear() 
            
        # Initialize the data struct  
        if user.form_controller == None:         
            form_controller = GameGPTFormController()
            form_controller.botCore = self
            form_controller.onEnd = self.on_form_done
            form_controller.user = user

            # initialize our data vars for controller
            form_controller.add(msg="свой возраст.",type="age")
            form_controller.add(msg="жанр игры.",   type="genre")
            form_controller.add(msg="сеттинг игры.",type="setting") 
            # 4. TODO: GPT Model
            user.form_controller = form_controller
        else:
            user.form_controller.reset()

        #for form in user.form_controller.list_forms:
        #    logging.log(logging.INFO, f"{user.name} form {form.type}")

        # Show first 
        user.form_controller.next(update=update,context=context,reply_markup=ReplyKeyboardRemove())
        
        return self.STATE_FORM_GAME_START

    # Handle all user inputs 
    async def on_get_message(self, update:Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        # If on_get_message callback is already working 
        # but not added user in database trying to send text messages 
        if not update.effective_user.id in self.users:
            return 

        user = self.users[update.effective_user.id]
        logging.log(logging.INFO, f"OnGetMessage | User {user.name} {update.effective_chat.id} said {update.message.text}!")

        if user.form_controller != None:
            if user.form_controller.isCommited == False: # Don't try push any kind of message if form is filled 
                # Push user message and show next form page
                user.form_controller.push(update.message.text)
                user.form_controller.next(update=update,context=context)
        else:
            # If user is passed on_form_done stage and go next
            if user.isReady == True:
                msg = update.message.text
                # User cannot user any words 
                if msg.isdigit() == False:
                    logging.log(logging.INFO, f"wrong message {msg} from {self.users[update.effective_chat.id].name}")
                    await context.bot.send_message(chat_id=update.effective_chat.id, text = "Вы можете использовать только числа!")
                    return
                # User cannot use numbers beyond range 
                if int(msg) < 1 or int(msg) > 4:
                    logging.log(logging.INFO, f"wrong message {msg} from {self.users[update.effective_chat.id].name}")
                    await context.bot.send_message(chat_id=update.effective_chat.id, text = "Вы можете использовать только числа в диапазоне от 1 до 4!")
                    return
                # Show keyboard numbers to make using bot a bit easier 
                gameKeyboardMarkup = ReplyKeyboardMarkup([["1", "2", "3", "4"]], one_time_keyboard=True, resize_keyboard=True)
                loop = asyncio.get_event_loop()
                loop.create_task(self.print_message_from_ai(text=msg, context=context, update=update, reply_markup=gameKeyboardMarkup))
            
    # Small utility function to send message  
    async def send(self, text, update:Update, reply_markup: ReplyMarkup = None) -> None:
        await self.application.bot.sendMessage(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup)
         
    async def on_form_done(self, update:Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = self.users[update.effective_user.id]
        logging.log(logging.INFO, f"{user.name} is on OnFormDone stage.")
        
        # Show two buttons. 
        # Done and Again          
        replyKeyboardMarkup = ReplyKeyboardMarkup([["Продолжить"], ["Снова"]], one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("Готово!\nЕсли хотите продолжить нажмите кнопку 'Продолжить'\nЕсли хотите изменить анкету нажимите кнопку 'Снова'", reply_markup= replyKeyboardMarkup)
        self.states[self.STATE_FORM_GAME_START] = [MessageHandler(filters.Regex("^Продолжить$"), self.on_game_start), MessageHandler(filters.Regex("^Снова$"), self.state_show_form)]
        user.isReady = True

        # Last user data save, next we are save only messages
        self.data_controller.save(user=user)
            
        return self.STATE_FORM_GAME_START

    async def print_message_from_ai(self, text, update:Update, context: ContextTypes.DEFAULT_TYPE, reply_markup: ReplyMarkup = None) -> None:
        if self.debug_turn_off_ai == False:
            user = self.users[update.effective_user.id]

            # Show "please wait" message 
            await context.bot.send_message(chat_id=update.effective_chat.id, text = "Ответ принят. Генерируется ситуация...", reply_markup=reply_markup)
            # Get response by user message 
            response = self.ai.get_response(text, user)
            # If we are get empty string it's a bad request for telegram we are handle it too.
            if response == "" or response == None:
                await context.bot.send_message(chat_id=update.effective_chat.id, text = "Something is wrong, please try again!")
                logging.log(logging.ERROR, "Empty string was given from OpenAI...")
                return

            # If we are get error from OpenAI we are send special message and send error to log 
            if self.ai.get_error == True:
                await context.bot.send_message(chat_id=update.effective_chat.id, text = "Something is wrong, please try again!")
                logging.log(logging.ERROR, response)
            
            # Print response 
            await context.bot.send_message(chat_id=update.effective_chat.id, text = response, reply_markup=reply_markup)
            
            # Save history
            self.data_controller.save_msg_history(user=user)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text = "You got jebatted KEKW\nAI is turned off...", reply_markup=reply_markup)
        
    def show_first_ai_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = self.users[update.effective_user.id]
        gameKeyboardMarkup = ReplyKeyboardMarkup([["1", "2", "3", "4"]], one_time_keyboard=True, resize_keyboard=True)
        loop = asyncio.get_event_loop()
        len_msh_history = len(user.ai_messages_history) 
        # Resume game 
        if len_msh_history > 1:
            loop.create_task(self.send(text=user.ai_messages_history[len_msh_history - 1]["content"], update=update, reply_markup=gameKeyboardMarkup))
        else: # New game
            loop.create_task(self.print_message_from_ai(text="", context=context, update=update, reply_markup=gameKeyboardMarkup))

    async def on_game_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int: 
        user = self.users[update.effective_user.id]
        logging.log(logging.INFO, f"{user.name} is on OnGameStart stage.")

        # Delete form controller because we don't needed when user is filled form
        #del user.form_controller
        user.form_controller = None

        if self.debug_turn_off_game_page == True:
            await context.bot.send_message(chat_id=update.effective_chat.id, text = "debug_turn_off_game_page",  reply_markup=ReplyKeyboardRemove())     
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text = "Игра началась!\nДля того чтобы играть, вы можете использовать только числа!",  reply_markup=ReplyKeyboardRemove())
            # Initialize bot ai struct            
            self.ai.get_context(user)
            # First generated message 
            self.show_first_ai_message(update, context)
    
        return ConversationHandler.END

    async def command_new(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        # If some user is not added in users database, wants to use clear command 
        if not update.effective_user.id in self.users:
            await update.message.reply_text("Use /start to use this bot.")
            return 

        user = self.users[update.effective_user.id]

        if not self.ai == None:
            if user.isReady == True:
                await update.message.reply_text("Bot's message history is cleared.")
                self.ai.clear_messages_history(user)   
                self.show_first_ai_message(update, context)
                return

        await update.message.reply_text("Bot's message history can't be cleared, because user is not fill form.") 

    async def command_clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        # If some user is not added in users database, wants to use clear command 
        if not update.effective_user.id in self.users:
            await update.message.reply_text("Use /start to use this bot.")
            return 
        user = self.users[update.effective_user.id]

        if not self.ai == None:
            if user.isReady == True:
                await update.message.reply_text("Bot's message history is cleared.")
                self.ai.clear_messages_history(user, to_first=True)   
                self.show_first_ai_message(update, context)
                return

        await update.message.reply_text("Bot's message history can't be cleared, because user is not fill form.") 

    # TODO: Only admins can use this 
    async def debug_print_all_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(f"All users in database {len(self.users)}:")
        for key in self.users:
            await update.message.reply_text(f"name:{self.users[key].name} key:{key}")

    async def debug_show_save_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        # TODO: Bad practice, need to make choice of users and show data  
        await update.message.reply_text(f"All users in database {len(self.users)}:")
        for key in self.users:
            user = self.users[key]
            await update.message.reply_text(f"name:{user.name} key:{key}")    

            for data_key in user.data_list:
                await update.message.reply_text(f"{data_key} | {user.data_list[data_key]}")        

    async def debug_show_message_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        pass 

    async def command_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        # Displays info on how to use the bot
        HELP_TEXT = "Other commands in menu: \n/clear - Clear - Retry | clear bot's history to first generated message \n/new  -  New Game | clear bot's history to initial message, generate new situation" \
                    "\n/debug_show_save_data - Debug! Shows saved data \n/debug_print_all_users - Debug! Print all users saved in database \n/debug_show_message_history - Debug! Print user's message history"

        await update.message.reply_text(f"Use /start to use this bot.\n\n{HELP_TEXT}")




