# 关键词检索（Keyword Spotting、KWS）打分工具
用于评估关键词检索效果的工具，评估指标为 recall、precision 和 F1。

## 关键词检索任务概述
这里所述的关键词检索任务指的是从连续语音流中检索出指定关键词在语音中的时间位置。例如在时长为20s的语音中，检索出关键词 `北京` 在语音中的位置为：2.3s ~ 2.6s 和 11.2s ~ 11.55s。

## 打分策略
有两种打分策略，本质上都是相同的。第一种根据预测关键词的中间时间点是否落在参考答案的时间区间内来判断是否命中；第二种根据预测结果的中间时间点和参考答案的中间时间点的差值是否低于阈值来判断是否命中。

第一种：
```txt
ref:
                 1.2    1.6
        ----------|      |----------

hypo:  
        ------|        |------------
             1.0      1.5
```
hypo_middle = (1.0 + 1.5) / 2 = 1.25

ref_st = 1.2 < hypo_middle < 1.6 = ref_et

命中。

第二种：
```txt
ref:
                   1.4    2.0
        ------------|      |----------

hypo:  
        ------|      |------------
             1.0    1.5
```
hypo_middle = (1.0 + 1.5) / 2 = 1.25

ref_middle = (1.4 + 2.0) / 2 = 1.7

若阈值为 0.5，则命中；若阈值为 0.3，则未命中；


## 使用
### 构建答案
将测试语音中标注的关键词时间点信息整理成如下形式：
```txt
xxx_1.wav
keyword_1 start_time end_time score
keyword_2 start_time end_time score
yyy_2.wav
keyword_2 start_time end_time score
keyword_3 start_time end_time score
```

**说明：** 
- `keyword`、`start_time`、`end_time` 和 `score` 之间以单个空格分隔；
- `score`, 在答案文件中，`score` 的值不重要，但是必须存在，默认为 100.00 即可；
- `start_time`、`end_time` 的格式为 `hour:minute:second.millisecond`

**Example:**
```txt
common_voice_en_18944441.wav
North American 00:00:02.620 00:00:03.750 100.00
common_voice_en_21476612.wav
North American 00:00:03.370 00:00:04.140 100.00
common_voice_en_27187728.wav
Commissioner 00:00:06.350 00:00:07.080 100.00
common_voice_en_19769191.wav
Portland 00:00:03.380 00:00:03.910 100.00
```

### 整理检索结果
将检索的结果整理成如下形式，格式和[答案](#构建答案)一样；
```txt
common_voice_en_27055852.wav
Portland 00:00:4.568 00:00:5.227 -1.562
common_voice_en_36490282.wav
North American 00:00:5.298 00:00:6.128 -0.693
common_voice_en_27085098.wav
Portland 00:00:4.898 00:00:5.807 -1.562
```

### 打分
```sh
python SkwEvaluator.py -s search_Result.txt 
                               -r kws_ref.txt 
                               -f
                               -tt 1.0
                               -st 0.0
                               -m range
```

使用 `python SkwEvaluator.py --help` 查看更多参数说明。

