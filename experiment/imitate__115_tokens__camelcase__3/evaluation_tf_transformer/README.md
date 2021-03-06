# Results and Evaluation

## Experiment Setup

* Hardware: Nvidia GeForce GTX 1080
* NN was evaluated on inferring/translating the test dataset
* Input: [src-test.txt](../src-test.txt), correct output: [tgt-test.txt](../tgt-test.txt), predicted output: [inference-test.txt](inference-test.txt)
* Evaluation was scripted in [evaluate_nn_results.py](/evaluate_nn_results.py)
* Evaluation results to be found in [inference-eval.json](inference-eval.json)
* Humanly readable output examples are saved in [characteristic_examples](characteristic_examples) and in [per_diagnostic_examples](per_diagnostic_examples)
* Pearson Number calculated with [scipy.stats.pearsonr](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.pearsonr.html)

## Results after 10k steps

Best evaluation results after 10k steps (6h50min); Loss function:

![Loss Function](imitate_loss_function.svg)

All data in [Tensorflow Board](https://tensorboard.dev/experiment/ye3BDGpKS6GKz4LnoLSDaw/#scalars).

### Influence of Datapoints per Diagnostic on Diagnostics' Accuracy

![Impact data per Diagnostic on Accuracy](imitate_impact_data_on_accuracy.svg)

pearsonr: (0.0634902867694032, 0.25447036235119896)

Each datapoint represents a diagnostic. It is hard to decipher a correlation between number of data points a diagnostic requires in train to be successfully predicted in test.

### Influence of Number of **Formatting** Tokens in Source on Success Rate of Predictions

![Source Formatting Length vs Success Rate](imitate_success_rate_formatting_len_src.svg)

The influence of total tokens in source is omitted, since the number of file context tokens for input is held constant.

### Influence of Number of Tokens in Target on Success Rate of Predictions

![Target Length vs Success Rate](imitate_success_rate_tgt_len.svg)
