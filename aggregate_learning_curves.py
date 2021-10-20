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
from evaluate_nn_results import Experiment, Tokenization, NNFramework, NNModel


class Tag(Enum):
    train = "loss"
    validation = "metrics/loss"


def get_csv_file_path(experiment, tokenization):
    dataset_version = "3"
    nn_framework = NNFramework.tensorflow
    nn_model = NNModel.transformer

    data_config_str = f"{experiment.value}__{tokenization.value}__{dataset_version}"
    final_dataset_dir = f"experiment/{data_config_str}"

    nn_config_str = f"{nn_framework.value}_{nn_model.value}"
    eval_dir = f"{final_dataset_dir}/evaluation_{nn_config_str}"

    experiment_csv_file = f"{eval_dir}/experiment.csv"
    return experiment_csv_file


def plot_loss_curve(x, y, legend, fig=None):

    markerSize = 12
    if len(x) > 50:
        markerSize = 6

    if not fig:
        fig = go.Figure()
        fig.update_yaxes(title_text='Loss')
        fig.update_xaxes(title_text="Steps")
        markers = dict(size=markerSize, color="rgba(255,0,0,0.65)")
    else:
        markers = dict(size=markerSize, color="rgba(0,0,255,0.65)")

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


def get_data(csv_file, tag):
    df = pd.read_csv(csv_file)
    df = df.loc[df['tag'] == tag]
    x = df['step'].tolist()
    y = df['value'].tolist()
    return x, y


def run_mode():

    for experiment in Experiment:

        for tag in Tag:

            csv_file_camelcase = get_csv_file_path(experiment, Tokenization.camelcase)
            csv_file_standard_tokenization = get_csv_file_path(experiment, Tokenization.standard)

            x_camel, y_camel = get_data(csv_file_camelcase, tag.value)
            x_stand, y_stand = get_data(csv_file_standard_tokenization, tag.value)

            fig = plot_loss_curve(x_camel, y_camel, "Split by Camelcase")
            fig = plot_loss_curve(x_stand, y_stand, "Standard Tokenization", fig)

            # No chance of making this work in f*cking Latex
            # fig.update_layout(legend=dict(
            #     orientation="h",
            #     yanchor="bottom",
            #     y=0.95,
            #     xanchor="right",
            #     x=1
            # ))

            fig.show()

            filename = f"{experiment.name}_{tag.name}_loss_function.svg"
            fig.write_image(f"experiment/{filename}")


run_mode()
