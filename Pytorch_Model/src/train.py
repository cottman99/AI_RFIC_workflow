import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split
import numpy as np
import argparse
import os
import h5py
import json
import random
from datetime import datetime
from pathlib import Path

# 从本地文件中导入我们定义的类
from dataset import EM_HDF5_Dataset
from model import AdaptableEM_CNN

def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

def save_training_manifest(args, dataset, input_channels, output_dim, train_size, val_size, best_val_loss, model_path):
    manifest = {
        "created_at": datetime.now().isoformat(),
        "hdf5_path": str(Path(args.hdf5_path).resolve()),
        "model_path": str(Path(model_path).resolve()),
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "learning_rate": args.learning_rate,
        "seed": args.seed,
        "dataset_length": len(dataset),
        "train_size": train_size,
        "val_size": val_size,
        "input_channels": input_channels,
        "output_dim": output_dim,
        "metadata": {
            "port_count": int(dataset.metadata["port_count"]),
            "base_matrix_shape": [int(x) for x in dataset.metadata["base_matrix_shape"]],
            "s_param_order": list(dataset.metadata["s_param_order"]),
            "target_frequencies_hz": [float(x) for x in dataset.metadata["target_frequencies_hz"].tolist()],
        },
        "best_val_loss": best_val_loss,
    }

    manifest_path = Path(model_path).with_suffix(".json")
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"  -> 已保存训练说明到: {manifest_path}")

def train(args):
    """
    主训练函数。
    """
    # --- 1. 设备配置 ---
    # 即使是CPU版本，也保持这种写法，以实现代码的设备无关性
    set_seed(args.seed)
    device = torch.device("cpu")
    print(f"正在使用设备: {device}")

    # --- 2. 加载数据集并动态获取参数 ---
    print("正在加载数据集...")
    try:
        full_dataset = EM_HDF5_Dataset(args.hdf5_path)
    except FileNotFoundError:
        print(f"错误: HDF5文件未找到于 '{args.hdf5_path}'")
        return
    
    # 从数据集中动态读取输入和输出维度
    input_channels = full_dataset.layouts_shape[1]
    output_dim = full_dataset.s_params_shape[1]
    
    print("\n--- 数据集信息 ---")
    print(f"总样本数: {len(full_dataset)}")
    print(f"输入通道数 (层数): {input_channels}")
    print(f"输出向量维度 (S参数): {output_dim}")
    print("--------------------")

    # --- 3. 划分训练集和验证集 ---
    # 80% 用于训练, 20% 用于验证
    train_size = int(0.8 * len(full_dataset))
    val_size = len(full_dataset) - train_size
    split_generator = torch.Generator().manual_seed(args.seed)
    train_dataset, val_dataset = random_split(full_dataset, [train_size, val_size], generator=split_generator)

    print(f"训练集大小: {len(train_dataset)}")
    print(f"验证集大小: {len(val_dataset)}")

    # 创建DataLoader
    train_loader = DataLoader(dataset=train_dataset, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(dataset=val_dataset, batch_size=args.batch_size, shuffle=False)

    # --- 4. 初始化模型、损失函数和优化器 ---
    print("\n正在初始化模型...")
    model = AdaptableEM_CNN(output_dim=output_dim, input_channels=input_channels).to(device)
    
    criterion = nn.MSELoss()  # 均方误差损失，适用于回归任务
    optimizer = optim.Adam(model.parameters(), lr=args.learning_rate)
    
    # 学习率调度器：每隔N个epoch，学习率乘以gamma
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=50, gamma=0.1)

    # --- 5. 训练循环 ---
    best_val_loss = float('inf')
    os.makedirs(args.output_dir, exist_ok=True)
    model_path = os.path.join(args.output_dir, args.checkpoint_name)

    print("\n开始训练...")
    for epoch in range(args.epochs):
        # --- 训练阶段 ---
        model.train()
        train_loss = 0.0
        for layouts, s_params in train_loader:
            layouts, s_params = layouts.to(device), s_params.to(device)

            # 前向传播
            predictions = model(layouts)
            loss = criterion(predictions, s_params)

            # 反向传播和优化
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            train_loss += loss.item()

        # --- 验证阶段 ---
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for layouts, s_params in val_loader:
                layouts, s_params = layouts.to(device), s_params.to(device)
                predictions = model(layouts)
                loss = criterion(predictions, s_params)
                val_loss += loss.item()

        # 计算平均损失
        avg_train_loss = train_loss / len(train_loader)
        avg_val_loss = val_loss / len(val_loader)

        print(f"Epoch [{epoch+1}/{args.epochs}], 训练损失: {avg_train_loss:.6f}, 验证损失: {avg_val_loss:.6f}")

        # 更新学习率
        scheduler.step()

        # --- 6. 保存最佳模型 ---
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            torch.save(model.state_dict(), model_path)
            save_training_manifest(
                args=args,
                dataset=full_dataset,
                input_channels=input_channels,
                output_dim=output_dim,
                train_size=train_size,
                val_size=val_size,
                best_val_loss=best_val_loss,
                model_path=model_path,
            )
            print(f"  -> 验证损失降低，已保存最佳模型到: {model_path}")

    print("\n训练完成！")

def main():
    parser = argparse.ArgumentParser(description="用于RFIC电磁仿真器的PyTorch训练脚本")
    
    parser.add_argument('--hdf5_path', type=str, required=True, help='HDF5数据集文件的路径')
    parser.add_argument('--epochs', type=int, default=200, help='训练的总轮数')
    parser.add_argument('--batch_size', type=int, default=32, help='每批次训练的样本数量')
    parser.add_argument('--learning_rate', type=float, default=1e-3, help='优化器的学习率')
    parser.add_argument('--output_dir', type=str, default='../models', help='保存训练好的模型文件的目录')
    
    parser.add_argument('--checkpoint_name', type=str, default='best_model_2ch_2port_16x16.pth', help='checkpoint file name')
    parser.add_argument('--seed', type=int, default=42, help='random seed')

    args = parser.parse_args()
    
    train(args)

if __name__ == '__main__':
    main()
