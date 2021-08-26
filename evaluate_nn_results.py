import os
import json
import re
import random
import math
import copy
import difflib
import statistics
from enum import Enum
from pathlib import Path
import pandas as pd
from collections import Counter
import plotly.graph_objects as go
import plotly.express as px
from scipy.stats import pearsonr


class Experiment(Enum):
    imitate = "imitate"
    extrap = "extrapolate"


class Tokenization(Enum):
    standard = "100_tokens__standard"
    camelcase = "115_tokens__camelcase"


class NNFramework(Enum):
    pytorch = "py"
    tensorflow = "tf"


class NNModel(Enum):
    transformer = "transformer"
    transformer_copy_mechanism = "transformer_copy_mech"  # Never used


experiment = Experiment.imitate
tokenization = Tokenization.standard
dataset_version = "3"
nn_framework = NNFramework.tensorflow
nn_model = NNModel.transformer

data_config_str = f"{experiment.value}__{tokenization.value}__{dataset_version}"
final_dataset_dir = f"experiment/{data_config_str}"

nn_config_str = f"{nn_framework.value}_{nn_model.value}"
eval_dir = f"{final_dataset_dir}/evaluation_{nn_config_str}"

# OUTPUT DIRS:
characteristic_examples_dir = f"{eval_dir}/characteristic_examples"
examples_per_diagnostic_dir = f"{eval_dir}/per_diagnostic_examples"
Path(characteristic_examples_dir).mkdir(parents=True, exist_ok=True)
Path(examples_per_diagnostic_dir).mkdir(parents=True, exist_ok=True)

# INPUT DIRS:
metadata_test_file = f"{final_dataset_dir}/metadata-test.json"
metadata_train_file = f"{final_dataset_dir}/metadata-train.json"
src_test_file = f"{final_dataset_dir}/src-test.txt"
tgt_test_file = f"{final_dataset_dir}/tgt-test.txt"
inference_test_file = f"{eval_dir}/inference-test.txt"
inference_eval_file = f"{eval_dir}/inference-eval.json"
# Only available for Tensorflow
experiment_csv_file = f"{eval_dir}/experiment.csv"

FORMATTING_TOKENS = ["WHITESPACE", "NEWLINE", "TAB"]

