import json 
import logging
import os
from User import GameGPTUser 

# BD Structure
# Data folder -> *user_name*_folder 
#                *user_name*_basics -> All data from User struct
#                *user_name*_message_history -> Message history from Game session  


class GameGPTUserDataController:
    DATA_FOLDER_NAME = "Data"
    
    def __init__(self) -> None:
        logging.log(logging.INFO, "[GameGPTUserDataController] Startup...")

        self.__create_data_folder()
       
    # Read existing data base and load it into core 
    def read_all_data_base(self, users: dict[str, GameGPTUser] = None) -> None:
        logging.log(logging.INFO, "[GameGPTUserDataController] Read existing data base...")
        dirs_names = []

        for (dirpath, dirnames, filenames) in os.walk(os.path.join(os.getcwd(), self.DATA_FOLDER_NAME)):
            dirs_names.append(dirnames)        

        logging.log(logging.INFO, dirs_names)
        if len(dirs_names) == 0:
            logging.log(logging.INFO, f"[GameGPTUserDataController] No found any folders in data folder! Probably it's the first start.")
            return

        for dirname in dirs_names[0]:
            if len(dirname) == 0:
                continue

            path_basics = os.path.join(os.getcwd(), self.DATA_FOLDER_NAME + f"\\{dirname}") + f"\\{dirname}_basics.json"
            try:
                with open(path_basics, "r") as basics_file:
                    data = json.load(basics_file)
                    logging.log(logging.INFO, f"[GameGPTUserDataController] Loaded file {path_basics} ")
                    logging.log(logging.INFO, f"[GameGPTUserDataController] {data} ")
                    try:
                        if not str(dirname).isdigit():
                            continue

                        id = int(dirname)
                        if id == 0:
                            logging.log(logging.ERROR, f"[GameGPTUserDataController] WTF moment, user has zero id!")
                            # continue

                        users[id] = GameGPTUser()

                        users[id].name = data["name"]
                        users[id].ai_gpt_model = data["ai_gpt_model"]
                        users[id].id = int(id)
                        users[id].isReady = bool(data["isReady"])
                        users[id].language = data["language"]

                        # TODO or FIXME: That's veeery bad, ass  \
                        for key in ["age","genre","setting"]:
                            if key in data:
                                users[id].data_list[key] = data[key]

                        path_history = os.path.join(os.getcwd(), self.DATA_FOLDER_NAME + f"\\{dirname}") + f"\\{dirname}_history.json"
                        try:
                            with open(path_history, "r") as history_file:
                                data = json.load(history_file)
                                logging.log(logging.INFO, f"[GameGPTUserDataController] Loaded file {path_history} ")
                                try:
                                    users[id].ai_messages_history = data
                                except KeyError as error:
                                    logging.log(logging.ERROR, f"[GameGPTUserDataController] KeyError! Failed to read history json file! Skip {dirname} | {error.args}")
                        except ValueError as error:
                            logging.log(logging.ERROR, f"[GameGPTUserDataController] ValueError! Failed to open history json file! Skip {dirname} | {error.args}")
                    except KeyError as error:          
                        logging.log(logging.ERROR, f"[GameGPTUserDataController] KeyError! Failed to read basics json file! Skip {dirname} | {error.args}")
            except ValueError as error:
                logging.log(logging.ERROR, f"[GameGPTUserDataController] ValueError! Failed to open basics json file! Skip {dirname} | {error.args}")

    # Save all data from user 
    def save(self, user: GameGPTUser = None) -> None:
        # Don't continue if user is none
        if user == None:
            return 

        # Check user folder on exist 
        if not self.__create_user_folder(user.id):
            return 

        data = { "name": user.name,
            "language": user.language,
            "isReady": user.isReady,
            "ai_gpt_model":user.ai_gpt_model,        
            "id":user.id,        
        }

        if len(user.data_list) != 0:
            data.update(user.data_list)

        data_in_json = json.dumps(data)
        # Testing 
        try:
            y = json.loads(data_in_json)
        except ValueError:
            logging.log(logging.ERROR, "[GameGPTUserDataController] Test json failed.")
            return 

        #logging.log(logging.INFO, y)
        try:
            path = os.path.join(os.getcwd(), self.DATA_FOLDER_NAME + f"\\{user.id}") + f"\\{user.id}_basics.json"
            logging.log(logging.INFO, f"[GameGPTUserDataController] Try to save... Path {path}")

            file = open(path, "+w")
            file.write(data_in_json)
            file.close()
        except OSError:
            logging.log(logging.ERROR, f"[GameGPTUserDataController] Failed to save {user.name} | {user.id} basics json file")
     
    # Save only message history
    def save_msg_history(self, user: GameGPTUser = None) -> None:
        # Check user folder on exist 
        if not self.__create_user_folder(user.id):
            return     

        data_in_json = json.dumps(user.ai_messages_history)

        # Testing 
        try:
            y = json.loads(data_in_json)
        except ValueError:
            logging.log(logging.ERROR, "[GameGPTUserDataController] Test json failed.")
            return 

        #logging.log(logging.INFO, y)
        try:
            path = os.path.join(os.getcwd(), self.DATA_FOLDER_NAME + f"\\{user.id}") + f"\\{user.id}_history.json"
            logging.log(logging.INFO, f"[GameGPTUserDataController] Try to save... Path {path}")

            file = open(path, "+w")
            file.write(data_in_json)
            file.close()
        except OSError:
            logging.log(logging.ERROR, f"[GameGPTUserDataController] Failed to save {user.name} | {user.id} history json file")

    def __create_data_folder(self) -> bool:
        if not os.path.exists(self.DATA_FOLDER_NAME):
            try:
                os.makedirs(self.DATA_FOLDER_NAME)
                return True
            except OSError:
                logging.log(logging.ERROR, "[GameGPTUserDataController] Failed to create data folder.")
                return False
                
        return True
    
    def __create_user_folder(self, user_id) -> bool:  
        path = f"{self.DATA_FOLDER_NAME}\\{user_id}"      
        if not os.path.exists(path):
            try:
                os.makedirs(path)
                return True
            except OSError:
                logging.log(logging.ERROR, f"[GameGPTUserDataController] Failed to create user {user_id} folder.")
                return False

        return True
    