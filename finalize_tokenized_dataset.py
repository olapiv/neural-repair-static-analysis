import os
import json
import random
import math
import statistics


tokenized_dataset_dir = "tokenized_dataset"
final_dataset_dir = "final_dataset"


class SourceFilenames:
    train_filename = "src-train.txt"
    test_filename = "src-test.txt"
    val_filename = "src-val.txt"


class TargetFilenames:
    train_filename = "tgt-train.txt"
    test_filename = "tgt-test.txt"
    val_filename = "tgt-val.txt"


src_train_filepath = f"{final_dataset_dir}/{SourceFilenames.train_filename}"
src_test_filepath = f"{final_dataset_dir}/{SourceFilenames.test_filename}"
src_val_filepath = f"{final_dataset_dir}/{SourceFilenames.val_filename}"

target_train_filepath = f"{final_dataset_dir}/{TargetFilenames.train_filename}"
target_test_filepath = f"{final_dataset_dir}/{TargetFilenames.test_filename}"
target_val_filepath = f"{final_dataset_dir}/{TargetFilenames.val_filename}"

all_filepaths = [src_train_filepath, target_train_filepath, src_test_filepath,
                 target_test_filepath, src_val_filepath, target_val_filepath]


class NormalMode:
    train_perc = 0.6
    test_perc = 0.2
    val_perc = 0.2

# train: 10000  --> 63%
# test: 2737  -->  17%
# val: 3000  --> 19%
# 15737


def flatten_input_datapoint(datapoint_dict):
    input_list = []

    for diag in datapoint_dict["DiagnosticOccurances"]:
        input_list.append("LINE")
        # input_list.extend([int(d) for d in diag["Line"]])
        input_list.append(str(diag["Line"]))  # Offset is subtracted anyways
        input_list.append("MESSAGE")
        input_list.extend(diag["TokenizedMessage"])

    input_list.append("FILE_CONTENT")
    input_list.extend(datapoint_dict["TokenizedFileContext"])

    return " ".join(input_list) + "\n"


def flatten_output_datapoint(datapoint_dict):
    output_list = []

    action_type = datapoint_dict["ParsedDiff"]["ActionType"]
    action = datapoint_dict["ParsedDiff"]["Action"]

    if action_type == "ADD":

        output_list.append("ADD")
        output_list.append("PREVIOUS_SOURCE_LOCATION")
        output_list.append(str(action["PreviousSourceLocation"]))
        output_list.append("TARGET_LINES")
        output_list.extend(action["TokenizedTargetLines"])

    elif action_type == "REPLACE":

        output_list.append("REPLACE")
        output_list.append("SOURCE_LOCATION")
        output_list.extend([str(line_num)
                           for line_num in action["SourceLocations"]])
        output_list.append("TARGET_LINES")
        output_list.extend(action["TokenizedTargetLines"])

    else:  # REMOVE

        output_list.append("REMOVE")
        output_list.append("SOURCE_LOCATION_START")
        output_list.extend(str(action["SourceLocationStart"]))
        output_list.append("SOURCE_LOCATION_END")
        output_list.extend(str(action["SourceLocationEnd"]))

    return " ".join(output_list) + "\n"


def main(zero_index_vars=False):
    """
        Two modes:
            1. COPY_MODE: copy behaviour learning (Entirely mixed)
                60%, 20%, 20%

            2. EXTRAP_MODE: extrapolation learning (Only new diag messages for validation)
                70%, 20%, 10%

        1. COPY_MODE:
            1. Mix datapoints randomly
        1. EXTRAP_MODE: (TODO: do later)
            1. Count no. of datapoints per Diag ID
            1. Calculate % of dataset per Diag ID
            1. ...
        1. Flatten all data
    """

    # Clear content of all files
    for filepath in all_filepaths:
        open(filepath, 'w').close()

    tokenized_files = [f for f in os.scandir(
        tokenized_dataset_dir) if f.is_file() and f.name.endswith(".json")]
    random.shuffle(tokenized_files)

    num_total_datapoints = len(tokenized_files)
    train_datapoints = 0
    test_datapoints = 0
    val_datapoints = 0

    bad_newline_endings = 0
    token_num_src = []
    token_num_tgt = []

    for tokenized_file in tokenized_files:

        print("tokenized_file: ", tokenized_file.name)

        with open(tokenized_file) as json_file:
            tokenized_data_dict = json.load(json_file)

        src_string = flatten_input_datapoint(tokenized_data_dict)
        target_string = flatten_output_datapoint(tokenized_data_dict)

        token_num_src.append(len(src_string.split()))
        token_num_tgt.append(len(target_string.split()))

        if src_string.count("\n") > 1 or target_string.count("\n") > 1:
            print("Bad newline encoding! tokenized_file: ", tokenized_file.name)
            bad_newline_endings += 1

        if (train_datapoints / num_total_datapoints) < NormalMode.train_perc:
            src_filepath = src_train_filepath
            target_filepath = target_train_filepath
            train_datapoints += 1
        elif (test_datapoints / num_total_datapoints) < NormalMode.test_perc:
            src_filepath = src_test_filepath
            target_filepath = target_test_filepath
            test_datapoints += 1
        else:
            src_filepath = src_val_filepath
            target_filepath = target_val_filepath
            val_datapoints += 1

        with open(src_filepath, 'a', encoding='utf-8') as src_file:
            src_file.write(src_string)

        with open(target_filepath, 'a', encoding='utf-8') as target_file:
            target_file.write(target_string)

    print("bad_newline_endings: ", bad_newline_endings)

    max_src_tokens = max(token_num_src)
    max_tgt_tokens = max(token_num_tgt)
    avg_src_tokens = statistics.mean(token_num_src)
    avg_tgt_tokens = statistics.mean(token_num_tgt)
    std_src_tokens = math.sqrt(statistics.pvariance(token_num_src))
    std_tgt_tokens = math.sqrt(statistics.pvariance(token_num_tgt))

    print("max_src_tokens: ", max_src_tokens)
    print("avg_src_tokens: ", avg_src_tokens)
    print("std_src_tokens: ", std_src_tokens)

    print("max_tgt_tokens: ", max_tgt_tokens)
    print("avg_tgt_tokens: ", avg_tgt_tokens)
    print("std_tgt_tokens: ", std_tgt_tokens)


if __name__ == '__main__':
    main()
