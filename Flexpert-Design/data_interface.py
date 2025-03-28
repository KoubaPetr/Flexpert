import inspect
from torch.utils.data import DataLoader
from src.interface.data_interface import DInterface_base
import torch
import os.path as osp
from src.tools.utils import cuda
import pdb
from src.tools.utils import load_yaml_config

class MyDataLoader(DataLoader):
    def __init__(self, dataset, model_name, batch_size=64, num_workers=8, *args, **kwargs):
        super().__init__(dataset, batch_size=batch_size, num_workers=num_workers, *args, **kwargs)
        self.pretrain_device = 'cuda:0'
        self.model_name = model_name
    
    def __iter__(self):
        for batch in super().__iter__():
            # 在这里对batch进行处理
            # ...
            try:
                self.pretrain_device = f'cuda:{torch.distributed.get_rank()}'
            except:
                self.pretrain_device = 'cuda:0'

            stream = torch.cuda.Stream(
                self.pretrain_device
            )
            with torch.cuda.stream(stream):
                if self.model_name=='GVP':
                    batch = batch.cuda(non_blocking=True, device=self.pretrain_device)
                    yield batch
                else:
                    for key, val in batch.items():
                        if type(val) == torch.Tensor:
                            batch[key] = batch[key].cuda(non_blocking=True, device=self.pretrain_device)

                    # X = batch['X'].cuda(non_blocking=True, device=self.pretrain_device)
                    # S = batch['S'].cuda(non_blocking=True, device=self.pretrain_device)
                    # score = batch['score'].cuda(non_blocking=True, device=self.pretrain_device)
                    # mask = batch['mask'].cuda(non_blocking=True, device=self.pretrain_device)
                    # lengths = batch['lengths'].cuda(non_blocking=True, device=self.pretrain_device)
                    # chain_mask = batch['chain_mask'].cuda(non_blocking=True, device=self.pretrain_device)
                    # chain_encoding = batch['chain_encoding'].cuda(non_blocking=True, device=self.pretrain_device)
                
                    yield batch


