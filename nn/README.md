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

```
