import os
import json
import random
import math
import copy
import statistics
from enum import Enum
from collections import Counter


tokenized_dataset_dir = "tokenized_dataset"
final_dataset_dir = "final_dataset"


class NormalMode:
    train_perc = 0.6
    val_perc = 0.2
    test_perc = 0.2

# train: 10000  --> 63%
# test: 2737  -->  17%
# val: 3000  --> 19%
# 15737


class InputOutput(Enum):
    src = "src"
    tgt = "tgt"


class Stage(Enum):
    train = "train"
    val = "val"
    test = "test"


all_filepaths = []

data_files = {}
for inputOutput in InputOutput:
    data_files[inputOutput.value] = {}
    for stage in Stage:
        data_files[inputOutput.value][stage.value] = {}
        filepath = f"{final_dataset_dir}/{inputOutput.value}-{stage.value}.txt"
        data_files[inputOutput.value][stage.value] = filepath
        all_filepaths.append(filepath)


metadata_dict = {
    "num-unique-diagnostics": 0,
    "avg-data-points-per-diagnostic": 0,
    "std-data-points-per-diagnostic": 0,

    "token-num-src": [],
    "max-tokens-src": 0,
    "avg-tokens-src": 0,
    "std-tokens-src": 0,

    "token-num-tgt": [],
    "max-tokens-tgt": 0,
    "avg-tokens-tgt": 0,
    "std-tokens-tgt": 0,

    "diagnostics": {
        # "DA2001": 4,
        # "DA2003": 4
    },
    "datapoints": [
        # {
        #     "ID": "226128-0",
        #     "Diagnostic": "DA2003"
        # }
    ]
}

metadata = {}
total_metadata = f"{final_dataset_dir}/metadata-total.json"
metadata["total"] = {}
metadata["total"]["file"] = total_metadata
metadata["total"]["data"] = copy.deepcopy(metadata_dict)
all_filepaths.append(total_metadata)
for stage in Stage:
    metadata[stage.value] = {}
    metadata_filepath = f"{final_dataset_dir}/metadata-{stage.value}.json"
    metadata[stage.value]["file"] = metadata_filepath
    all_filepaths.append(metadata_filepath)
    metadata[stage.value]["data"] = copy.deepcopy(metadata_dict)


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


def generate_num_token_statistics(metadata):
    total_src = []
    total_tgt = []
    for stage in Stage:
        metadata[stage.value]["data"]["max-tokens-src"] = max(metadata[stage.value]["data"]["token-num-src"])
        metadata[stage.value]["data"]["avg-tokens-src"] = statistics.mean(metadata[stage.value]["data"]["token-num-src"])
        metadata[stage.value]["data"]["std-tokens-src"] = statistics.pstdev(metadata[stage.value]["data"]["token-num-src"])
        total_src += metadata[stage.value]["data"]["token-num-src"]

        metadata[stage.value]["data"]["max-tokens-tgt"] = max(metadata[stage.value]["data"]["token-num-tgt"])
        metadata[stage.value]["data"]["avg-tokens-tgt"] = statistics.mean(metadata[stage.value]["data"]["token-num-tgt"])
        metadata[stage.value]["data"]["std-tokens-tgt"] = statistics.pstdev(metadata[stage.value]["data"]["token-num-tgt"])
        total_tgt += metadata[stage.value]["data"]["token-num-tgt"]

        metadata[stage.value]["data"].pop("token-num-src", None)
        metadata[stage.value]["data"].pop("token-num-tgt", None)

    metadata["total"]["data"]["max-tokens-src"] = max(total_src)
    metadata["total"]["data"]["avg-tokens-src"] = statistics.mean(total_src)
    metadata["total"]["data"]["std-tokens-src"] = statistics.pstdev(total_src)

    metadata["total"]["data"]["max-tokens-tgt"] = max(total_tgt)
    metadata["total"]["data"]["avg-tokens-tgt"] = statistics.mean(total_tgt)
    metadata["total"]["data"]["std-tokens-tgt"] = statistics.pstdev(total_tgt)

    metadata["total"]["data"].pop("token-num-src", None)
    metadata["total"]["data"].pop("token-num-tgt", None)


