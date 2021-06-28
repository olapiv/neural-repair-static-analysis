# Experiment

## Possible Independent Variables

* Mixture of train, val & test dataset
  * Randomly mixed to measure copy learning
  * Selecting diagnostics exclusively for test-set to measure extrapolation learning
* Indexing variable names / identifiers
* Separating variable names / identifiers between camel cases
* Max number of source/target (input/output) tokens
* Randomly masking line number / diagnostic in input
* Number of tokens before & after required lines
  * Fixed number of tokens
  * Random number of tokens

## NN - How To

### Setup CUDA

```Command
SET PATH=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.2\bin;%PATH%
SET PATH=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.2\extras\CUPTI\lib64;%PATH%
SET PATH=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.2\include;%PATH%
SET PATH=C:\Users\vlohse\Desktop\cuDNN\bin;%PATH%
```

or

```Powershell
$PATH = [Environment]::GetEnvironmentVariable("PATH")
$new_path = "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.2\bin"
[Environment]::SetEnvironmentVariable("PATH", "$PATH;$new_path")

$new_path = "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.2\extras\CUPTI\lib64"
[Environment]::SetEnvironmentVariable("PATH", "$PATH;$new_path")

$new_path = "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.2\include"
[Environment]::SetEnvironmentVariable("PATH", "$PATH;$new_path")

$new_path = "C:\Users\vlohse\Desktop\cuDNN\bin"
[Environment]::SetEnvironmentVariable("PATH", "$PATH;$new_path")

```

### OpenNMT Commands

```Powershell

# Source and target vocabulary is highly related, so bundle it into one file:
onmt-build-vocab --tokenizer_config config/tokenizer.yml --size 50000 --save_vocab data/vocab.txt `
    data/src-train.txt `
    data/src-test.txt `
    data/src-val.txt `
    data/tgt-test.txt `
    data/tgt-train.txt `
    data/tgt-val.txt

onmt-main --model_type Transformer --config data.yml --auto_config train --with_eval

onmt-main --model_type Transformer --config data.yml --auto_config infer --features_file data/src-test.txt --predictions_file data/inference-test.txt
```
