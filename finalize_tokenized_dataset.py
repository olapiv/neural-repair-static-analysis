import os
import json
import random
import math
import copy
import statistics
from enum import Enum
from pathlib import Path
from collections import Counter

random.seed(10)  # For reproducible shuffles


class Modes:
    """
        Two modes:
            1. Imitation: Entirely mixed dataset
            2. Extrapolation: Only new diag messages for test & validation
    """

    class Imitation:
        label = "imitate"
        train_perc = 0.6
        val_perc = 0.2
        test_perc = 0.2

    class Extrapolation:
        label = "extrapolate"
        train_perc = 0.7
        val_perc = 0.2
        test_perc = 0.1


class InputOutput(Enum):
    src = "src"
    tgt = "tgt"


class Stage(Enum):
    train = "train"
    val = "val"
    test = "test"


metadata_dict = {
    "num-datapoints": 0,

    "num-nugets": 0,
    "avg-data-points-per-nuget": 0,
    "std-data-points-per-nuget": 0,

    "num-diagnostics": 0,
    "avg-data-points-per-diagnostic": 0,
    "std-data-points-per-diagnostic": 0,

    "num-repos": 0,
    "avg-data-points-per-repo": 0,
    "std-data-points-per-repo": 0,

    "token-num-src": [],
    "max-tokens-src": 0,
    "avg-tokens-src": 0,
    "std-tokens-src": 0,

    "token-num-tgt": [],
    "max-tokens-tgt": 0,
    "avg-tokens-tgt": 0,
    "std-tokens-tgt": 0,

    "nugets": {
        # "BitCodeAnalyzer.4.1.0": 3,
        # "Documentation.Analyser.1.1.1": 5
    },
    "diagnostics": {
        # "DA2001": 4,
        # "DA2003": 4
    },
    "repos": {
        # "dapper-dot-net": 4,
        # "mono": 9,
        # "ServiceStack": 2
    },
    "datapoints": [
        # {
        #     "ID": "226128-0",
        #     "DiagnosticID": "DA2003",
        #     "Nuget": "Documentation.Analyser.1.1.1",
        #     "Repo": "mono"
        # }
    ]
}


