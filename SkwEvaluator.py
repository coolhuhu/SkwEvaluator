import os
import shutil
import argparse
from typing import List, Dict


def time_str_format(time_str):
    """
    00:00:11.640 -> 11.64
    """
    hour, minute, second = time_str.split(':')
    hour, minute, second = float(hour), float(minute), float(second)
    time_float = hour * 3600 + minute * 60 + second
    return time_float


def parse_file(file: str, threshold: float = 0.0):
    with open(file) as f:
        lines = [line.strip() for line in f]
    
    file2ref = {}
    keyword_num = 0
    per_keyword_num = {}
    try:
        filename = None
        for line in lines:
            line = line.strip()
            # NOTE By default, they are separated by a single space.
            seqs = line.split(' ')
            seqs = [s for s in seqs if len(s) > 0]
        
            if len(seqs) <= 1:
                filename = line
                if filename not in file2ref:
                    file2ref[filename] = {}
                score = None
                end_time = None
                start_time = None
                keyword = None
            else:
                score = float(seqs[-1])
                # 忽略掉小于阈值的关键词
                if score < threshold:
                    continue
                
                end_time = round(time_str_format(seqs[-2]), 2)
                start_time = round(time_str_format(seqs[-3]), 2)
                keyword = seqs[:-3]
                keyword = ' '.join(keyword)
                keyword = keyword.strip()

                keyword_num += 1
                if keyword not in per_keyword_num:
                    per_keyword_num[keyword] = 0
                per_keyword_num[keyword] += 1
            
            if keyword:
                if keyword not in file2ref[filename]:
                    file2ref[filename][keyword] = []
                file2ref[filename][keyword].append([start_time, end_time, score])

    except Exception as e:
        print(e)
        print("The result file format is incorrect.")

    return file2ref, keyword_num, per_keyword_num
    

def difference_match(result_start_time, result_end_time,
                    ref_start_time, ref_end_time, threshold=2):
    result_middle_time = (result_start_time + result_end_time) / 2
    ref_middle_time = (ref_start_time + ref_end_time) / 2
    if abs(result_middle_time - ref_middle_time) <= threshold:
        return True
    return False


def range_match(result_start_time, result_end_time,
                ref_start_time, ref_end_time, threshold=2):
    res_middle_time = (result_start_time + result_end_time) / 2
    if res_middle_time >= ref_start_time and res_middle_time <= ref_end_time:
        return True
    return False


