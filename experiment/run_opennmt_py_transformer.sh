#!/bin/bash

if [ -z "$1" ]; then
    echo "Missing dataset name as argument (e.g. imitate__100_tokens__standard__3, imitate__115_tokens__camelcase__3, etc.)"
    exit 1
fi

DATASET_NAME=$1

MODEL_NAME="opennmt_py__transformer"

NEW_CONFIG_FILE_NAME="${DATASET_NAME}__${MODEL_NAME}.yml"

# Create copy of config file
cp opennmt_py_transformer_config.yml $NEW_CONFIG_FILE_NAME

HARDDRIVE_DIR="/mnt/data/vplohse"
OUTPUT_DIR="${HARDDRIVE_DIR}/acr_static_analysis_results/${DATASET_NAME}/${MODEL_NAME}"

if [ -d $HARDDRIVE_DIR ]; then
    mkdir -p $OUTPUT_DIR
else
    echo "HARDDRIVE_DIR doesn't exist: $HARDDRIVE_DIR"
fi

HARDDRIVE_DIR_ESCAPED="\/mnt\/data\/vplohse"
OUTPUT_DIR_ESCAPED="${HARDDRIVE_DIR}\/acr_static_analysis_results\/${DATASET_NAME}\/${MODEL_NAME}"

# Insert correct paths
sed -i'.original' -e "s/INSERT-DATA-DIR/${DATASET_NAME}/" $NEW_CONFIG_FILE_NAME
rm -f "${NEW_CONFIG_FILE_NAME}.original"
sed -i'.original' -e "s/INSERT-OUTPUT-DIR/${OUTPUT_DIR}/" $NEW_CONFIG_FILE_NAME
rm -f "${NEW_CONFIG_FILE_NAME}.original"

VENV_DIR="venv_opennmt_py"
echo $VENV_DIR
if [ ! -d $VENV_DIR ]; then
    python3 -m venv $VENV_DIR
fi

source $VENV_DIR/bin/activate
pip install --upgrade pip
pip install -r requirements_opennmt_py.txt

# Sample all data
if [ -f ${DATASET_NAME}/vocab.txt ]; then
    rm -f ${DATASET_NAME}/vocab.txt  # Make sure vocab is updated
fi
onmt_build_vocab -config $NEW_CONFIG_FILE_NAME -n_sample 30000

onmt_train -config $NEW_CONFIG_FILE_NAME

EVAL_DIR="${DATASET_NAME}/evaluation_py_transformer"
mkdir -p $EVAL_DIR
OUTPUT="${EVAL_DIR}/inference-test.txt"
onmt_translate -model $OUTPUT_DIR -src "${DATASET_NAME}/src-test.txt" -output $OUTPUT -gpu 0