def generate_diagnostics_statistics(metadata):

    all_diagnostics = Counter({})
    for stage in Stage:        
        num_unique_diagnostics = len(metadata[stage.value]["data"]["diagnostics"])
        metadata[stage.value]["data"]["num-unique-diagnostics"] = num_unique_diagnostics

        data_points_per_diagnostic = metadata[stage.value]["data"]["diagnostics"].values()
        metadata[stage.value]["data"]["avg-data-points-per-diagnostic"] = statistics.mean(data_points_per_diagnostic)
        metadata[stage.value]["data"]["std-data-points-per-diagnostic"] = statistics.pstdev(data_points_per_diagnostic)

        all_diagnostics += Counter(metadata[stage.value]["data"]["diagnostics"])

    metadata["total"]["data"]["diagnostics"] = all_diagnostics
    metadata["total"]["data"]["num-unique-diagnostics"] = len(all_diagnostics)
    data_points_per_diagnostic = all_diagnostics.values()
    metadata["total"]["data"]["avg-data-points-per-diagnostic"] = statistics.mean(data_points_per_diagnostic)
    metadata["total"]["data"]["std-data-points-per-diagnostic"] = statistics.pstdev(data_points_per_diagnostic)
    metadata["total"]["data"].pop("datapoints", None)


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

    for tokenized_file in tokenized_files:

        print("tokenized_file: ", tokenized_file.name)

        with open(tokenized_file) as json_file:
            tokenized_data_dict = json.load(json_file)

        src_string = flatten_input_datapoint(tokenized_data_dict)
        target_string = flatten_output_datapoint(tokenized_data_dict)

        if src_string.count("\n") > 1 or target_string.count("\n") > 1:
            print("Bad newline encoding! tokenized_file: ", tokenized_file.name)
            bad_newline_endings += 1

        num_src_tokens = len(src_string.split())
        num_tgt_tokens = len(target_string.split())

        if (train_datapoints / num_total_datapoints) < NormalMode.train_perc:
            train_datapoints += 1
            current_stage = Stage.train.value
        elif (val_datapoints / num_total_datapoints) < NormalMode.val_perc:
            val_datapoints += 1
            current_stage = Stage.val.value
        else:
            test_datapoints += 1
            current_stage = Stage.test.value

        src_filepath = data_files["src"][current_stage]
        target_filepath = data_files["tgt"][current_stage]
        metadata[current_stage]["data"]["token-num-src"].append(num_src_tokens)
        metadata[current_stage]["data"]["token-num-tgt"].append(num_tgt_tokens)
        diagnostic_id = tokenized_data_dict["DiagnosticID"]
        metadata[current_stage]["data"]["datapoints"].append({
            "ID": os.path.splitext(tokenized_file.name)[0],
            "DiagnosticID": diagnostic_id
        })
        if diagnostic_id in metadata[current_stage]["data"]["diagnostics"]:
            metadata[current_stage]["data"]["diagnostics"][diagnostic_id] += 1
        else:
            metadata[current_stage]["data"]["diagnostics"][diagnostic_id] = 1

        with open(src_filepath, 'a', encoding='utf-8') as src_file:
            src_file.write(src_string)

        with open(target_filepath, 'a', encoding='utf-8') as target_file:
            target_file.write(target_string)

    print("bad_newline_endings: ", bad_newline_endings)

    generate_num_token_statistics(metadata)
    generate_diagnostics_statistics(metadata)

    for stage in Stage:
        with open(metadata[stage.value]["file"], 'w') as fout:
            json_str = json.dumps(metadata[stage.value]["data"], indent=4)
            print(json_str, file=fout)

    with open(metadata["total"]["file"], 'w') as fout:
        json_str = json.dumps(metadata["total"]["data"], indent=4)
        print(json_str, file=fout)


if __name__ == '__main__':
    main()
