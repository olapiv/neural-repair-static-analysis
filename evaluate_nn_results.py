import os
import json
import random
import math
import copy
import statistics
from enum import Enum
from collections import Counter


final_dataset_dir = "final_dataset"
metadata_test_file = f"{final_dataset_dir}/metadata-test.json"
metadata_train_file = f"{final_dataset_dir}/metadata-train.json"
src_test_file = f"{final_dataset_dir}/src-test.txt"
tgt_test_file = f"{final_dataset_dir}/tgt-test.txt"
inference_test_file = f"{final_dataset_dir}/inference-test.txt"
inference_eval_file = f"{final_dataset_dir}/inference-eval.json"

data_example = {
    "ID": "",
    "DiagnosticID": "",
    "FileContext": "",
    "ParsedDiffCorrect": {},
    "ParsedDiffInferred": {}
}

evaluation_dict = {
    "num_total_datapoints": 0,
    "num_extrapolated_datapoints": 0,

    "correct_results_total_perc": 0,
    "correct_results_extrapolated_perc": 0,

    # Take different DiagnosticIDs for examples here

    "highest_accuracy_examples": [
        # data_example
    ],

    "worst_accuracy_examples": [
        # data_example
    ],

    "correctly_extrapolated_examples": [
        # data_example
    ],

    "incorrectly_extrapolated_examples": [
        # data_example
    ],

    "result_per_diagnostic": {
        "DA2001": {
            "perc_correct": 0,
            "correct": 0,
            "wrong": 0,
            "included_in_training": True
        }
    }
}

# Clear old evaluation data
open(inference_eval_file, 'w').close()


def recreate_code(tokenized_code):
    initial_code = ""
    for token in tokenized_code.split():
        if token == "WHITESPACE":
            initial_code += " "
        elif token == "NEWLINE":
            initial_code += "\n"
        elif token == "TAB":
            initial_code += "\t"
        else:
            initial_code += token
    return initial_code


def main():
    with open(metadata_test_file) as json_file:
        metadata_test = json.load(json_file)

    with open(tgt_test_file, 'r') as file:
        tgt_test_string = file.read()

    with open(inference_test_file, 'r') as file:
        inference_test_string = file.read()


if __name__ == '__main__':
    main()
