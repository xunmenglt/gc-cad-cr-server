import sys
sys.path.insert(0,'/opt/data/private/liuteng/code/paper/emr_mpo/src')
from ie.global_pointer import QwenForEffiGlobalPointer
from transformers import AutoTokenizer
import numpy as np
import torch

class IEAPI:
    def __init__(self,model_name_or_path:str="",model=None,tokenizer=None) -> None:
        if model_name_or_path:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name_or_path)
            self.model = QwenForEffiGlobalPointer.from_pretrained(model_name_or_path,trust_remote_code=True)
        else:
            self.model=model
            self.tokenizer=tokenizer
        self.model.eval()
        self.max_seq_length = 512

    def fush_multi_answer(self, has_answer, new_answer):
        # 对于某个id测试集，出现多个example时（例如同一个测试样本使用了多个模板而生成了多个example），此时将预测的topk结果进行合并
        # has为已经合并的结果，new为当前新产生的结果，
        # has格式为 {"ans": {"prob": float(prob[index_ids[ei]]), "pos": (s, e)}, ...}
        # new {"ans": {"prob": float(prob[index_ids[ei]]), "pos": (s, e)}, ...}
        # print("has_answer=", has_answer)
        for ans, value in new_answer.items():
            if ans not in has_answer.keys():
                has_answer[ans] = value
            else:
                has_answer[ans]["prob"] += value["prob"]
                has_answer[ans]["pos"].extend(value["pos"])
        return has_answer

    def get_predict_result(self, probs, indices, examples):
        probs = probs.squeeze(1)  # topk结果的概率
        indices = indices.squeeze(1)  # topk结果的索引
        # print("probs=", probs) # [n, m]
        # print("indices=", indices) # [n, m]
        predictions = {}
        topk_predictions = {}
        idx = 0
        for prob, index in zip(probs, indices):
            index_ids = torch.Tensor([i for i in range(len(index))]).long()
            topk_answer = list()
            answer = []
            topk_answer_dict = dict()
            # TODO 1. 调节阈值 2. 处理输出实体重叠问题
            entity_index = index[prob > 0.3]
            index_ids = index_ids[prob > 0.3]
            for ei, entity in enumerate(entity_index):
                # 1D index转2D index
                start_end = np.unravel_index(
                    entity, (self.max_seq_length, self.max_seq_length))
                s = examples["offset_mapping"][idx][start_end[0]][0]
                e = examples["offset_mapping"][idx][start_end[1]][1]
                ans = examples["content"][idx][s:e]
                if ans not in answer:
                    answer.append(ans)
                    # topk_answer.append({"answer": ans, "prob": float(prob[index_ids[ei]]), "pos": (s, e)})
                    topk_answer_dict[ans] = {
                        "prob":
                        float(prob[index_ids[ei]]),
                        "pos": [(s.detach().cpu().numpy().tolist(),
                                 e.detach().cpu().numpy().tolist())]
                    }

            predictions[idx] = answer
            if idx not in topk_predictions.keys():
                # print("topk_answer_dict=", topk_answer_dict)
                topk_predictions[idx] = topk_answer_dict
            else:
                # print("topk_predictions[id_]=", topk_predictions[id_])
                topk_predictions[idx] = self.fush_multi_answer(
                    topk_predictions[idx], topk_answer_dict)
            idx += 1

        for idx, values in topk_predictions.items():
            # values {"ans": {}, ...}
            answer_list = list()
            for ans, value in values.items():
                answer_list.append({
                    "answer": ans,
                    "prob": value["prob"],
                    "pos": value["pos"]
                })
            topk_predictions[idx] = answer_list

        return predictions, topk_predictions

    def request(self, text: str, entity_type: str, relation: str = None):
        assert text is not None and entity_type is not None
        if not relation:
            instruction = "找到文章中所有【{}】类型的实体？文章：【{}】".format(entity_type, text)
        else:
            instruction = "找到文章中【{}】的【{}】？文章：【{}】".format(
                entity_type, relation, text)

        inputs = self.tokenizer(instruction,
                                max_length=self.max_seq_length,
                                padding="max_length",
                                return_tensors="pt",
                                return_offsets_mapping=True)

        examples = {
            "content": [instruction],
            "offset_mapping": inputs["offset_mapping"],
        }

        batch_input = {
            "input_ids": inputs["input_ids"].to(self.model.device),
            "attention_mask": inputs["attention_mask"].to(self.model.device),
            "token_type_ids": inputs["token_type_ids"].to(self.model.device),
        }
        outputs = self.model(**batch_input)
        probs, indices = outputs["topk_probs"].cpu(), outputs["topk_indices"].cpu()
        predictions, topk_predictions = self.get_predict_result(
            probs, indices, examples=examples)
        return predictions, topk_predictions,instruction


