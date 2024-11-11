from data.scripts.data_utils import parse_PDB
from utils.utils import ClassConfig, DataCollatorForTokenRegression
from models.T5_encoder_per_token import PT5_classification_model
from data.scripts.get_enm_fluctuations_for_dataset import get_fluctuation_for_json_dict
import argparse
import os
import yaml
import torch

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_file", type=str, required=True, help="Input file")
    parser.add_argument("--modality", type=str, required=True, help="Indicate 'Seq' or '3D' to use Flexpert-Seq or Flexpert-3D?")
    args = parser.parse_args()

    args.modality = args.modality.upper()
    filename, suffix = os.path.splitext(args.input_file)
        
    if args.modality not in ["SEQ", "3D"]:
        raise ValueError("Modality must be either Seq or 3D")

    if suffix == ".fasta":
        if args.modality == "3D":
            raise ValueError("Flexpert-3D needs the structure, fasta is not enough")
        raise NotImplementedError("JSONL file is not supported yet")
    elif suffix == ".pdb":
        parsed_name = filename.split('/')[-1].split('_')
        if len(parsed_name[0]) != 4 or len(parsed_name[1]) != 1 or not parsed_name[1].isalpha():
            raise ValueError("PDB file name is expected to be in the format of 'name_chain.pdb', e.g.: 1BUI_C.pdb")
        _name= parsed_name[0]
        _chain = parsed_name[1]
        parsed_pdb = parse_PDB(args.input_file,name=_name, input_chain_list=[_chain])[0]
        backbone, sequence = parsed_pdb['coords_chain_{}'.format(_chain)], parsed_pdb['seq_chain_{}'.format(_chain)]
        backbones = [backbone]
        sequences = [sequence]
    elif suffix == ".jsonl":
        raise NotImplementedError("JSONL file is not supported yet")
    else:
        raise ValueError("Input file must be a fasta, pdb or jsonl file")

    #load model Seq / 3D and the tokenizer

    ### Set environment variables
    env_config = yaml.load(open('configs/env_config.yaml', 'r'), Loader=yaml.FullLoader)
    # Set folder for huggingface cache
    os.environ['HF_HOME'] = env_config['huggingface']['HF_HOME']
    # Set gpu device
    os.environ["CUDA_VISIBLE_DEVICES"]= env_config['gpus']['cuda_visible_device']



    config = yaml.load(open('configs/train_config.yaml', 'r'), Loader=yaml.FullLoader)
    class_config=ClassConfig(config)
    class_config.adaptor_architecture = 'no-adaptor' if args.modality == 'SEQ' else 'conv'
    model, tokenizer = PT5_classification_model(half_precision=config['mixed_precision'], class_config=class_config)

    model.to(config['inference_args']['device'])
    if args.modality == 'SEQ':
        raise NotImplementedError("Seq model is not supported yet - paste it in once retrained")
    elif args.modality == '3D':
        state_dict = torch.load(config['inference_args']['3d_model_path'], map_location=config['inference_args']['device'])
        model.load_state_dict(state_dict, strict=False)
    model.eval()

    #TODO: get ENM for the backbones
    flucts_list = []
    tokenized_seqs = []
    attention_masks = []
    for backbone, sequence in zip(backbones, sequences):
        _dict = {'coords': backbone, 'seq': sequence}
        flucts, _ = get_fluctuation_for_json_dict(_dict, enm_type = config['inference_args']['enm_type'])
        flucts = flucts.tolist()
        flucts.append(0.0) #To match the special token for the sequence
        flucts = torch.tensor(flucts)
        flucts_list.append(flucts.unsqueeze(0))
        
        tokenizer_out = tokenizer(' '.join(sequence), add_special_tokens=True, return_tensors='pt')
        tokenized_seq, attention_mask = tokenizer_out['input_ids'], tokenizer_out['attention_mask']
        tokenized_seqs.append(tokenized_seq)
        attention_masks.append(attention_mask)


    import pdb; pdb.set_trace()

    #TODO: START FROM HERE collate the batch using the flucts_list, tokenized_seqs and attention_masks
    
    # Create a features dict that matches training format
    features = {
        'input_ids': tokenized['input_ids'],
        'attention_mask': tokenized['attention_mask'],
        'enm_vals': flucts_list[0]  # Assuming single sequence prediction
    }

    # Use the data collator to process the input
    data_collator = DataCollatorForTokenRegression(tokenizer)
    batch = data_collator([features])  # Wrap in list since collator expects batch

    # Move to device
    batch = {k: v.to(config['inference_args']['device']) for k, v in batch.items()}

    # Predict
    with torch.no_grad():
        outputs = model(**batch)
        predictions = outputs.logits

    #TODO: predict the batches    

    # #predict a single sequence
    # seq_tokens = tokenizer.encode(' '.join(sequence), add_special_tokens=True)
    # seq_tokens = torch.tensor(seq_tokens).unsqueeze(0).to(config['inference_args']['device'])
    # with torch.no_grad():
    #     output = model(seq_tokens)
    # import pdb; pdb.set_trace()