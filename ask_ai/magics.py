# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/00_magics.ipynb.

# %% auto 0
__all__ = ['CONTEXT_MAX_WORDS', 'conversation_api', 'coding_api', 'OpenAIAPI', 'ConversationAPI', 'CodingAPI',
           'collect_code_history', 'ai_ask', 'ai_continue', 'ai_code', 'load_ipython_extension']

# %% ../nbs/00_magics.ipynb 3
import os
import openai
from IPython.display import display, Markdown

openai.api_key = os.environ['OPENAI_API_KEY']
CONTEXT_MAX_WORDS = 2200

# %% ../nbs/00_magics.ipynb 4
from abc import ABC, abstractmethod

class OpenAIAPI(ABC):
    def __init__(self):
        self.reset_context()

    @abstractmethod
    def reset_context(self):
        pass

    def get_completion(self, prompt, new_conversation=True):
        if new_conversation:
            self.reset_context()
        
        self.context.append(
            {
                'role':'user',
                'content': prompt
            }
        )

        response = openai.ChatCompletion.create(
            model = "gpt-3.5-turbo",
            messages = self.context
        )
        
        completion = self.extract_completion(response)
        self.extend_context(response)
        self.prune_context()

        self.completion = completion    
        self.response = response  # useful for debugging
    
    def extract_completion(self, response):
        return response['choices'][0].message.content.strip()
    
    def extend_context(self, response):
        self.context.append(response['choices'][0].message.to_dict())
    
    def prune_context(self):
        # Prune context to under CONTEXT_MAX_WORDS words. That should be ~CONTEXT_MAX_WORDS*1.5 tokens, leaving room for the prompt and completion.
        pruned_context = []
        word_count = 0
        while self.context:
            last_message = self.context.pop()
            word_count += len(last_message['content'].split())
            if word_count < CONTEXT_MAX_WORDS:
                pruned_context.append(last_message)
            else:
                break
        pruned_context.reverse()
        self.context = pruned_context

    def display_completion(self):
        display(Markdown(self.completion))

class ConversationAPI(OpenAIAPI):
    def reset_context(self):
        self.context = [
            {
                'role': 'system',
                'content': 'You are an expert programmer helping out a friend. Your friend is using Python in Jupyter Notebook. Give a succinct answer that a programmer with one year of professional experience would easily understand.'
            }
        ]

class CodingAPI(OpenAIAPI):
    def reset_context(self):
        self.context = [
            {
                'role': 'system',
                'content':
                    '''
                        You are a programming assistant. You will be passed code and instruction what to do next. Output the code that should be added next. Your prompt will be in the following format:

                        Code: {code}
                        Instruction: {instruction}

                        Output only the code that should be added next. Do not output the entire code. Do not output the instruction. Do not output the prompt. Do not output any other text. Do not output any lines that are not indented correctly. Do not output any lines that are not valid Python.
                    '''
            }
        ]

conversation_api = ConversationAPI()
coding_api = CodingAPI()

# %% ../nbs/00_magics.ipynb 5
def collect_code_history():
    history = [cell_content for session, cell_number, cell_content in get_ipython().history_manager.get_tail()]
    collected_code = ''
    word_count = 0
    while history:
        last_cell_content = history.pop()
        word_count += len(last_cell_content.split())
        if word_count < CONTEXT_MAX_WORDS:
            collected_code += ' ' + last_cell_content
        else:
            break
    return collected_code

# %% ../nbs/00_magics.ipynb 6
import base64
import re

def ai_ask(line, cell):
    conversation_api.get_completion(cell)
    conversation_api.display_completion()

def ai_continue(line, cell):
    conversation_api.get_completion(cell, False)
    conversation_api.display_completion()
    
def ai_code(line, cell):
    prompt = f'Code: {collect_code_history()}\nInstruction: {cell}'
    coding_api.get_completion(prompt)
    
    # this removes the boilerplate text from the completion
    pattern = r"^(Code|```).*\n"
    code = re.sub(pattern, "", coding_api.completion, flags=re.MULTILINE)
    
    encoded_code = base64.b64encode(code.encode()).decode()
    js_code = f"""
        var new_cell = Jupyter.notebook.insert_cell_below('code');
        new_cell.set_text(atob("{encoded_code}"));
    """
    get_ipython().run_cell_magic('javascript', '', js_code)

# %% ../nbs/00_magics.ipynb 7
def load_ipython_extension(ipython):
    ipython.register_magic_function(ai_ask, magic_kind='cell', magic_name='ai_ask')
    ipython.register_magic_function(ai_continue, magic_kind='cell', magic_name='ai_continue')
    ipython.register_magic_function(ai_code, magic_kind='cell', magic_name='ai_code')
