import opennmt

config = {
    "model_dir": "/data/wmt-ende/checkpoints/",
    "data": {
        "source_vocabulary": "/data/wmt-ende/joint-vocab.txt",
        "target_vocabulary": "/data/wmt-ende/joint-vocab.txt",
        "train_features_file": "/data/wmt-ende/train.en",
        "train_labels_file": "/data/wmt-ende/train.de",
        "eval_features_file": "/data/wmt-ende/valid.en",
        "eval_labels_file": "/data/wmt-ende/valid.de",
    }
}

model = opennmt.models.TransformerBase()
runner = opennmt.Runner(model, config, auto_config=True)
runner.train(num_devices=2, with_eval=True)

decoder = opennmt.decoders.SelfAttentionDecoder(num_layers=6, vocab_size=32000)

initial_state = decoder.initial_state(
    memory=memory, memory_sequence_length=memory_sequence_length
)

batch_size = tf.shape(memory)[0]
start_ids = tf.fill([batch_size], opennmt.START_OF_SENTENCE_ID)

decoding_result = decoder.dynamic_decode(
    target_embedding,
    start_ids=start_ids,
    initial_state=initial_state,
    decoding_strategy=opennmt.utils.BeamSearch(4),
)