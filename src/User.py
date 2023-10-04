class GameGPTUser:
    def __init__(self) -> None:                
        self.data_list : dict = { }
        self.name: str = ''

        self.form_controller = None
        self.isReady = False
        
        self.language: str = "Russian" # TODO

        self.ai_messages_history = []     
        self.ai_gpt_model:str = "gpt-3.5-turbo"
        self.id: int = 0