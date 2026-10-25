"""Full-width text verifier; only pretrained top transformer block differs in trainability."""
import torch
from torch import nn
from transformers import AutoConfig
from transformers.models.deberta_v2.modeling_deberta_v2 import DebertaV2Layer,build_relative_position
import common092 as c
class Head(nn.Module):
    def __init__(self):
        super().__init__();self.norm=nn.LayerNorm(1024);self.attention=nn.Linear(1024,1);self.dropout=nn.Dropout(.1);self.classifier=nn.Linear(1024,3)
    def forward(self,x):
        x=self.norm(x);weights=self.attention(x).softmax(0);return self.classifier(self.dropout((x*weights).sum(0)))
class Verifier(nn.Module):
    def __init__(self,adapt=True):
        super().__init__();cfg=AutoConfig.from_pretrained(c.ROOT/'.local_models/032/deberta_v3_nli',local_files_only=True)
        cfg.hidden_dropout_prob=0.;cfg.attention_probs_dropout_prob=0.
        self.layer=DebertaV2Layer(cfg);self.head=Head();source=torch.load(c.PRIVATE/'pretrained_top.pt',map_location='cpu',weights_only=True)
        self.layer.load_state_dict(source['layer']);self.register_buffer('relative',source['relative']);self.cfg=cfg
        for p in self.layer.parameters():p.requires_grad_(adapt)
    def encode(self,h,mask):
        attention=mask[:,None,None,:]*mask[:,None,:,None]
        pos=build_relative_position(h,h,bucket_size=self.cfg.position_buckets,max_position=self.cfg.max_position_embeddings)
        out,_=self.layer(h,attention,relative_pos=pos,rel_embeddings=self.relative)
        return out[:,0]
