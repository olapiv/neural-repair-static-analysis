# Final Dataset & Corresponding Results

## Dataset

* Dataset & metadata files generated with [finalize_tokenized_dataset.py](/finalize_tokenized_dataset.py)
* Measuring **Copy Behaviour**: Distribution of data points across training-, validation- and test-set with overlapping diagnostics
  * train_perc = 60% of datapoints
  * val_perc = 20% of datapoints
  * test_perc = 20% of datapoints
* Variable names / identifiers are *not* indexed
* Train, val & test dataset are *randomly* chosen from aggregate dataset
* See metadata files for further information on data
* Max number of FILE_CONTENT tokens in input (required lines + context): 100