evaluation_dict = {
    "num_total_datapoints": 0,
    "num_extrapolated_datapoints": 0,

    "num_diagnostics_total": 0,
    "num_diagnostics_copied": 0,
    "num_diagnostics_extrapolated": 0,

    # Hard to do this per diagnostic, since some may have been both correct and incorrect
    "correct_results_total_perc": None,
    "correct_results_copied_perc": None,
    "correct_results_extrapolated_perc": None,

    # Give all diagnostics same weight, even if they have unequal numbers of data points
    "avg_success_per_diagnostic_total": None,
    "avg_success_per_diagnostic_copied": None,
    "avg_success_per_diagnostic_extrapolated": None,

    "avg_src_len_correct_result": None,
    "avg_src_len_incorrect_result": None,

    "avg_tgt_len_correct_result": None,
    "avg_tgt_len_incorrect_result": None,

    "avg_success_perc_per_src_len": {
        # 23: 0.7
    },
    "avg_success_perc_per_tgt_len": {
        # 23: 0.7
    },

    "avg_success_perc_per_src_formatting_token": {
        # 23: 0.7
    },
    "avg_success_perc_per_tgt_formatting_token": {
        # 23: 0.7
    },

    "result_per_diagnostic": {
        # "DA2001": {
        #     "perc_correct_in_test": 0,
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
    # REMOVE SOURCE_LOCATION_START 9 SOURCE_LOCATION_END 11
    # ADD PREVIOUS_SOURCE_LOCATION 1 TARGET_LINES WHITESPACE
    # REPLACE SOURCE_LOCATION 4 5 TARGET_LINES WHITESPACE

    recreated_diff = {}
    if not diff_string:
        recreated_diff["diff_type"] = "ADD"
        recreated_diff["previous_source_location"] = 0
        recreated_diff["target_lines"] = []
        return recreated_diff

    token_list = diff_string.split()
    diff_type = token_list[0]
    recreated_diff["diff_type"] = diff_type
    if diff_type == "ADD":
        recreated_diff["previous_source_location"] = token_list[2]
        code_string = recreate_code(" ".join(token_list[4:]))
        recreated_diff["target_lines"] = code_string.rstrip('\n').split("\n")
    elif diff_type == "REMOVE":
        recreated_diff["source_location_start"] = token_list[2]
        recreated_diff["source_location_end"] = token_list[4]
    else:
        recreated_diff["source_location"] = []
        targetLines = []
        hit_target_line = False
        for token in token_list[2:]:
            if hit_target_line:
                targetLines.append(token)
            elif token == "TARGET_LINES":
                hit_target_line = True
                continue
            else:
                recreated_diff["source_location"].append(token)
        code_string = recreate_code(" ".join(targetLines))
        recreated_diff["target_lines"] = code_string.rstrip('\n').split("\n")

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
    # for diag_occ_str in diagnostic_occurances_str.split("LINE"):  # Screw up with NEWLINE
    for diag_occ_str in re.findall(r'LINE\s\d+\sMESSAGE(?:(?!LINE\s\d+\sMESSAGE).)*', diagnostic_occurances_str):
        if diag_occ_str == "":
            continue
        diag_occ_str = diag_occ_str.lstrip("LINE ")
        diag_occ = {}
        (diag_line_str, diag_message_str) = diag_occ_str.split("MESSAGE")
        diag_occ["diagnostic_line"] = diag_line_str.strip()
        diag_occ["diagnostic_message"] = recreate_code(diag_message_str)
        parsed_src["diagnostic_occurances"].append(diag_occ)

    return parsed_src


def create_diff_with_diags(src_dict, tgt_dict):

    original_file = src_dict["file_context"][:]
    changed_file = src_dict["file_context"][:]

    diff_type = tgt_dict["diff_type"]
    try:
        if diff_type == "ADD":
            prev_src_loc = int(tgt_dict["previous_source_location"])
            changed_file[prev_src_loc:prev_src_loc] = tgt_dict["target_lines"]

        elif diff_type == "REMOVE":
            src_start = int(tgt_dict["source_location_start"])
            src_end = int(tgt_dict["source_location_end"])
            del changed_file[src_start:src_end + 1]

        elif diff_type == "REPLACE":
            src_start = int(tgt_dict["source_location"][0])
            src_end = int(tgt_dict["source_location"][-1])
            del changed_file[src_start:src_end + 1]
            changed_file[src_start:src_start] = tgt_dict["target_lines"]

        else:  # Nothing useful predicted
            return ""
    except ValueError as e:
        # In case weird things have been outputted
        # invalid literal for int() with base 10: '('
        print(e)
        return ""

    # ['  Lalalalala', '  lalala', '- dia', '+ dida', '?   +\n']
    diff_list = list(difflib.Differ().compare(original_file, changed_file))
    diff_list = [x for x in diff_list if not x.startswith("?")]

    # Inserting diagnostic message
    diff_list_with_diagnostics = diff_list[:]
    inserted_diags = 0
    for diagnostic in src_dict["diagnostic_occurances"]:

        line_index_original = 0
        for line_index_diff, diff_line in enumerate(diff_list):
            if diff_line.startswith("+"):
                continue
            if line_index_original == int(diagnostic['diagnostic_line']):
                diag_message = f"<<<< DIAGNOSTIC: {diagnostic['diagnostic_message']} >>>>"
                diff_list_with_diagnostics.insert(
                    line_index_diff + inserted_diags, diag_message)
                inserted_diags += 1

            line_index_original += 1

    return '\n'.join(diff_list_with_diagnostics)


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
                # "perc_correct_in_test": 0,  # Calculate later
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


def save_diagnostic_avg_results(evaluation_dict):

    total_diagnostics = evaluation_dict["result_per_diagnostic"]
    copied_diagnostics = {diagnostic_id: result for diagnostic_id,
                          result in total_diagnostics.items() if result["num_datapoints_in_train"] > 0}
    extrapolated_diagnostics = {diagnostic_id: result for diagnostic_id,
                                result in total_diagnostics.items() if result["num_datapoints_in_train"] == 0}

    percentage_added_total = sum([v["perc_correct_in_test"]
                                 for v in total_diagnostics.values()])
    percentage_added_copied = sum([v["perc_correct_in_test"]
                                  for v in copied_diagnostics.values()])
    percentage_added_extrapolated = sum(
        [v["perc_correct_in_test"] for v in extrapolated_diagnostics.values()])

    num_diagnostics_total = len(total_diagnostics.keys())
    num_diagnostics_copied = len(copied_diagnostics.keys())
    num_diagnostics_extrapolated = len(extrapolated_diagnostics.keys())

    evaluation_dict["num_diagnostics_total"] = num_diagnostics_total
    evaluation_dict["num_diagnostics_copied"] = num_diagnostics_copied
    evaluation_dict["num_diagnostics_extrapolated"] = num_diagnostics_extrapolated

    if num_diagnostics_total != 0:
        evaluation_dict["avg_success_per_diagnostic_total"] = percentage_added_total / \
            num_diagnostics_total

    if num_diagnostics_copied != 0:
        evaluation_dict["avg_success_per_diagnostic_copied"] = percentage_added_copied / \
            num_diagnostics_copied

    if num_diagnostics_extrapolated != 0:
        evaluation_dict["avg_success_per_diagnostic_extrapolated"] = percentage_added_extrapolated / \
            num_diagnostics_extrapolated


def save_num_tokens_vs_success_perc(evaluation_dict, metadata_train, metadata_test, src_test_list, tgt_test_list, inference_test_list):

    total_src_tokens_incorrect = 0
    total_tgt_tokens_incorrect = 0

    total_src_tokens_correct = 0
    total_tgt_tokens_correct = 0

    result_per_src_len = {}
    result_per_tgt_len = {}

    num_correct_datapoints = 0
    for index, tgt_test_line in enumerate(tgt_test_list):
        is_correct = tgt_test_line == inference_test_list[index]

        src_test_line = src_test_list[index]

        src_test_line = src_test_line.rstrip('\n').split(" ")
        tgt_test_line = tgt_test_line.rstrip('\n').split(" ")

        src_len = len(src_test_line)
        tgt_len = len(tgt_test_line)
        if is_correct:
            num_correct_datapoints += 1
            total_src_tokens_correct += src_len
            total_tgt_tokens_correct += tgt_len
        else:
            total_src_tokens_incorrect += src_len
            total_tgt_tokens_incorrect += tgt_len

        if src_len not in result_per_src_len:
            result_per_src_len[src_len] = {}
            result_per_src_len[src_len]["correct"] = 0
            result_per_src_len[src_len]["wrong"] = 0
        if tgt_len not in result_per_tgt_len:
            result_per_tgt_len[tgt_len] = {}
            result_per_tgt_len[tgt_len]["correct"] = 0
            result_per_tgt_len[tgt_len]["wrong"] = 0

        if is_correct:
            result_per_src_len[src_len]["correct"] += 1
            result_per_tgt_len[tgt_len]["correct"] += 1
        else:
            result_per_src_len[src_len]["wrong"] += 1
            result_per_tgt_len[tgt_len]["wrong"] += 1

    num_datapoints = len(src_test_list)

    if num_correct_datapoints != 0:
        evaluation_dict["avg_src_len_correct_result"] = total_src_tokens_correct / \
            num_correct_datapoints
        evaluation_dict["avg_tgt_len_correct_result"] = total_tgt_tokens_correct / \
            num_correct_datapoints

    num_incorrect_datapoints = num_datapoints - num_correct_datapoints
    if num_incorrect_datapoints != 0:
        evaluation_dict["avg_src_len_incorrect_result"] = total_src_tokens_incorrect / \
            num_incorrect_datapoints
        evaluation_dict["avg_tgt_len_incorrect_result"] = total_tgt_tokens_incorrect / \
            num_incorrect_datapoints

    success_perc_per_src_len = {}
    for src_len, value in result_per_src_len.items():
        success_perc_per_src_len[src_len] = value["correct"] / \
            (value["correct"] + value["wrong"])

    success_perc_per_tgt_len = {}
    for tgt_len, value in result_per_tgt_len.items():
        success_perc_per_tgt_len[tgt_len] = value["correct"] / \
            (value["correct"] + value["wrong"])

    evaluation_dict["avg_success_perc_per_src_len"] = success_perc_per_src_len
    evaluation_dict["avg_success_perc_per_tgt_len"] = success_perc_per_tgt_len


def save_num_formatting_tokens_vs_success_perc(evaluation_dict, src_test_list, tgt_test_list, inference_test_list):

    result_per_src_num_format_tokens = {}
    result_per_tgt_num_format_tokens = {}

    for index, tgt_test_line in enumerate(tgt_test_list):
        is_correct = tgt_test_line == inference_test_list[index]

        src_test_line = src_test_list[index]

        src_test_line = src_test_line.rstrip('\n').split(" ")
        tgt_test_line = tgt_test_line.rstrip('\n').split(" ")

        src_num_format_token = len(
            [token for token in src_test_line if token in FORMATTING_TOKENS])
        tgt_num_format_token = len(
            [token for token in tgt_test_line if token in FORMATTING_TOKENS])

        if src_num_format_token not in result_per_src_num_format_tokens:
            result_per_src_num_format_tokens[src_num_format_token] = {}
            result_per_src_num_format_tokens[src_num_format_token]["correct"] = 0
            result_per_src_num_format_tokens[src_num_format_token]["wrong"] = 0
        if tgt_num_format_token not in result_per_tgt_num_format_tokens:
            result_per_tgt_num_format_tokens[tgt_num_format_token] = {}
            result_per_tgt_num_format_tokens[tgt_num_format_token]["correct"] = 0
            result_per_tgt_num_format_tokens[tgt_num_format_token]["wrong"] = 0

        if is_correct:
            result_per_src_num_format_tokens[src_num_format_token]["correct"] += 1
            result_per_tgt_num_format_tokens[tgt_num_format_token]["correct"] += 1
        else:
            result_per_src_num_format_tokens[src_num_format_token]["wrong"] += 1
            result_per_tgt_num_format_tokens[tgt_num_format_token]["wrong"] += 1

    success_perc_per_src_format_token = {}
    for src_len, value in result_per_src_num_format_tokens.items():
        success_perc_per_src_format_token[src_len] = value["correct"] / \
            (value["correct"] + value["wrong"])

    success_perc_per_tgt_format_token = {}
    for tgt_len, value in result_per_tgt_num_format_tokens.items():
        success_perc_per_tgt_format_token[tgt_len] = value["correct"] / \
            (value["correct"] + value["wrong"])

    evaluation_dict["avg_success_perc_per_src_formatting_token"] = success_perc_per_src_format_token
    evaluation_dict["avg_success_perc_per_tgt_formatting_token"] = success_perc_per_tgt_format_token


def flatten_result_per_diagnostic(result_per_diagnostic_dict):
    flattened = []
    for key, value in result_per_diagnostic_dict.items():
        flattened.append({
            "diagnostic_id": key,
            "perc_correct_in_test": value["perc_correct_in_test"],
            "correct": value["correct"],
            "wrong": value["wrong"],
            "num_datapoints_in_train": value["num_datapoints_in_train"],
        })
    return flattened


def generate_diff(
    diagnostic_result,
    src_test_list,
    tgt_test_list,
    inference_test_list,
    metadata_test,
    getCorrectExample=True
):

    # diagnostic_result:
    # {
    #     'diagnostic_id': 'CS0002',
    #     'perc_correct_in_test': 0.9473684210526315,
    #     'correct': [31, 113, 133, 233, 290, 328, 341, 432, 527, 580, 624, 1410, 1415, 1455, 1494, 1541, 1567, 1577],
    #     'wrong': [1188],
    #     'num_datapoints_in_train': 0
    # }

    if getCorrectExample:
        if not diagnostic_result["correct"]:
            return None, None

        # Get first datapoint of given diagnostic
        line_num = diagnostic_result["correct"][0]
        # print("line_num: ", line_num)

        diff_tgt = tgt_test_list[line_num]

        parsed_diff_correct = recreate_diff(diff_tgt)

    else:
        if not diagnostic_result["wrong"]:
            return None, None

        # Get first datapoint of given diagnostic
        line_num = diagnostic_result["wrong"][0]
        # print("line_num: ", line_num)

        # Show what went wrong
        diff_tgt = tgt_test_list[line_num]
        diff_inferred = inference_test_list[line_num]

        parsed_diff_correct = recreate_diff(diff_tgt)
        parsed_diff_inferred = recreate_diff(diff_inferred)

    src_str = src_test_list[line_num]
    parsed_src = recreate_src(src_str)

    datapoint_id = metadata_test["datapoints"][line_num]["ID"]

    diff_with_diags = f"""id: {datapoint_id}
diagnostic: {diagnostic_result['diagnostic_id']}
perc_correct_in_test: {diagnostic_result['perc_correct_in_test']}
num_datapoints_in_train: {diagnostic_result['num_datapoints_in_train']}"""

    correct_diff_with_diags = create_diff_with_diags(
        parsed_src, parsed_diff_correct)

    if getCorrectExample:
        diff_with_diags += "\n<<<<<<<< CORRECTLY INFERRED >>>>>>>>\n"
        diff_with_diags += correct_diff_with_diags

    else:
        inferred_diff_with_diags = create_diff_with_diags(
            parsed_src, parsed_diff_inferred)
        diff_with_diags += "\n<<<<<<<< CORRECT >>>>>>>>\n"
        diff_with_diags += correct_diff_with_diags
        diff_with_diags += "\n<<<<<<<< INFERRED >>>>>>>>\n"
        diff_with_diags += inferred_diff_with_diags

    return datapoint_id, diff_with_diags


def save_characteristic_examples(
    characteristic_examples_dict,
    src_test_list,
    tgt_test_list,
    inference_test_list,
    metadata_test
):

    for key, result_per_diagnostic_list in characteristic_examples_dict.items():
        for result_num, diagnostic_result in enumerate(result_per_diagnostic_list):
            if result_num == 2:
                break

            # Get a correct datapoint
            if key in ["highest_accuracy_copied", "highest_accuracy_extrapolated"]:

                _, diff_with_diags = generate_diff(
                    diagnostic_result,
                    src_test_list,
                    tgt_test_list,
                    inference_test_list,
                    metadata_test,
                    True
                )

            # Get an incorrect or ambiguous datapoint
            # key in (lowest_accuracy_copied, lowest_accuracy_extrapolated,
            # ambiguous_accuracy_copied & ambiguous_accuracy_extrapolated)
            else:

                _, diff_with_diags = generate_diff(
                    diagnostic_result,
                    src_test_list,
                    tgt_test_list,
                    inference_test_list,
                    metadata_test,
                    False
                )

            if not diff_with_diags:
                continue

            diff_filename = f"{key}_{str(result_num)}"
            diff_filepath = f"{characteristic_examples_dir}/{diff_filename}.diff"
            with open(diff_filepath, 'w', encoding='utf-8') as diff_file:
                diff_file.write(diff_with_diags)


def save_one_wrong_one_right_per_diagnostic(
    evaluation_dict,
    src_test_list,
    tgt_test_list,
    inference_test_list,
    metadata_test
):
    result_per_diagnostic = flatten_result_per_diagnostic(
        evaluation_dict["result_per_diagnostic"])

    for diagnostic_result in result_per_diagnostic:

        for getCorrectExample in [True, False]:
            datapoint_id, diff_with_diags = generate_diff(
                diagnostic_result,
                src_test_list,
                tgt_test_list,
                inference_test_list,
                metadata_test,
                getCorrectExample
            )

            if not diff_with_diags:
                continue

            diagnostic_id = diagnostic_result['diagnostic_id']
            correct = "correct" if getCorrectExample else "wrong"
            diff_filename = f"diag_{diagnostic_id}__{correct}__id_{datapoint_id}"
            diff_filepath = f"{examples_per_diagnostic_dir}/{diff_filename}.diff"
            with open(diff_filepath, 'w', encoding='utf-8') as diff_file:
                diff_file.write(diff_with_diags)


def sort_for_characteristic_examples(evaluation_dict):

    result_per_diagnostic = flatten_result_per_diagnostic(
        evaluation_dict["result_per_diagnostic"])

    highest_accuracy_copied = [
        result for result in result_per_diagnostic if result["num_datapoints_in_train"] > 0]
    highest_accuracy_copied.sort(
        key=lambda x: x.get('perc_correct_in_test'), reverse=True)
    highest_accuracy_extrapolated = [
        result for result in result_per_diagnostic if result["num_datapoints_in_train"] == 0]
    highest_accuracy_extrapolated.sort(
        key=lambda x: x.get('perc_correct_in_test'), reverse=True)

    lowest_accuracy_copied = [
        result for result in result_per_diagnostic if result["num_datapoints_in_train"] > 0]
    lowest_accuracy_copied.sort(key=lambda x: x.get('perc_correct_in_test'))
    lowest_accuracy_extrapolated = [
        result for result in result_per_diagnostic if result["num_datapoints_in_train"] == 0]
    lowest_accuracy_extrapolated.sort(
        key=lambda x: x.get('perc_correct_in_test'))

    ambiguous_accuracy_copied = [
        result for result in result_per_diagnostic if result["num_datapoints_in_train"] > 0]
    ambiguous_accuracy_copied.sort(
        key=lambda x: abs(x.get('perc_correct_in_test') - 0.5))
    ambiguous_accuracy_extrapolated = [
        result for result in result_per_diagnostic if result["num_datapoints_in_train"] == 0]
    ambiguous_accuracy_extrapolated.sort(
        key=lambda x: abs(x.get('perc_correct_in_test') - 0.5))

    return {
        "highest_accuracy_copied": highest_accuracy_copied,
        "highest_accuracy_extrapolated": highest_accuracy_extrapolated,
        "lowest_accuracy_copied": lowest_accuracy_copied,
        "lowest_accuracy_extrapolated": lowest_accuracy_extrapolated,
        "ambiguous_accuracy_copied": ambiguous_accuracy_copied,
        "ambiguous_accuracy_extrapolated": ambiguous_accuracy_extrapolated
    }


def plot_num_datapoints_vs_success(evaluation_dict, filename):
    datapoints_graph = flatten_result_per_diagnostic(
        evaluation_dict["result_per_diagnostic"])

    x = [datapoint["num_datapoints_in_train"]
         for datapoint in datapoints_graph]
    y = [datapoint["perc_correct_in_test"] for datapoint in datapoints_graph]
    text = [datapoint["diagnostic_id"] for datapoint in datapoints_graph]

    fig = px.scatter(
        x=x,
        y=y,
        # Text makes picture unreadable in Latex:
        # text=text,

        # trendline="ols"
    )

    markers = dict(size=9, color="rgba(5,5,5,0.4)")
    fig.update_traces(
        marker=markers,

        # Text makes picture unreadable in Latex:
        # textposition='top right',
        # textfont_size=10,
    )

    # fig.update_layout(title="Per Diagnostic: Data Points Needed To Produce Good Results in Test")
    fig.update_xaxes(title_text='Number datapoints in train')
    fig.update_yaxes(title_text='Success Rate')
    # fig.show()
    fig.write_image(f"{eval_dir}/{filename}")

    print(f"for {filename}; pearsonr: {pearsonr(x, y)}")


def plot_src_format_tokens_vs_success(evaluation_dict):
    """
    Not done for total tokens because file content is fixed to 100 tokens; Only checking 
    for formatting tokens in source.
    """

    filename = f"{experiment.name}_success_rate_formatting_len_src.svg"
    x_axis = "Number of Formatting Source Tokens"

    x = list(
        evaluation_dict["avg_success_perc_per_src_formatting_token"].keys())
    y = [success_perc for success_perc in evaluation_dict["avg_success_perc_per_src_formatting_token"].values()]

    fig = plot_num_tokens_vs_success(x, y, x_axis, "")

    # fig.show()
    fig.write_image(f"{eval_dir}/{filename}")

    # print(f"for {filename}; pearsonr: {pearsonr(x, y)}")


def plot_tgt_tokens_vs_success(evaluation_dict):
    """
    Plots total tokens and formatting tokens into one graph
    """

    filename = f"{experiment.name}_success_rate_tgt_len.svg"
    x_axis = "Number of Target Tokens"

    x_total = list(evaluation_dict["avg_success_perc_per_tgt_len"].keys())
    y_total = [
        success_perc for success_perc in evaluation_dict["avg_success_perc_per_tgt_len"].values()]
    legend = "Total"

    fig = plot_num_tokens_vs_success(x_total, y_total, x_axis, legend)

    x_formatting = list(
        evaluation_dict["avg_success_perc_per_tgt_formatting_token"].keys())
    y_formatting = [
        success_perc for success_perc in evaluation_dict["avg_success_perc_per_tgt_formatting_token"].values()]
    legend = "Formatting"

    # Need to append experiment.name to filename because of Latex SVG problems
    fig = plot_num_tokens_vs_success(
        x_formatting, y_formatting, x_axis, legend, fig)

    # fig.show()
    fig.write_image(f"{eval_dir}/{filename}")


def plot_num_tokens_vs_success(x, y, x_axis, legend, fig=None):

    if not fig:
        fig = go.Figure()
        fig.update_yaxes(title_text='Success Rate')
        fig.update_xaxes(title_text=x_axis)
        markers = dict(size=9, color="rgba(255,0,0,0.8)")
    else:
        markers = dict(size=9, color="rgba(0,0,255,0.8)")

    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="markers",
            marker=markers,
            name=legend
        )
    )

    return fig