class SkwEvaluator():
    def __init__(self):
        self.recall_true = 0
        self.recall_false = 0
        self.recall_miss = 0
        self.result_keyword_num = 0
        self.reference_keyword_num = 0
        self.result_per_keyword_num = {}
        self.reference_per_keyword_num = {}
        csv_header = ["file", "keyword", \
                      "ref_start_time", "ref_end_time", "ref_score", \
                      "sys_start_time", "sys_end_time", "sys_score"]
        self.recall_true_keywords = [csv_header]
        self.recall_false_keywords = [csv_header]
        self.recall_miss_keywords = [csv_header]
        self.keyword_match_method = difference_match
        
    def set_keyword_match_method(self, method_name):
        if method_name == "range":
            self.keyword_match_method = range_match
        elif method_name == "difference":
            self.keyword_match_method = difference_match
        else:
            raise AttributeError(f"not support {method_name}")
          
    def parse_result_file(self, file: str, threshold: float = 0.0):
        """
        Parsing result file.
        """
        file2ref, self.result_keyword_num, self.result_per_keyword_num = parse_file(file, threshold)
        return file2ref

    def parse_ref_file(self, file: str):
        """
        Parsing the reference file.
        """
        file2ref, self.reference_keyword_num, self.reference_per_keyword_num = parse_file(file)
        return file2ref
    
    def keyword_match(self, filename, keyword, result_items: List, reference_items: List, threshold):
        """
        检索结果中和答案中，同一条语音下都存在同一个关键词；
        根据关键词的时间点来匹配是否召回命中。
        """
        r_t, r_f = 0, 0
        for res_item in result_items:
            res_start_time, res_end_time, _ = res_item
            flag = False
            for ref_item in reference_items:
                ref_start_time, ref_end_time, _ = ref_item
                if self.keyword_match_method(res_start_time, res_end_time, 
                                             ref_start_time, ref_end_time, 
                                             threshold=threshold):
                    # NOTE 一般来说，有两种匹配关键词的计算方式
                    # 第一种是，根据中间时间点的差值来判断是否召回命中，
                    # 若中间时间点的差值小于阈值，则召回命中，反之召回错误；
                    # 另一种是，检索出的关键词的中间时间点落在参考答案的时间范围内，
                    # 算一个召回命中，反之召回错误；
                    # 这里采用的是第一种计算方式
                    self.recall_true += 1
                    self.recall_true_keywords.append([filename, keyword, *ref_item, *res_item])
                    flag = True
                    
                    # NOTE: 可能存在下面这种情况
                    # result_items = [[1.2, 1.75], [1.9, 2.65]]
                    # reference_items = [[1.35, 1.95], [2.15, 3.0]]
                    break
            if not flag:
                self.recall_false += 1
                self.recall_false_keywords.append([filename, keyword, *ref_item, *res_item])
    
    def cal(self, result: Dict, reference: Dict, threshold=2):
        for file, result_keywords in result.items():
            # 从检索结果去匹配参考答案，统计 recall_true 和 recall_false
            if file not in reference:
                # 检索出的答案，不在答案中，说明该语音中检索出来的关键词全是 recall_false
                for keyword, result_items in result_keywords.items():
                    self.recall_false += len(result_items)
                    for item in result_items:
                        self.recall_false_keywords.append([file, keyword, "", "", "", *item]) 
            else:
                # 该条语音在答案中存在
                # 该情况下，有 recall_true 和 recall_false 两种情况
                reference_keywords = reference[file]
                for keyword, result_items in result_keywords.items():
                    if keyword in reference_keywords:
                        # 语音中检索出了关键词，且参考答案中该条语音也存在该关键词
                        # 根据时间来判断是否召回命中
                        reference_items = reference_keywords[keyword]
                        self.keyword_match(file, keyword, result_items, reference_items, threshold)
                    else:
                        # 语音中检索出了关键词，但是参考答案中不存在该关键词，
                        # 因此检索出的该关键词是 recall_false
                        self.recall_false += len(result_items)
                        for item in result_items:
                            self.recall_false_keywords.append([file, keyword, "", "", "", *item])
                        
        for file, reference_keywords in reference.items():
            # 从参考答案中去匹配检索结果，统计 recall_miss
            if file not in result:
                # 参考答案中标出了该条语音下的关键词时间点，但是检索答案中不存在该语音
                # 说明参考答案中该条语音下标出的关键词全部为 recall_miss
                for keyword, reference_items in reference_keywords.items():
                    self.recall_miss += len(reference_items)
                    for item in reference_items:
                        self.recall_miss_keywords.append([file, keyword, *item, "", "", ""])
            else:
                # 参考答案中标出了该关键词，但是检索结果中不存在
                # 说明该关键词为 recall_miss
                result_keywords = result[file]
                for keyword, reference_items in reference_keywords.items():
                    if keyword not in result_keywords:
                        self.recall_miss += len(reference_items)
                        for item in reference_items:
                            self.recall_miss_keywords.append([file, keyword, *item, "", "", ""])

    def get_f1(self):
        p = self.get_precision()
        r = self.get_recall()
        if abs(p + r) <= 0.001:
            f1 = 0
        else:  
            f1 = 2 * p * r / (p + r)
        return round(f1, 4)
    
    def get_recall(self):
        return round(self.recall_true / self.reference_keyword_num, 4)
    
    def get_precision(self):
        return round(self.recall_true / self.result_keyword_num, 4)
    
    def write_result(self):
        output_dir = "./result"
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)
        
        recall_true_file = os.path.join(output_dir, "recall_true.txt")
        recall_false_file = os.path.join(output_dir, "recall_false.txt")
        recall_miss_file = os.path.join(output_dir, "recall_miss.txt")
        
        def write_file(lines, file):
            with open(file, "wt", encoding="utf-8") as wf:
                for line in lines:
                    line = [str(l) for l in line]
                    wf.write(f"{','.join(line)}\n")
        
        write_file(self.recall_true_keywords, recall_true_file)
        write_file(self.recall_false_keywords, recall_false_file)
        write_file(self.recall_miss_keywords, recall_miss_file)
        
        score_file = os.path.join(output_dir, "score.txt")
        with open(score_file, "wt", encoding="utf-8") as wf:
            wf.write(f"检索结果中关键词数量: {self.result_keyword_num}\n")
            wf.write(f"参考答案中关键词数量: {self.reference_keyword_num}\n")
            wf.write(f"命中正确的关键词数量: {self.recall_true}\n")
            wf.write(f"命中错误的关键词数量: {self.recall_false}\n")
            wf.write(f"没有命中的关键词数量: {self.recall_miss}\n")
            wf.write(f"recall: {self.get_recall()}\n")
            wf.write(f"precision: {self.get_precision()}\n")
            wf.write(f"F1: {self.get_f1()}\n")
            