class DInterface(DInterface_base):
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.save_hyperparameters()
        self.load_data_module()

    def setup(self, stage=None):
        from src.datasets.featurizer import (featurize_AF, featurize_GTrans, featurize_GVP,
                         featurize_ProteinMPNN, featurize_Inversefolding)
        if self.hparams.model_name in ['AlphaDesign', 'PiFold', 'KWDesign', 'GraphTrans', 'StructGNN', 'GCA', 'E3PiFold']:
            self.collate_fn = featurize_GTrans
        elif self.hparams.model_name == 'GVP':
            featurizer = featurize_GVP()
            self.collate_fn = featurizer.collate
        elif self.hparams.model_name == 'ProteinMPNN':
            self.collate_fn = featurize_ProteinMPNN
        elif self.hparams.model_name == 'ESMIF':
            self.collate_fn = featurize_Inversefolding
            
        # Assign train/val datasets for use in dataloaders
        if stage == 'fit' or stage is None:
            self.trainset = self.instancialize(split = 'train')
            self.valset = self.instancialize(split='valid')

        # Assign test dataset for use in dataloader(s)
        if stage == 'test' or stage is None:
            self.testset = self.instancialize(split='test')
        
        if stage in ['predict','eval']:
            self.predictset = self.instancialize(split='predict')

    def train_dataloader(self):
        return MyDataLoader(self.trainset, model_name=self.hparams.model_name, batch_size=self.batch_size, num_workers=self.hparams.num_workers, shuffle=True, prefetch_factor=8, pin_memory=True, collate_fn=self.collate_fn)

    def val_dataloader(self):
        return MyDataLoader(self.valset, model_name=self.hparams.model_name, batch_size=self.batch_size, num_workers=self.hparams.num_workers, shuffle=False, pin_memory=True, collate_fn=self.collate_fn)

    def test_dataloader(self):
        return MyDataLoader(self.testset, model_name=self.hparams.model_name, batch_size=self.batch_size, num_workers=self.hparams.num_workers, shuffle=False, pin_memory=True, collate_fn=self.collate_fn)

    def predict_dataloader(self):
        return MyDataLoader(self.predictset, model_name=self.hparams.model_name, batch_size=self.batch_size, num_workers=self.hparams.num_workers, shuffle=False, pin_memory=True, collate_fn=self.collate_fn)

    def load_data_module(self):
        
        name = self.hparams.dataset
        if name == 'AF2DB':
            from src.datasets.AF2DB_dataset_lmdb import Af2dbDataset
            self.data_module = Af2dbDataset
        
        if name == 'TS':
            from src.datasets.ts_dataset  import TSDataset
            self.data_module = TSDataset
            self.hparams['path'] = osp.join(self.hparams.data_root, 'ts')
        
        if name == 'CASP15':
            from src.datasets.casp_dataset  import CASPDataset
            self.data_module = CASPDataset
            self.hparams['path'] = osp.join(self.hparams.data_root, 'casp15')
        
        if name == 'CATH4.2':
            from src.datasets.cath_dataset import CATHDataset
            self.data_module = CATHDataset
            self.hparams['version'] = 4.2
            self.hparams['path'] = osp.join(self.hparams.data_root, 'cath4.2')
            
        if name == 'CATH4.3':
            from src.datasets.cath_dataset import CATHDataset
            self.data_module = CATHDataset
            self.hparams['version'] = 4.3
            self.hparams['path'] = osp.join(self.hparams.data_root, 'cath4.3')
        
        if name == 'MPNN':
            from src.datasets.mpnn_dataset import MPNNDataset
            self.data_module = MPNNDataset

        if name == 'FOLDSWITCHERS_1':
            from src.datasets.foldswitchers_dataset import FoldswitchersDataset
            self.data_module = FoldswitchersDataset
            self.hparams['path'] = osp.join(self.hparams.data_root, 'fold_switchers/fold_1')

        if name == 'FOLDSWITCHERS_2':
            from src.datasets.foldswitchers_dataset import FoldswitchersDataset
            self.data_module = FoldswitchersDataset
            self.hparams['path'] = osp.join(self.hparams.data_root, 'fold_switchers/fold_2')

        if name == 'PDBInference':
            from src.datasets.pdb_inference import PDBInference
            self.data_module = PDBInference
            self.hparams['path'] = osp.join(self.hparams.infer_path)

        if name == 'ATLAS_DIST_1':
            from src.datasets.atlas_dataset import AtlasDataset
            self.data_module = AtlasDataset
            self.hparams['path'] = osp.join(self.hparams.data_root, 'atlas/distant-frame-pairs_NO_SUPERPOSITION/frames_1')
        
        if name == 'ATLAS_DIST_2':
            from src.datasets.atlas_dataset import AtlasDataset
            self.data_module = AtlasDataset
            self.hparams['path'] = osp.join(self.hparams.data_root, 'atlas/distant-frame-pairs_NO_SUPERPOSITION/frames_2')
        
        if name == 'ATLAS_CLUSTER_1':
            from src.datasets.atlas_dataset import AtlasDataset
            self.data_module = AtlasDataset
            self.hparams['path'] = osp.join(self.hparams.data_root, 'atlas/cluster-representatives/frames_1')

        if name == 'ATLAS_CLUSTER_2':
            from src.datasets.atlas_dataset import AtlasDataset
            self.data_module = AtlasDataset
            self.hparams['path'] = osp.join(self.hparams.data_root, 'atlas/cluster-representatives/frames_2')

        if name == 'ATLAS_PDB':
            from src.datasets.atlas_dataset import AtlasDataset
            self.data_module = AtlasDataset
            self.hparams['path'] = osp.join(self.hparams.data_root, '../atlas_pdb_inference/')

        if name == 'ATLAS_FULL_MINIMIZED':
            from src.datasets.atlas_dataset import AtlasDataset
            self.data_module = AtlasDataset
            self.hparams['path'] = osp.join(self.hparams.data_root, '../atlas_eval_proteinmpnn/atlas_full/minimized_PDBs/pdbs/')
        
        if name == 'ATLAS_FULL_REFOLDED':
            from src.datasets.atlas_dataset import AtlasDataset
            self.data_module = AtlasDataset
            self.hparams['path'] = osp.join(self.hparams.data_root, '../atlas_eval_proteinmpnn/atlas_full/refolded_PDBs/pdbs/')
        
        if name == 'ATLAS_FULL_CRYSTAL':
            from src.datasets.atlas_dataset import AtlasDataset
            self.data_module = AtlasDataset
            self.hparams['path'] = osp.join(self.hparams.data_root, '../atlas_eval_proteinmpnn/atlas_full/crystal_PDBs/pdbs/')

        if name == 'FLEX_CATH4.3':
            from src.datasets.flex_cath_dataset import FlexCATHDataset
            self.data_module = FlexCATHDataset
            self.hparams['version'] = 4.3
            self.hparams['path'] = osp.join(self.hparams.data_root, 'cath4.3')


    def instancialize(self, **other_args):
        """ Instancialize a model using the corresponding parameters
            from self.hparams dictionary. You can also input any args
            to overwrite the corresponding value in self.kwargs.
        """
        class_args =  list(inspect.signature(self.data_module.__init__).parameters)[1:]
        inkeys = self.hparams.keys()
        args1 = {}
        for arg in class_args:
            if arg in inkeys:
                args1[arg] = self.hparams[arg]
        args1.update(other_args)

        # if self.hparams['test_engineering'] and self.hparams['use_dynamics']:
        #     args1['data_jsonl_name'] = self.hparams['test_eng_data_path']
        #elif self.hparams['use_dynamics']:
        if self.hparams['use_dynamics']:
            args1['data_jsonl_name'] = load_yaml_config('configs/ANMAwareFlexibilityProtTrans.yaml')['data_jsonl_name']
        # import pdb; pdb.set_trace()
        return self.data_module(**args1) #Here this leads to __init__ of the class dataset