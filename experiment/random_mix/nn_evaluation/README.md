# Results and Evaluation

## Experiment Setup

* NN model: Out-of-the-box OpenNMT Transformer with SelfAttentionDecoder
* See further NN parameters in [nn/data.yml](nn/data.yml)
* Hardware: Nvidia GeForce GTX 1080
* NN was evaluated on inferring/translating the test dataset
* Input: [src-test.txt](../src-test.txt), correct output: [tgt-test.txt](../tgt-test.txt), predicted output: [inference-test.txt](inference-test.txt)
* Evaluation was scripted in [evaluate_nn_results.py](/evaluate_nn_results.py)
* Evaluation results to be found in [inference-eval.json](inference-eval.json)

## Results after 5k steps

Convergence after around 3k steps (1h35min); Loss function:

![Loss Function](loss_function_20k_steps.png)

Measuring the impact of datapoints per diagnostic on its accuracy in the following figure.

![Impact data per Diagnostic on Accuracy](impact_data_on_accuracy.png)

Each datapoint represents a diagnostic. It is hard to decipher a correlation between number of data points a diagnostic requires in train to be successfully predicted in test.

Measuring the impact of number of tokens in target/source on success rate of predictions in test in the followng figure.

![Target Length vs Success Rate](success-rate-tgt-len.png)

![Source Length vs Success Rate](success-rate-src-len.png)