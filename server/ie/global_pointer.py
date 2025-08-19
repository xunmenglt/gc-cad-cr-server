import torch
from torch import nn
from transformers import Qwen2Model,Qwen2PreTrainedModel
from transformers.models.bert import BertPreTrainedModel, BertModel
from transformers.models.bert import BertTokenizerFast
from ie.ie_utils import multilabel_categorical_crossentropy

class SinusoidalPositionEmbedding(nn.Module):
    """定义Sin-Cos位置Embedding
    """

    def __init__(
            self, output_dim, merge_mode='add', custom_position_ids=False):
        super(SinusoidalPositionEmbedding, self).__init__()
        self.output_dim = output_dim
        self.merge_mode = merge_mode
        self.custom_position_ids = custom_position_ids

    def forward(self, inputs):
        if self.custom_position_ids:
            seq_len = inputs.shape[1]
            inputs, position_ids = inputs
            position_ids = position_ids.type(torch.float)
        else:
            input_shape = inputs.shape
            batch_size, seq_len = input_shape[0], input_shape[1]
            position_ids = torch.arange(seq_len).type(torch.float)[None]
        indices = torch.arange(self.output_dim // 2).type(torch.float)
        indices = torch.pow(10000.0, -2 * indices / self.output_dim)
        embeddings = torch.einsum('bn,d->bnd', position_ids, indices)
        embeddings = torch.stack([torch.sin(embeddings), torch.cos(embeddings)], dim=-1)
        embeddings = torch.reshape(embeddings, (-1, seq_len, self.output_dim))
        if self.merge_mode == 'add':
            return inputs + embeddings.to(inputs.device)
        elif self.merge_mode == 'mul':
            return inputs * (embeddings + 1.0).to(inputs.device)
        elif self.merge_mode == 'zero':
            return embeddings.to(inputs.device)



class QwenForEffiGlobalPointer(Qwen2PreTrainedModel):
    def __init__(self, config):
        super().__init__(config)
        self.backbone=Qwen2Model(config=config)
        self.hidden_size = self.config.hidden_size
        self.ent_type_size = 1
        self.inner_dim = 64
        self.RoPE = True
        self.dense_1 = nn.Linear(self.hidden_size, self.inner_dim * 2)
        self.dense_2 = nn.Linear(self.hidden_size, self.ent_type_size * 2)
        
    def forward(self, input_ids,attention_mask,**kwargs):

        input_ids = input_ids
        attention_mask = attention_mask

        context_outputs = self.backbone(input_ids, attention_mask)
        last_hidden_state = context_outputs.last_hidden_state
        outputs = self.dense_1(last_hidden_state)
        qw, kw = outputs[..., ::2], outputs[..., 1::2]
        batch_size = input_ids.shape[0]

        if self.RoPE:
            pos = SinusoidalPositionEmbedding(self.inner_dim, 'zero')(outputs)
            cos_pos = pos[..., 1::2].repeat_interleave(2, dim=-1) # e.g. [0.34, 0.90] -> [0.34, 0.34, 0.90, 0.90]
            sin_pos = pos[..., ::2].repeat_interleave(2, dim=-1)
            qw2 = torch.stack([-qw[..., 1::2], qw[..., ::2]], 3)
            qw2 = torch.reshape(qw2, qw.shape)
            qw = qw * cos_pos + qw2 * sin_pos
            kw2 = torch.stack([-kw[..., 1::2], kw[..., ::2]], 3)
            kw2 = torch.reshape(kw2, kw.shape)
            kw = kw * cos_pos + kw2 * sin_pos
        
        logits = torch.einsum('bmd,bnd->bmn', qw, kw) / self.inner_dim ** 0.5
        bias = torch.einsum('bnh->bhn', self.dense_2(last_hidden_state)) / 2
        logits = logits[:, None] + bias[:, ::2, None] + bias[:, 1::2, :, None]  # logits[:, None] 增加一个维度
        #logits.shape=[2,1,512,512]

        mask = torch.triu(attention_mask.unsqueeze(2) * attention_mask.unsqueeze(1))
        
        with torch.no_grad():
            prob = torch.sigmoid(logits) * mask.unsqueeze(1)
            topk = torch.topk(prob.view(batch_size, self.ent_type_size, -1), 50, dim=-1)

        return {
            'input_ids': input_ids,
            'attention_mask': attention_mask,
            'logits': logits,
            'topk_probs': topk.values,
            'topk_indices': topk.indices
        }

    def compute_loss(self, forward_outputs, label_ids, **kwargs):

        input_ids = forward_outputs['input_ids']
        attention_mask = forward_outputs['attention_mask']
        logits = forward_outputs['logits']

        mask = torch.triu(attention_mask.unsqueeze(2) * attention_mask.unsqueeze(1))
        y_pred = logits - (1-mask.unsqueeze(1))*1e12
        y_true = label_ids.view(input_ids.shape[0] * self.ent_type_size, -1)
        y_pred = y_pred.view(input_ids.shape[0] * self.ent_type_size, -1)
        loss = multilabel_categorical_crossentropy(y_pred, y_true)

        return loss
    

class BertForEffiGlobalPointer(BertPreTrainedModel):
    def __init__(self, config):
        # encodr: RoBerta-Large as encoder
        # inner_dim: 64
        # ent_type_size: ent_cls_num
        super().__init__(config)
        self.bert = BertModel(config)
        self.hidden_size = config.hidden_size
        self.ent_type_size = 1
        self.inner_dim = 64
        self.RoPE = True
        self.dense_1 = nn.Linear(self.hidden_size, self.inner_dim * 2)
        self.dense_2 = nn.Linear(self.hidden_size, self.ent_type_size * 2)

    def forward(self, input_ids, attention_mask, token_type_ids, **kwargs):
        context_outputs = self.bert(input_ids, attention_mask, token_type_ids)
        last_hidden_state = context_outputs.last_hidden_state # [bz, seq_len, hidden_dim]
        outputs = self.dense_1(last_hidden_state) # [bz, seq_len, 2*inner_dim]
        qw, kw = outputs[..., ::2], outputs[..., 1::2]  # 从0,1开始间隔为2 最后一个纬度，从0开始，取奇数位置所有向量汇总
        batch_size = input_ids.shape[0]
        if self.RoPE:
            pos = SinusoidalPositionEmbedding(self.inner_dim, "zero")(outputs)
            cos_pos = pos[..., 1::2].repeat_interleave(2, dim=-1) # e.g. [0.34, 0.90] -> [0.34, 0.34, 0.90, 0.90]
            sin_pos = pos[..., ::2].repeat_interleave(2, dim=-1)
            qw2 = torch.stack([-qw[..., 1::2], qw[..., ::2]], 3)
            qw2 = torch.reshape(qw2, qw.shape)
            qw = qw * cos_pos + qw2 * sin_pos
            kw2 = torch.stack([-kw[..., 1::2], kw[..., ::2]], 3)
            kw2 = torch.reshape(kw2, kw.shape)
            kw = kw * cos_pos + kw2 * sin_pos
        logits = torch.einsum("bmd,bnd->bmn", qw, kw) / self.inner_dim ** 0.5
        bias = torch.einsum("bnh->bhn", self.dense_2(last_hidden_state)) / 2
        logits = logits[:, None] + bias[:, ::2, None] + bias[:, 1::2, :, None]  # logits[:, None] 增加一个维度

        mask = torch.triu(attention_mask.unsqueeze(2) * attention_mask.unsqueeze(1)) # 上三角矩阵

        with torch.no_grad():
            prob = torch.sigmoid(logits) * mask.unsqueeze(1)
            topk = torch.topk(prob.view(batch_size, self.ent_type_size, -1), 50, dim=-1)


        return {
            'input_ids': input_ids,
            'attention_mask': attention_mask,
            'logits': logits,
            'topk_probs': topk.values,
            'topk_indices': topk.indices
        }

    def compute_loss(self, forward_outputs, label_ids, **kwargs):

        input_ids = forward_outputs['input_ids']
        attention_mask = forward_outputs['attention_mask']
        logits = forward_outputs['logits']

        mask = torch.triu(attention_mask.unsqueeze(2) * attention_mask.unsqueeze(1))
        y_pred = logits - (1-mask.unsqueeze(1))*1e12
        y_true = label_ids.view(input_ids.shape[0] * self.ent_type_size, -1)
        y_pred = y_pred.view(input_ids.shape[0] * self.ent_type_size, -1)
        loss = multilabel_categorical_crossentropy(y_pred, y_true)

        return loss