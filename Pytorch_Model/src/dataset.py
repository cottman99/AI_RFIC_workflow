import torch
from torch.utils.data import Dataset
import h5py
import numpy as np

class EM_HDF5_Dataset(Dataset):
    """
    一个自定义的PyTorch Dataset类，用于高效地从HDF5文件中加载RFIC版图数据。
    这个类支持“懒加载”(lazy-loading)，只在需要时才从磁盘读取数据，
    非常适合处理远大于内存的大型数据集。
    """
    def __init__(self, h5_path):
        """
        初始化数据集。
        Args:
            h5_path (string): HDF5文件的路径。
        """
        self.h5_path = h5_path
        
        # 在主进程中预先读取元数据
        with h5py.File(self.h5_path, 'r') as f:
            self.metadata = {
                'port_count': f['metadata'].attrs['port_count'],
                'base_matrix_shape': tuple(f['metadata'].attrs['base_matrix_shape']),
                's_param_order': [s.decode('utf-8') for s in f['metadata']['s_param_order'][:]],
                'target_frequencies_hz': f['metadata']['target_frequencies_hz'][:]
            }
            # 预先获取数据集的形状信息
            self.layouts_shape = f['layouts'].shape
            self.s_params_shape = f['s_params'].shape

        # 将文件句柄保持为None，在需要时（在每个worker中）重新打开
        self.h5_file = None
        self.layouts = None
        self.s_params = None

    def __len__(self):
        """返回数据集中的样本总数。"""
        return self.layouts_shape[0]

    def __getitem__(self, idx):
        """
        根据索引获取一个样本。
        这是真正从磁盘读取数据的地方，并且只读取idx对应的那一条。
        """
        # 为多进程DataLoader优化：每个worker进程都打开自己的文件句柄
        if self.h5_file is None:
            self.h5_file = h5py.File(self.h5_path, 'r')
            self.layouts = self.h5_file['layouts']
            self.s_params = self.h5_file['s_params']

        # 获取数据
        layout = self.layouts[idx]
        s_param = self.s_params[idx]
        
        # 转换为PyTorch Tensor
        # Numpy数组默认是float64，需要转换为float32 (torch.float)
        return torch.from_numpy(layout.astype(np.float32)), torch.from_numpy(s_param.astype(np.float32))

if __name__ == '__main__':
    # 这是一个简单的测试，用于验证Dataset类是否能正常工作
    # 请将 'path/to/your/dataset.h5' 替换为您的实际文件路径
    try:
        test_dataset = EM_HDF5_Dataset('../data/dataset_2port_16x16.h5')
        print(f"数据集加载成功！共找到 {len(test_dataset)} 个样本。")
        
        # 打印元数据
        print("\n--- 数据集元数据 ---")
        for key, value in test_dataset.metadata.items():
            print(f"{key}: {value}")
        
        # 获取并打印第一个样本
        layout_tensor, s_param_tensor = test_dataset[0]
        print("\n--- 第一个样本信息 ---")
        print(f"输入张量 (Layout) 的形状: {layout_tensor.shape}")
        print(f"输入张量的数据类型: {layout_tensor.dtype}")
        print(f"输出张量 (S-Params) 的形状: {s_param_tensor.shape}")
        print(f"输出张量的数据类型: {s_param_tensor.dtype}")

    except FileNotFoundError:
        print("\n错误: 测试用HDF5文件未找到。")
        print("请确保在 '../data/' 目录下有名为 'dataset_2port_16x16.h5' 的文件。")
    except Exception as e:
        print(f"发生错误: {e}")
