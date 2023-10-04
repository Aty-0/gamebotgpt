import logging
import os

import openai

from User import GameGPTUser


class GameGPTAICore:
    API_KEY = os.getenv("GAME_GPT_AI_API_KEY", "None") 
    ORG_ID = os.getenv("GAME_GPT_AI_ORG_ID", "None") 
    
    MAX_TOKENS = 500

    # If we are get error
    get_error:bool = True
    
    def __init__(self):        
        logging.log(logging.INFO, "OpenAI: Run bot AI core...")
        if self.API_KEY == "None" or self.ORG_ID == "None":
            logging.log(logging.FATAL, "OpenAI: API_KEY or ORG_ID is none, we can't continue!")
            return 
        openai.organization = self.ORG_ID
        openai.api_key = self.API_KEY

    def get_context(self, user: GameGPTUser):       
        genre = user.data_list["genre"]
        setting = user.data_list["setting"]
        age = user.data_list["age"]
        # FIXME: Better initial message 
         
        # Initial message for AI
        text = "You need to imagine one game situation for player, next you need to imagine 4 ways to pass it, you can't make trees of ways. Then you are wait to anwers, don't generate situation next, when player choise something," \
               "you need to create another game situation by his choice. Consider that game will be infinity, player never end it." \
               "You tell to play only what's game situation you invented and 4 ways." \
               f"Game world will be in a genre, {genre}, in that setting {setting}. Consider that user's age is {age} and you need to make "  \
               f"world interesting for that type of age. Use {user.language} for explain." 
  
        # First message is always the context message  
        if len(user.ai_messages_history) == 0:
          user.ai_messages_history.append({"role": "user", "content":text})
        else:
          user.ai_messages_history[0] = {"role": "user", "content":text}

    def clear_messages_history(self, user: GameGPTUser, to_first: bool=False):
        logging.log(logging.INFO, f"OpenAI: Bot's message history is cleared for {user.name}")
        user.ai_messages_history = [user.ai_messages_history[item] for item in range(0, 2 if to_first == False else 1 )]
        logging.log(logging.INFO, f"OpenAI: {user.ai_messages_history}")
        
        
    def get_response(self, prompt:str, user: GameGPTUser):
        # Save message to history for context

        # if prompt is empty we are try to get response by existing history
        # like on start, we are have first context message and wait response from AI
        if prompt != "":  
          user.ai_messages_history.append(
            { "role": "user", "content": prompt} 
          )

        # Try to get response from OpenAI
        try:
          # Default chat bot response example:
          response = openai.ChatCompletion.create(
            model = user.ai_gpt_model,
            messages= user.ai_messages_history,
            temperature = 1, # text randomness 
            max_tokens = self.MAX_TOKENS,
          )
        
          self.get_error = False

          # Print to log AI's message 
          log_decoded_reponse_message = str(response['choices'][0]['message']['content']).encode("UTF-8").decode("UTF-8")
          logging.log(logging.INFO, f"OpenAI: response: *{ log_decoded_reponse_message }")

          # Save GPT messages
          response_message = response['choices'][0]['message']['content']
          if response_message != "" or response_message != None:
            user.ai_messages_history.append(
              { "role": "assistant", "content": response_message} 
            )

          return response_message
        # TODO: MOAR error codes
        except openai.error.RateLimitError as e:
          self.get_error = True
          return f"OpenAI API request exceeded rate limit: {e}"
        except openai.error.InvalidRequestError as e:
          self.get_error = True
          return f"OpenAI API request was invalid: {e}"
        except openai.error.Timeout as e:
          self.get_error = True
          return f"OpenAI API request timed out: {e}"
        except openai.error.APIConnectionError as e:
          self.get_error = True
          return f"OpenAI API request failed to connect: {e}"
        except openai.error.AuthenticationError as e:
          self.get_error = True
          return f"OpenAI API request was not authorized:{e}"
        