def plot_loss_curve(tf_csv_path):
    """
    Only works with Tensorflow data (not Pytorch)
    """

    df = pd.read_csv(tf_csv_path)
    df = df.loc[df['tag'] == "loss"]

    fig = go.Figure()
    fig.update_xaxes(title_text='Steps')
    fig.update_yaxes(title_text='Loss')
    markers = dict(size=6, color="rgba(255,0,0,0.65)")

    fig.add_trace(
        go.Scatter(
            x=df['step'].tolist(),
            y=df['value'].tolist(),
            mode="markers",
            marker=markers
        )
    )

    filename = f"{experiment.name}_loss_function.svg"
    fig.write_image(f"{eval_dir}/{filename}")


def remove_redundant_data(evaluation_dict):

    for diagnostic_id, result in evaluation_dict["result_per_diagnostic"].items():
        # result["correct"] = len(result["correct"])
        # result["wrong"] = len(result["wrong"])
        result["num_datapoints_in_test"] = len(
            result["correct"]) + len(result["wrong"])
        result.pop('correct', None)
        result.pop('wrong', None)


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

    save_num_tokens_vs_success_perc(evaluation_dict, metadata_train,
                                    metadata_test, src_test_list, tgt_test_list, inference_test_list)

    save_num_formatting_tokens_vs_success_perc(
        evaluation_dict, src_test_list, tgt_test_list, inference_test_list)

    save_result_per_diagnostic(
        evaluation_dict, metadata_train, metadata_test, tgt_test_list, inference_test_list)

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
        value["perc_correct_in_test"] = num_correct / total_datapoints

        total_total += total_datapoints
        total_correct += num_correct

        if value["num_datapoints_in_train"] > 0:
            copied_correct += num_correct
            copied_total += total_datapoints
        else:
            extrapolated_correct += num_correct
            extrapolated_total += total_datapoints

    evaluation_dict["num_extrapolated_datapoints"] = extrapolated_total

    evaluation_dict["correct_results_total_perc"] = (
        total_correct / total_total) if total_total > 0 else None
    evaluation_dict["correct_results_copied_perc"] = (
        copied_correct / copied_total) if copied_total else None
    evaluation_dict["correct_results_extrapolated_perc"] = (
        extrapolated_correct / extrapolated_total) if extrapolated_total else None

    save_diagnostic_avg_results(evaluation_dict)

    characteristic_examples_dict = sort_for_characteristic_examples(
        evaluation_dict)

    save_characteristic_examples(
        characteristic_examples_dict,
        src_test_list,
        tgt_test_list,
        inference_test_list,
        metadata_test
    )

    save_one_wrong_one_right_per_diagnostic(
        evaluation_dict,
        src_test_list,
        tgt_test_list,
        inference_test_list,
        metadata_test
    )

    plot_num_datapoints_vs_success(
        evaluation_dict, f"{experiment.name}_impact_data_on_accuracy.svg")

    plot_src_format_tokens_vs_success(evaluation_dict)
    plot_tgt_tokens_vs_success(evaluation_dict)

    if nn_framework == NNFramework.tensorflow:
        plot_loss_curve(experiment_csv_file)

    remove_redundant_data(evaluation_dict)

    with open(inference_eval_file, 'w') as fout:
        json_str = json.dumps(evaluation_dict, indent=4)
        print(json_str, file=fout)


if __name__ == '__main__':
    main()
