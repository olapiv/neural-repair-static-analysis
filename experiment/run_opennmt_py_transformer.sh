#!/bin/bash

if [ -z "$1" ]; then
    exit 1
fi

# Any of imitate__100_tokens__standard__3, imitate__150_tokens__camelcase__3, etc.
DATASET_NAME=$1

MODEL_NAME="opennmt_py__transformer"

NEW_CONFIG_FILE_NAME="${DATASET_NAME}__${MODEL_NAME}.yml"

# Create copy of config file
cp opennmt_py_transformer_config.yml $NEW_CONFIG_FILE_NAME

RELATIVE_OUTPUT_DIR="${DATASET_NAME}\/${MODEL_NAME}"

# Insert correct paths
sed -i'.original' -e "s/INSERT-DATA-DIR/${DATASET_NAME}/" $NEW_CONFIG_FILE_NAME
rm -f "${NEW_CONFIG_FILE_NAME}.original"
sed -i'.original' -e "s/INSERT-OUTPUT-DIR/${RELATIVE_OUTPUT_DIR}/" $NEW_CONFIG_FILE_NAME
rm -f "${NEW_CONFIG_FILE_NAME}.original"

VENV_DIR="venv_opennmt_py"
echo $VENV_DIR
if [ ! -d $VENV_DIR ]; then
    virtualenv $VENV_DIR
fi

source $VENV_DIR/bin/activate
pip install --upgrade pip
pip install -r requirements_opennmt_py.txt

# Sample all data
onmt_build_vocab -config $NEW_CONFIG_FILE_NAME -n_sample 30000