class Pipeline:

    def __init__(self, input_dir, mode=Modes.Extrapolation, limit_tgt_tokens=500, limit_src_tokens=500):

        self.mode = mode
        self.input_dir = input_dir

        input_dir_basename = os.path.basename(os.path.normpath(input_dir))
        self.output_dir = f"experiment/{mode.label}__{input_dir_basename}"
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

        self.limit_tgt_tokens = limit_tgt_tokens
        self.limit_src_tokens = limit_src_tokens

    def initialize_data_files(self, mode, all_filepaths):
        data_files = {}
        for inputOutput in InputOutput:
            data_files[inputOutput.value] = {}
            for stage in Stage:
                data_files[inputOutput.value][stage.value] = {}
                filepath = f"{self.output_dir}/{inputOutput.value}-{stage.value}.txt"
                data_files[inputOutput.value][stage.value] = filepath
                all_filepaths.append(filepath)

        return data_files

    def initialize_metadata(self, mode, all_filepaths):
        metadata = {}
        total_metadata = f"{self.output_dir}/metadata-total.json"
        metadata["total"] = {}
        metadata["total"]["file"] = total_metadata
        metadata["total"]["data"] = copy.deepcopy(metadata_dict)
        metadata["total"]["data"].pop("datapoints", None)

        all_filepaths.append(total_metadata)
        for stage in Stage:
            metadata[stage.value] = {}
            metadata_filepath = f"{self.output_dir}/metadata-{stage.value}.json"
            metadata[stage.value]["file"] = metadata_filepath
            all_filepaths.append(metadata_filepath)
            metadata[stage.value]["data"] = copy.deepcopy(metadata_dict)

        return metadata

    def flatten_input_datapoint(self, datapoint_dict):
        input_list = []

        for diag in datapoint_dict["DiagnosticOccurances"]:
            input_list.append("LINE")
            # input_list.extend([int(d) for d in diag["Line"]])
            # Offset is subtracted anyways
            input_list.append(str(diag["Line"]))
            input_list.append("MESSAGE")
            input_list.extend(diag["TokenizedMessage"])

        input_list.append("FILE_CONTENT")
        input_list.extend(datapoint_dict["TokenizedFileContext"])

        return " ".join(input_list) + "\n"

    def flatten_output_datapoint(self, datapoint_dict):
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
            output_list.append(str(action["SourceLocationStart"]))
            output_list.append("SOURCE_LOCATION_END")
            output_list.append(str(action["SourceLocationEnd"]))

        return " ".join(output_list) + "\n"

    def generate_num_token_statistics(self, metadata):
        total_src = []
        total_tgt = []
        for stage in Stage:
            metadata[stage.value]["data"]["max-tokens-src"] = max(
                metadata[stage.value]["data"]["token-num-src"])
            metadata[stage.value]["data"]["avg-tokens-src"] = statistics.mean(
                metadata[stage.value]["data"]["token-num-src"])
            metadata[stage.value]["data"]["std-tokens-src"] = statistics.pstdev(
                metadata[stage.value]["data"]["token-num-src"])
            total_src += metadata[stage.value]["data"]["token-num-src"]

            metadata[stage.value]["data"]["max-tokens-tgt"] = max(
                metadata[stage.value]["data"]["token-num-tgt"])
            metadata[stage.value]["data"]["avg-tokens-tgt"] = statistics.mean(
                metadata[stage.value]["data"]["token-num-tgt"])
            metadata[stage.value]["data"]["std-tokens-tgt"] = statistics.pstdev(
                metadata[stage.value]["data"]["token-num-tgt"])
            total_tgt += metadata[stage.value]["data"]["token-num-tgt"]

            metadata[stage.value]["data"].pop("token-num-src", None)
            metadata[stage.value]["data"].pop("token-num-tgt", None)

        metadata["total"]["data"]["max-tokens-src"] = max(total_src)
        metadata["total"]["data"]["avg-tokens-src"] = statistics.mean(
            total_src)
        metadata["total"]["data"]["std-tokens-src"] = statistics.pstdev(
            total_src)

        metadata["total"]["data"]["max-tokens-tgt"] = max(total_tgt)
        metadata["total"]["data"]["avg-tokens-tgt"] = statistics.mean(
            total_tgt)
        metadata["total"]["data"]["std-tokens-tgt"] = statistics.pstdev(
            total_tgt)

        metadata["total"]["data"].pop("token-num-src", None)
        metadata["total"]["data"].pop("token-num-tgt", None)

    def generate_diagnostics_statistics(self, metadata):

        all_diagnostics = Counter({})
        for stage in Stage:

            diagnostics = metadata[stage.value]["data"]["diagnostics"]

            metadata[stage.value]["data"]["num-diagnostics"] = len(diagnostics)

            data_points_per_diagnostic = diagnostics.values()
            metadata[stage.value]["data"]["avg-data-points-per-diagnostic"] = statistics.mean(data_points_per_diagnostic)
            metadata[stage.value]["data"]["std-data-points-per-diagnostic"] = statistics.pstdev(data_points_per_diagnostic)

            all_diagnostics += Counter(diagnostics)

        metadata["total"]["data"]["diagnostics"] = all_diagnostics
        metadata["total"]["data"]["num-diagnostics"] = len(all_diagnostics)
        data_points_per_diagnostic = all_diagnostics.values()
        metadata["total"]["data"]["avg-data-points-per-diagnostic"] = statistics.mean(data_points_per_diagnostic)
        metadata["total"]["data"]["std-data-points-per-diagnostic"] = statistics.pstdev(data_points_per_diagnostic)

    def generate_nuget_statistics(self, metadata):

        all_nugets = Counter({})
        for stage in Stage:

            nugets = metadata[stage.value]["data"]["nugets"]

            metadata[stage.value]["data"]["num-nugets"] = len(nugets)

            data_points_per_nuget = nugets.values()
            metadata[stage.value]["data"]["avg-data-points-per-nuget"] = statistics.mean(data_points_per_nuget)
            metadata[stage.value]["data"]["std-data-points-per-nuget"] = statistics.pstdev(data_points_per_nuget)

            all_nugets += Counter(nugets)

        metadata["total"]["data"]["nugets"] = all_nugets
        metadata["total"]["data"]["num-nugets"] = len(all_nugets)
        data_points_per_nuget = all_nugets.values()
        metadata["total"]["data"]["avg-data-points-per-nuget"] = statistics.mean(data_points_per_nuget)
        metadata["total"]["data"]["std-data-points-per-nuget"] = statistics.pstdev(data_points_per_nuget)

    def generate_repo_statistics(self, metadata):

        all_repos = Counter({})
        for stage in Stage:

            repos = metadata[stage.value]["data"]["repos"]

            metadata[stage.value]["data"]["num-repos"] = len(repos)

            data_points_per_repo = repos.values()
            metadata[stage.value]["data"]["avg-data-points-per-repo"] = statistics.mean(data_points_per_repo)
            metadata[stage.value]["data"]["std-data-points-per-repo"] = statistics.pstdev(data_points_per_repo)

            all_repos += Counter(repos)

        metadata["total"]["data"]["repos"] = all_repos
        metadata["total"]["data"]["num-repos"] = len(all_repos)
        data_points_per_repo = all_repos.values()
        metadata["total"]["data"]["avg-data-points-per-repo"] = statistics.mean(data_points_per_repo)
        metadata["total"]["data"]["std-data-points-per-repo"] = statistics.pstdev(data_points_per_repo)

    def filter_useful_datapoints(self, tokenized_files):

        useful_datapoints = []
        bad_newline_endings = 0
        duplications = {}

        seen_src = set()
        for tokenized_file in tokenized_files:

            print("tokenized_file: ", tokenized_file.name)

            with open(tokenized_file) as json_file:
                tokenized_data_dict = json.load(json_file)

            src_string = self.flatten_input_datapoint(tokenized_data_dict)
            target_string = self.flatten_output_datapoint(tokenized_data_dict)

            # TODO: Debug this for new dataset
            if src_string.count("\n") > 1 or target_string.count("\n") > 1:
                print("Bad newline encoding! tokenized_file: ",
                      tokenized_file.name)
                bad_newline_endings += 1
                if src_string.count("\n") > 1:
                    print("src_string: ", src_string)
                if target_string.count("\n") > 1:
                    print("target_string: ", target_string)
                continue

            num_src_tokens = len(src_string.split())
            num_tgt_tokens = len(target_string.split())

            if num_src_tokens > self.limit_src_tokens:
                print("Too many tokens; num_src_tokens: ", num_src_tokens)
                continue

            if num_tgt_tokens > self.limit_tgt_tokens:
                print("Too many tokens; num_tgt_tokens: ", num_tgt_tokens)
                continue

            # Can happen since dataset was generated across C# solutions; one project can be included by
            # multiple solutions and therefore fix duplications may occur
            if src_string in seen_src:
                print(f"Duplication in of src_string!")
                if src_string not in duplications:
                    duplications[src_string] = 0
                duplications[src_string] += 1
                continue
            else:
                seen_src.add(src_string)

            useful_datapoints.append(tokenized_file)

        print("bad_newline_endings: ", bad_newline_endings)
        print("Total initial tokenized files :", len(tokenized_files))
        print("Total useful tokenized files :", len(useful_datapoints))
        print("Total src duplications: ", len(tokenized_files) - len(seen_src))
        print("Unique src duplications: ", len(duplications.keys()))

        return useful_datapoints

    def split_dataset_by_diagnostics(self, tokenized_files):
        """
            Evaluate NN for EXTRAPOLATION
            70% diagnostics in train
            20% diagnostics in validation
            10% diagnostics in test
            --> Mix diagnostics randomly
        """

        # Get and shuffle diagnostics
        diagnostics = []
        for tokenized_file in tokenized_files:
            with open(tokenized_file) as json_file:
                tokenized_data_dict = json.load(json_file)
            diagnostics.append(tokenized_data_dict["DiagnosticID"])

        diagnostics = list(set(diagnostics))
        diagnostics.sort()  # To have a reproducible shuffle
        random.shuffle(diagnostics)

        # Consider checking analyzer_package_details.csv that test diagnostics are unique

        # Split diagnostics into datasets
        train_diagnostics = []
        val_diagnostics = []
        test_diagnostics = []
        for diagnostic in diagnostics:
            if (len(train_diagnostics) / len(diagnostics)) < Modes.Extrapolation.train_perc:
                train_diagnostics.append(diagnostic)
            elif (len(val_diagnostics) / len(diagnostics)) < Modes.Extrapolation.val_perc:
                val_diagnostics.append(diagnostic)
            else:
                test_diagnostics.append(diagnostic)

        # Assign datapoints to datasets
        file_to_dataset = {}
        for tokenized_file in tokenized_files:

            with open(tokenized_file) as json_file:
                tokenized_data_dict = json.load(json_file)

            diagnostic = tokenized_data_dict["DiagnosticID"]
            if diagnostic in train_diagnostics:
                file_to_dataset[tokenized_file.name] = Stage.train.value
            elif diagnostic in val_diagnostics:
                file_to_dataset[tokenized_file.name] = Stage.val.value
            else:
                file_to_dataset[tokenized_file.name] = Stage.test.value

        return file_to_dataset

    def split_dataset_by_datapoints(self, tokenized_files):
        """
            Train NN for COPY
            60% datapoints in train
            20% datapoints in validation
            20% datapoints in test
            --> Mix datapoints randomly
        """

        # Sort first to have a reproducible shuffle
        tokenized_files.sort(key=lambda x: x.name)
        random.shuffle(tokenized_files)

        file_to_dataset = {}

        num_total_datapoints = len(tokenized_files)
        train_datapoints = 0
        val_datapoints = 0
        test_datapoints = 0

        for tokenized_file in tokenized_files:

            if (train_datapoints / num_total_datapoints) < Modes.Imitation.train_perc:
                train_datapoints += 1
                file_to_dataset[tokenized_file.name] = Stage.train.value
            elif (val_datapoints / num_total_datapoints) < Modes.Imitation.val_perc:
                val_datapoints += 1
                file_to_dataset[tokenized_file.name] = Stage.val.value
            else:
                test_datapoints += 1
                file_to_dataset[tokenized_file.name] = Stage.test.value

        return file_to_dataset

    def calculate_num_datapoints(self, metadata, file_to_dataset):

        metadata["total"]["data"]["num-datapoints"] = len(file_to_dataset)
        for stage in Stage:
            filtered_dict = {k: v for k,
                             v in file_to_dataset.items() if v == stage.value}
            metadata[stage.value]["data"]["num-datapoints"] = len(
                filtered_dict)

    def main(self):
        all_filepaths = []

        metadata = self.initialize_metadata(self.mode, all_filepaths)
        data_files = self.initialize_data_files(self.mode, all_filepaths)

        # Clear content of all files
        for filepath in all_filepaths:
            open(filepath, 'w').close()

        tokenized_files = [f for f in os.scandir(
            self.input_dir) if f.is_file() and f.name.endswith(".json")]

        tokenized_files = self.filter_useful_datapoints(tokenized_files)

        if self.mode == Modes.Extrapolation:
            file_to_dataset = self.split_dataset_by_diagnostics(
                tokenized_files)
        elif self.mode == Modes.Imitation:
            file_to_dataset = self.split_dataset_by_datapoints(tokenized_files)

        self.calculate_num_datapoints(metadata, file_to_dataset)

        for tokenized_file in tokenized_files:

            with open(tokenized_file) as json_file:
                tokenized_data_dict = json.load(json_file)

            diagnostic_id = tokenized_data_dict["DiagnosticID"]
            nuget_name = tokenized_data_dict["AnalyzerNuGet"]
            repo = tokenized_data_dict["Repo"]

            src_string = self.flatten_input_datapoint(tokenized_data_dict)
            target_string = self.flatten_output_datapoint(tokenized_data_dict)

            num_src_tokens = len(src_string.split())
            num_tgt_tokens = len(target_string.split())

            current_stage = file_to_dataset[tokenized_file.name]

            metadata[current_stage]["data"]["token-num-src"].append(num_src_tokens)
            metadata[current_stage]["data"]["token-num-tgt"].append(num_tgt_tokens)
            
            metadata[current_stage]["data"]["datapoints"].append({
                "ID": os.path.splitext(tokenized_file.name)[0],
                "DiagnosticID": diagnostic_id,
                "Nuget": nuget_name,
                "Repo": repo
            })

            if diagnostic_id not in metadata[current_stage]["data"]["diagnostics"]:
                metadata[current_stage]["data"]["diagnostics"][diagnostic_id] = 0
            metadata[current_stage]["data"]["diagnostics"][diagnostic_id] += 1
            
            if nuget_name not in metadata[current_stage]["data"]["nugets"]:
                metadata[current_stage]["data"]["nugets"][nuget_name] = 0
            metadata[current_stage]["data"]["nugets"][nuget_name] += 1

            if repo not in metadata[current_stage]["data"]["repos"]:
                metadata[current_stage]["data"]["repos"][repo] = 0
            metadata[current_stage]["data"]["repos"][repo] += 1

            src_filepath = data_files["src"][current_stage]
            target_filepath = data_files["tgt"][current_stage]

            with open(src_filepath, 'a', encoding='utf-8') as src_file:
                src_file.write(src_string)

            with open(target_filepath, 'a', encoding='utf-8') as target_file:
                target_file.write(target_string)

        self.generate_num_token_statistics(metadata)
        self.generate_diagnostics_statistics(metadata)
        self.generate_nuget_statistics(metadata)
        self.generate_repo_statistics(metadata)

        for stage in Stage:
            with open(metadata[stage.value]["file"], 'w') as fout:
                json_str = json.dumps(metadata[stage.value]["data"], indent=4)
                print(json_str, file=fout)

        with open(metadata["total"]["file"], 'w') as fout:
            json_str = json.dumps(metadata["total"]["data"], indent=4)
            print(json_str, file=fout)


if __name__ == '__main__':

    input_dir = "tokenized_datasets/100_tokens__standard__3"
    mode = Modes.Imitation

    pipeline = Pipeline(input_dir, mode)
    pipeline.main()
