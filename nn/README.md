# How To

```bash

# Source and target vocabulary is highly related, so bundle it into one file:
onmt-build-vocab --tokenizer_config config/tokenizer.yml --size 50000 --save_vocab data/vocab.txt \
    data/src-train.txt \
    data/src-test.txt \
    data/src-val.txt \
    data/target-test.txt \
    data/target-train.txt \
    data/target-val.txt

onmt-main --model_type Transformer --config data.yml --auto_config train --with_eval

onmt-main --model_type Transformer --config data.yml --auto_config infer --features_file data/src-test.txt

onmt-main --model_type Transformer --config data.yml --auto_config infer --features_file data/src-test.txt --predictions_file data/inference-test.txt
```
