import os
import json
import random
import math
import copy
import statistics
from enum import Enum
from collections import Counter
import plotly.graph_objects as go


final_dataset_dir = "final_dataset"
metadata_test_file = f"{final_dataset_dir}/metadata-test.json"
metadata_train_file = f"{final_dataset_dir}/metadata-train.json"
src_test_file = f"{final_dataset_dir}/src-test.txt"
tgt_test_file = f"{final_dataset_dir}/tgt-test.txt"
inference_test_file = f"{final_dataset_dir}/inference-test.txt"
inference_eval_file = f"{final_dataset_dir}/inference-eval.json"

data_example = {
    "id": "",
    "diagnostic_id": "",
    "perc_correct": 0.0,
    "parsed_src": {
        "diagnostic_occurances": [
            # {
            #     "diagnostic_line": "",
            #     "diagnostic_message": "",
            # }
        ],
        "file_context": "",
    },
    "parsed_diff_correct": {},
    "parsed_diff_inferred": {},
}

evaluation_dict = {
    "num_total_datapoints": 0,
    "num_extrapolated_datapoints": 0,

    # Hard to do this per diagnostic, since some may have been both correct and incorrect
    "correct_results_total_perc": 0,
    "correct_results_copied_perc": 0,
    "correct_results_extrapolated_perc": 0,

    # Take different DiagnosticIDs for examples here

    # Fill with multiple "data_example":
    "highest_accuracy_copied_examples": [],
    "highest_accuracy_extrapolated_examples": [],
    "lowest_accuracy_copied_examples": [],
    "lowest_accuracy_extrapolated_examples": [],
    "ambiguous_accuracy_copied_examples": [],
    "ambiguous_accuracy_extrapolated_examples": [],

    "result_per_diagnostic": {
        # "DA2001": {
        #     "perc_correct": 0,
        #     "correct": 0,
        #     "wrong": 0,
        #     "num_datapoints_in_train": 0
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
    recreated_diff["diff_type"] = diff_type
    if diff_type == "ADD":
        recreated_diff["PreviousSourceLocation"] = token_list[2]
        code_string = recreate_code(" ".join(token_list[4:]))
        recreated_diff["TargetLines"] = code_string.rstrip('\n').split("\n")
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
            elif token == "TARGET_LINES":
                hit_target_line = True
                continue
            else:
                recreated_diff["SourceLocation"].append(token)
        code_string = recreate_code(" ".join(targetLines))
        recreated_diff["TargetLines"] = code_string.rstrip('\n').split("\n")

    return recreated_diff


def recreate_src(src_string):

    parsed_src = {
        "diagnostic_occurances": [
            # {
            #     "diagnostic_line": "",
            #     "diagnostic_message": "",
            # }
        ],
        "file_context": "",
    }

    (diagnostic_occurances_str, file_context) = src_string.split(" FILE_CONTENT ")
    parsed_src["file_context"] = recreate_code(
        file_context).rstrip('\n').split("\n")

    # LINE 2 MESSAGE unused WHITESPACE field WHITESPACE ' _array ' LINE 3 MESSAGE unused WHITESPACE field WHITESPACE ' _dummy '
    for diag_occ_str in diagnostic_occurances_str.split("LINE"):
        if diag_occ_str == "":
            continue
        diag_occ = {}
        (diag_line_str, diag_message_str) = diag_occ_str.split("MESSAGE")
        diag_occ["diagnostic_line"] = diag_line_str.strip()
        diag_occ["diagnostic_message"] = recreate_code(diag_message_str)
        parsed_src["diagnostic_occurances"].append(diag_occ)

    return parsed_src


def save_result_per_diagnostic(evaluation_dict, metadata_train, metadata_test, tgt_test_list, inference_test_list):

    for index, tgt_test_line in enumerate(tgt_test_list):
        is_correct = tgt_test_line == inference_test_list[index]

        # ID, DiagnosticID
        diagnostic_id = metadata_test["datapoints"][index]["DiagnosticID"]
        if diagnostic_id in metadata_train["diagnostics"]:
            num_datapoints_in_train = metadata_train["diagnostics"][diagnostic_id]
        else:
            num_datapoints_in_train = 0

        if diagnostic_id not in evaluation_dict["result_per_diagnostic"]:

            evaluation_dict["result_per_diagnostic"][diagnostic_id] = {
                "perc_correct": 0,  # Calculate later
                "correct": [index] if is_correct else [],
                "wrong": [] if is_correct else [index],
                "num_datapoints_in_train": num_datapoints_in_train,
            }

        else:
            if is_correct:
                evaluation_dict["result_per_diagnostic"][diagnostic_id]["correct"].append(
                    index)
            else:
                evaluation_dict["result_per_diagnostic"][diagnostic_id]["wrong"].append(
                    index)


def flatten_result_per_diagnostic(result_per_diagnostic_dict):
    flattened = []
    for key, value in result_per_diagnostic_dict.items():
        flattened.append({
            "diagnostic_id": key,
            "perc_correct": value["perc_correct"],
            "correct": value["correct"],
            "wrong": value["wrong"],
            "num_datapoints_in_train": value["num_datapoints_in_train"],
        })
    return flattened


def save_characteristic_examples(
    evaluation_dict,
    characteristic_examples_dict,
    src_test_list,
    tgt_test_list,
    inference_test_list,
    metadata_test
):

    for key, result_per_diagnostic_list in characteristic_examples_dict.items():
        num_examples = 0
        for diagnostic_result in result_per_diagnostic_list:
            if num_examples == 2:
                break
            num_examples += 1

            example_dict = copy.deepcopy(data_example)
            example_dict["diagnostic_id"] = diagnostic_result["diagnostic_id"]

            # Get a correct datapoint
            if key in ["highest_accuracy_copied", "highest_accuracy_extrapolated"]:
                if not diagnostic_result["correct"]:
                    continue

                # Get first datapoint of given diagnostic
                line_num = diagnostic_result["correct"][0]

                diff_tgt = tgt_test_list[line_num]

                example_dict["parsed_diff_correct"] = recreate_diff(diff_tgt)

            # Get an incorrect datapoint
            elif key in ["lowest_accuracy_copied", "lowest_accuracy_extrapolated"]:
                if not diagnostic_result["wrong"]:
                    continue

                # Get first datapoint of given diagnostic
                line_num = diagnostic_result["wrong"][0]

                # Show what went wrong
                diff_tgt = tgt_test_list[line_num]
                diff_inferred = inference_test_list[line_num]

                example_dict["parsed_diff_correct"] = recreate_diff(diff_tgt)
                example_dict["parsed_diff_inferred"] = recreate_diff(
                    diff_inferred)

            # TODO later: Get a correct & incorrect datapoint
            else:  # ambiguous_accuracy_copied & ambiguous_accuracy_extrapolated
                if not diagnostic_result["wrong"]:
                    continue

                # Get first datapoint of given diagnostic
                line_num = diagnostic_result["wrong"][0]

                # Show what went wrong
                diff_tgt = tgt_test_list[line_num]
                diff_inferred = inference_test_list[line_num]

                example_dict["ParsedDiffCorrect"] = recreate_diff(diff_tgt)
                example_dict["ParsedDiffInferred"] = recreate_diff(
                    diff_inferred)

            datapoint_id = metadata_test["datapoints"][line_num]["ID"]
            example_dict["id"] = datapoint_id

            example_dict["perc_correct"] = diagnostic_result["perc_correct"]

            src_str = src_test_list[line_num]
            example_dict["parsed_src"] = recreate_src(src_str)

            key_name = key + "_examples"
            if key_name not in evaluation_dict:
                evaluation_dict[key_name] = []
            evaluation_dict[key_name].append(example_dict)


def sort_for_characteristic_examples(evaluation_dict):

    result_per_diagnostic = flatten_result_per_diagnostic(
        evaluation_dict["result_per_diagnostic"])

    highest_accuracy_copied = [
        result for result in result_per_diagnostic if result["num_datapoints_in_train"] > 0]
    highest_accuracy_copied.sort(
        key=lambda x: x.get('perc_correct'), reverse=True)
    highest_accuracy_extrapolated = [
        result for result in result_per_diagnostic if result["num_datapoints_in_train"] == 0]
    highest_accuracy_extrapolated.sort(
        key=lambda x: x.get('perc_correct'), reverse=True)

    lowest_accuracy_copied = [
        result for result in result_per_diagnostic if result["num_datapoints_in_train"] > 0]
    lowest_accuracy_copied.sort(key=lambda x: x.get('perc_correct'))
    lowest_accuracy_extrapolated = [
        result for result in result_per_diagnostic if result["num_datapoints_in_train"] == 0]
    lowest_accuracy_extrapolated.sort(key=lambda x: x.get('perc_correct'))

    ambiguous_accuracy_copied = [
        result for result in result_per_diagnostic if result["num_datapoints_in_train"] > 0]
    ambiguous_accuracy_copied.sort(
        key=lambda x: abs(x.get('perc_correct') - 0.5))
    ambiguous_accuracy_extrapolated = [
        result for result in result_per_diagnostic if result["num_datapoints_in_train"] == 0]
    ambiguous_accuracy_extrapolated.sort(
        key=lambda x: abs(x.get('perc_correct') - 0.5))

    return {
        "highest_accuracy_copied": highest_accuracy_copied,
        "highest_accuracy_extrapolated": highest_accuracy_extrapolated,
        "lowest_accuracy_copied": lowest_accuracy_copied,
        "lowest_accuracy_extrapolated": lowest_accuracy_extrapolated,
        "ambiguous_accuracy_copied": ambiguous_accuracy_copied,
        "ambiguous_accuracy_extrapolated": ambiguous_accuracy_extrapolated
    }


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

    save_result_per_diagnostic(
        evaluation_dict, metadata_train, metadata_test, tgt_test_list, inference_test_list)

    characteristic_examples_dict = sort_for_characteristic_examples(
        evaluation_dict)

    save_characteristic_examples(evaluation_dict, characteristic_examples_dict,
                                 src_test_list, tgt_test_list, inference_test_list, metadata_test)

    total_total = 0
    copied_total = 0
    extrapolated_total = 0

    total_correct = 0
    copied_correct = 0
    extrapolated_correct = 0

    for value in evaluation_dict["result_per_diagnostic"].values():
        num_correct = len(value["correct"])
        num_wrong = len(value["wrong"])
        total_datapoints = num_correct + num_wrong
        value["perc_correct"] = num_correct / total_datapoints

        total_total += total_datapoints
        total_correct += num_correct

        if value["num_datapoints_in_train"] > 0:
            copied_correct += num_correct
            copied_total += total_datapoints
        else:
            extrapolated_correct += num_correct
            extrapolated_total += total_datapoints

    evaluation_dict["num_extrapolated_datapoints"] = extrapolated_total

    evaluation_dict["correct_results_total_perc"] = total_correct / \
        total_total
    evaluation_dict["correct_results_copied_perc"] = copied_correct / copied_total
    evaluation_dict["correct_results_extrapolated_perc"] = extrapolated_correct / \
        extrapolated_total

    datapoints_graph = flatten_result_per_diagnostic(
        evaluation_dict["result_per_diagnostic"])

    x = [datapoint["num_datapoints_in_train"]
         for datapoint in datapoints_graph]
    y = [datapoint["perc_correct"] for datapoint in datapoints_graph]
    text = [datapoint["diagnostic_id"] for datapoint in datapoints_graph]
    fig = go.Figure(data=go.Scatter(x=x,
                                    y=y,
                                    mode='markers',
                                    text=text))
    fig.update_layout(
        title='Training Points Necessary for Good Results in Test')
    fig.update_xaxes(title_text='num_datapoints_in_train')
    fig.update_yaxes(title_text='perc_correct_in_test')
    fig.show()

    with open(inference_eval_file, 'w') as fout:
        json_str = json.dumps(evaluation_dict, indent=4)
        print(json_str, file=fout)


if __name__ == '__main__':
    main()
