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

    # Hard to do this per diagnostic, since some may have been both correct and incorrect
    "correct_results_total_perc": 0,
    "correct_results_copied_perc": 0,
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
        # "DA2001": {
        #     "perc_correct": 0,
        #     "correct": 0,
        #     "wrong": 0,
        #     "included_in_training": True
        # }
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

def recreate_diff(diff_string):
    # REMOVE SOURCE_LOCATION_START 3 SOURCE_LOCATION_END 4
    # ADD PREVIOUS_SOURCE_LOCATION 1 TARGET_LINES WHITESPACE
    # REPLACE SOURCE_LOCATION 4 TARGET_LINES WHITESPACE

    recreated_diff = {}
    token_list = diff_string.split()
    diff_type = token_list[0]
    if diff_type == "ADD":
        recreated_diff["PreviousSourceLocation"] = token_list[2]
        recreated_diff["TargetLines"] = recreate_code(" ".join(token_list[4:]))
    elif diff_type == "REMOVE":
        recreated_diff["SourceLocationStart"] = token_list[2]
        recreated_diff["SourceLocationEnd"] = token_list[4]
    else:
        recreated_diff["SourceLocation"] = []
        targetLines = []
        hit_target_line = False
        for token in token_list[2:]:
            if hit_target_line:
                targetLines.append(token)

            if token == "TARGET_LINES":
                hit_target_line = True
                continue
            else:
                recreated_diff["SourceLocation"].append(token)
        recreated_diff["TargetLines"] = recreate_code(" ".join(targetLines))

    return recreated_diff
    



def main():
    with open(metadata_test_file) as json_file:
        metadata_test = json.load(json_file)

    with open(metadata_train_file) as json_file:
        metadata_train = json.load(json_file)

    with open(src_test_file, 'r') as file:
        src_test_list = file.read().split("\n")
        if src_test_list[-1] == '':
            del src_test_list[-1]

    with open(tgt_test_file, 'r') as file:
        tgt_test_list = file.read().split("\n")
        if tgt_test_list[-1] == '':
            del tgt_test_list[-1]

    with open(inference_test_file, 'r') as file:
        inference_test_list = file.read().split("\n")
        if inference_test_list[-1] == "":
            del inference_test_list[-1]
    
    evaluation_dict["num_total_datapoints"] = len(inference_test_list)

    for index, tgt_test_line in enumerate(tgt_test_list):
        is_correct = tgt_test_line == inference_test_list[index]

        diagnostic_id = metadata_test["datapoints"][index]["DiagnosticID"] # ID, DiagnosticID
        included_in_training = diagnostic_id in metadata_train["diagnostics"]
        if diagnostic_id not in evaluation_dict["result_per_diagnostic"]:

            evaluation_dict["result_per_diagnostic"][diagnostic_id] = {
                "perc_correct": 0,  # Calculate later
                "correct": 1 if is_correct else 0,
                "wrong": 0 if is_correct else 1,
                "included_in_training": included_in_training
            }

        else:
            if is_correct:
                evaluation_dict["result_per_diagnostic"][diagnostic_id]["correct"] += 1
            else:
                evaluation_dict["result_per_diagnostic"][diagnostic_id]["wrong"] += 1

        # TODO: Do this properly
        if not included_in_training:
            if is_correct:
                evaluation_dict["correctly_extrapolated_examples"] = []
            else:
                evaluation_dict["incorrectly_extrapolated_examples"] = []

    total_total = 0
    copied_total = 0
    extrapolated_total = 0

    total_correct = 0
    copied_correct = 0
    extrapolated_correct = 0

    for value in evaluation_dict["result_per_diagnostic"].values():
        total_datapoints = value["correct"] + value["wrong"]
        value["perc_correct"] = value["correct"] / total_datapoints

        total_total += total_datapoints
        total_correct += value["correct"]

        if value["included_in_training"]:
            copied_correct += value["correct"]
            copied_total += total_datapoints
        else:
            extrapolated_correct += value["correct"]
            extrapolated_total += total_datapoints
    
    evaluation_dict["correct_results_total_perc"] = total_correct / total_datapoints
    evaluation_dict["correct_results_copied_perc"] = copied_correct / copied_total
    evaluation_dict["correct_results_extrapolated_perc"] = extrapolated_correct / extrapolated_total


    with open(inference_eval_file, 'w') as fout:
        json_str = json.dumps(evaluation_dict, indent=4)
        print(json_str, file=fout)


if __name__ == '__main__':
    main()