def test_keyword_match():
    evaluator = SkwEvaluator()
    filename = "1.wav"
    keyword = "hello"
    result_items = [
        [1.23, 1.89, 0],
        [5.34, 6.12, 0]
    ]
    reference_items = [
        [1.47, 2.15, 0],
        [6.0, 6.88, 0]
    ]
    evaluator.keyword_match(filename, keyword, result_items, reference_items, 1)
    print("recall false:")
    print(evaluator.recall_false)
    print(evaluator.recall_false_keywords)
    print("recall true:")
    print(evaluator.recall_true)
    print(evaluator.recall_true_keywords)
    

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--search_result", type=str, required=True,
                        help="search result file")
    parser.add_argument("-r", "--reference", type=str, required=True,
                        help="reference file")
    parser.add_argument("-tt", "--time_threshold", type=float, default=1,
                        help="keyword match threshold")
    parser.add_argument("-st", "--score_threshold", type=float, default=0,
                        help="keyword score threshold, if less score_threadhold, \
                              the keyword is not considered to be a hit.")
    parser.add_argument("-f", "--isWriteResultToFile", action="store_true",
                        help="write result to file.")
    parser.add_argument("-m", "--metric_method", type=str, default="difference",
                        choices=["range", "difference"],
                        help="If is 'difference', determine whether it hits based on \
                              the difference between the intermediate time points. \
                              If it's 'range', determine whether it hits based on \
                              whether the midpoint of the retrieval result time falls \
                              between the reference answer time points.")
    return parser.parse_args()


def main(args):
    evaluator = SkwEvaluator()
    evaluator.set_keyword_match_method(args.metric_method)
    result_file2ref = evaluator.parse_result_file(args.search_result, args.score_threshold)
    reference_file2ref = evaluator.parse_ref_file(args.reference)
    
    print(f"检索结果中关键词数量: {evaluator.result_keyword_num}")
    print(f"参考答案中关键词数量: {evaluator.reference_keyword_num}")
    
    evaluator.cal(result_file2ref, reference_file2ref, args.time_threshold)
    
    print(f"命中正确的关键词数量: {evaluator.recall_true}")
    print(f"命中错误的关键词数量: {evaluator.recall_false}")
    print(f"没有命中的关键词数量: {evaluator.recall_miss}")
    
    print(f"recall: {evaluator.get_recall()}")
    print(f"precision: {evaluator.get_precision()}")
    print(f"F1: {evaluator.get_f1()}")
    
    if args.isWriteResultToFile:
        evaluator.write_result()
    
    
if __name__ == "__main__":
    """
    Usage:
        python skw_evaluate.py -s search_Result.txt 
                               -r kws_ref.txt 
                               -f
                               -tt 1.0
                               -st 0.0
                               -m range
    """
    args = parse_args()
    main(args)