if __name__ == "__main__":
    model_type = "bert"
    model_name_or_path = "/opt/data/private/liuteng/code/models/qwen2-ner-1.5b/checkpoint-30000"
    hugie = IEAPI(model_name_or_path=model_name_or_path)
    text = "金融资产管理公司违反金融法律、行政法规的,由中国人民银行依照有关法律和《金融违法行为处罚办法》给予处罚;"

    ## named entity recognition
    entity_type = "法律法规"
    predictions, topk_predictions,_ = hugie.request(text, entity_type)
    print("entity_type:{}".format(entity_type))
    print("predictions:\n{}".format(predictions))
    print("topk_predictions:\n{}".format(topk_predictions))
    print("\n\n")
    

    ## event extraction
    entity = "固定利率"
    relation = "年利率"
    predictions, topk_predictions,_ = hugie.request(text,
                                                  entity,
                                                  relation=relation)
    print("entity:{}, relation:{}".format(entity, relation))
    print("predictions:\n{}".format(predictions))
    print("topk_predictions:\n{}".format(topk_predictions))
    print("\n\n")

    ## event extraction
    entity = "塔吉克斯坦地震"
    relation = "震源位置"
    predictions, topk_predictions,_ = hugie.request(text,
                                                  entity,
                                                  relation=relation)
    print("entity:{}, relation:{}".format(entity, relation))
    print("predictions:\n{}".format(predictions))
    print("topk_predictions:\n{}".format(topk_predictions))
    print("\n\n")

    ## event extraction
    entity = "塔吉克斯坦地震"
    relation = "时间"
    predictions, topk_predictions,_ = hugie.request(text,
                                                  entity,
                                                  relation=relation)
    print("entity:{}, relation:{}".format(entity, relation))
    print("predictions:\n{}".format(predictions))
    print("topk_predictions:\n{}".format(topk_predictions))
    print("\n\n")

    ## event extraction
    entity = "塔吉克斯坦地震"
    relation = "影响"
    predictions, topk_predictions,_ = hugie.request(text,
                                                  entity,
                                                  relation=relation)
    print("entity:{}, relation:{}".format(entity, relation))
    print("predictions:\n{}".format(predictions))
    print("topk_predictions:\n{}".format(topk_predictions))
    print("\n\n")
    """
    Output results:

    entity_type:国家
predictions:
{0: ["塔吉克斯坦"]}
predictions:
{0: [{"answer": "塔吉克斯坦", "prob": 0.9999997615814209, "pos": [(tensor(57), tensor(62))]}]}



entity:塔吉克斯坦地震, relation:震源深度
predictions:
{0: ["10公里"]}
predictions:
{0: [{"answer": "10公里", "prob": 0.999994158744812, "pos": [(tensor(80), tensor(84))]}]}



entity:塔吉克斯坦地震, relation:震源位置
predictions:
{0: ["10公里", "距我国边境线最近约82公里", "北纬37.98度，东经73.29度", "北纬37.98度，东经73.29度，距我国边境线最近约82公里"]}
predictions:
{0: [{"answer": "10公里", "prob": 0.9895901083946228, "pos": [(tensor(80), tensor(84))]}, {"answer": "距我国边境线最近约82公里", "prob": 0.8584909439086914, "pos": [(tensor(107), tensor(120))]}, {"answer": "北纬37.98度，东经73.29度", "prob": 0.7202121615409851, "pos": [(tensor(89), tensor(106))]}, {"answer": "北纬37.98度，东经73.29度，距我国边境线最近约82公里", "prob": 0.11628123372793198, "pos": [(tensor(89), tensor(120))]}]}



entity:塔吉克斯坦地震, relation:时间
predictions:
{0: ["2月23日8时37分"]}
predictions:
{0: [{"answer": "2月23日8时37分", "prob": 0.9999995231628418, "pos": [(tensor(49), tensor(59))]}]}



entity:塔吉克斯坦地震, relation:影响
predictions:
{0: ["新疆喀什等地震感强烈"]}
predictions:
{0: [{"answer": "新疆喀什等地震感强烈", "prob": 0.9525265693664551, "pos": [(tensor(123), tensor(133))]}]}

    """
