"""No-card tokenizer/Jinja only; never import torch/transformers or model code."""
from pathlib import Path

class CPUPinnedTokenizer:
    def __init__(self,folder):
        from tokenizers import Tokenizer
        from jinja2.sandbox import ImmutableSandboxedEnvironment
        self.folder=Path(folder);self.tokenizer=Tokenizer.from_file(str(self.folder/'tokenizer.json'))
        self.tokenizer.no_truncation();self.tokenizer.no_padding()
        env=ImmutableSandboxedEnvironment(trim_blocks=True,lstrip_blocks=True)
        def fail(message):raise ValueError(message)
        env.globals['raise_exception']=fail
        self.template=env.from_string((self.folder/'chat_template.jinja').read_text(encoding='utf-8'))
    def apply_chat_template(self,messages,tokenize,**kwargs):
        text=self.template.render(messages=messages,**kwargs)
        return self.encode(text,add_special_tokens=False) if tokenize else text
    def encode(self,text,add_special_tokens=False):return self.tokenizer.encode(text,add_special_tokens=add_special_tokens).ids
    def decode(self,ids,skip_special_tokens=False):return self.tokenizer.decode(ids,skip_special_tokens=skip_special_tokens)
    def convert_tokens_to_ids(self,token):return self.tokenizer.token_to_id(token)
