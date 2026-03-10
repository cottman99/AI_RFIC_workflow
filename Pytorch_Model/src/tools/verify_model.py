import torch
import numpy as np
import matplotlib.pyplot as plt
import h5py
import argparse
import os
import pandas as pd
import sys
from pathlib import Path

# 从本地文件中导入我们定义的类
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dataset import EM_HDF5_Dataset
from model import AdaptableEM_CNN

def plot_s_parameters_comparison(true_s_params, pred_s_params, freqs, s_param_names, loss, save_path=None, plot_mode='combined'):
    """
    绘制真实S参数和预测S参数的对比图。
    
    参数:
        plot_mode: 'combined' - 所有S参数绘制在一张图上
                  'subplots' - 每个S参数使用独立的子图
    """
    # 设置中文字体以支持中文标签
    plt.rcParams['font.sans-serif'] = ['SimHei']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 计算S参数的数量
    num_s_params = len(s_param_names)
    
    # 频率轴
    freqs_ghz = freqs / 1e9  # 转换为GHz
    num_freqs = len(freqs_ghz)
    
    # 用于存储表格数据的列表
    table_data = []
    
    if plot_mode == 'combined':
        # 全乎绘制一张图模式
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # 绘制每个S参数的真实值和预测值
        for i in range(num_s_params):
            # 计算当前S参数在向量中的起始索引
            start_idx = i * num_freqs * 2
            
            # 真实值 - 修正为与create_hdf5.py一致的排列方式
            true_real = true_s_params[start_idx:start_idx + num_freqs]  # 实部
            true_imag = true_s_params[start_idx + num_freqs:start_idx + 2 * num_freqs]  # 虚部
            
            # 预测值 - 修正为与create_hdf5.py一致的排列方式
            pred_real = pred_s_params[start_idx:start_idx + num_freqs]  # 实部
            pred_imag = pred_s_params[start_idx + num_freqs:start_idx + 2 * num_freqs]  # 虚部
            
            # 绘制幅度对比
            true_mag = 20 * np.log10(np.abs(true_real + 1j*true_imag))
            pred_mag = 20 * np.log10(np.abs(pred_real + 1j*pred_imag))
            
            ax.plot(freqs_ghz, true_mag, label=f'真实 {s_param_names[i]}', linestyle='-', linewidth=2)
            ax.plot(freqs_ghz, pred_mag, label=f'预测 {s_param_names[i]}', linestyle='--', linewidth=2)
            
            # 为表格添加数据
            for j in range(num_freqs):
                table_data.append({
                    '频率 (GHz)': freqs_ghz[j],
                    'S参数': s_param_names[i],
                    '真实实部': true_real[j],
                    '真实虚部': true_imag[j],
                    '预测实部': pred_real[j],
                    '预测虚部': pred_imag[j]
                })
        
        # 设置图形属性
        ax.set_xlabel('频率 (GHz)')
        ax.set_ylabel('幅度 (dB)')
        ax.set_title(f'S参数对比 - 全图模式\n验证损失: {loss:.6f}')
        ax.legend()
        ax.grid(True)
        
    elif plot_mode == 'subplots':
        # 子图对比模式
        fig, axes = plt.subplots(num_s_params, 1, figsize=(12, 3*num_s_params))
        if num_s_params == 1:
            axes = [axes]  # 确保axes是可迭代的
        
        # 绘制每个S参数的真实值和预测值
        for i in range(num_s_params):
            ax = axes[i]
            
            # 计算当前S参数在向量中的起始索引
            start_idx = i * num_freqs * 2
            
            # 真实值 - 修正为与create_hdf5.py一致的排列方式
            true_real = true_s_params[start_idx:start_idx + num_freqs]  # 实部
            true_imag = true_s_params[start_idx + num_freqs:start_idx + 2 * num_freqs]  # 虚部
            
            # 预测值 - 修正为与create_hdf5.py一致的排列方式
            pred_real = pred_s_params[start_idx:start_idx + num_freqs]  # 实部
            pred_imag = pred_s_params[start_idx + num_freqs:start_idx + 2 * num_freqs]  # 虚部
            
            # 绘制幅度对比
            true_mag = 20 * np.log10(np.abs(true_real + 1j*true_imag))
            pred_mag = 20 * np.log10(np.abs(pred_real + 1j*pred_imag))
            
            ax.plot(freqs_ghz, true_mag, label=f'真实 {s_param_names[i]}', linestyle='-', linewidth=2)
            ax.plot(freqs_ghz, pred_mag, label=f'预测 {s_param_names[i]}', linestyle='--', linewidth=2)
            
            # 设置子图属性
            ax.set_xlabel('频率 (GHz)')
            ax.set_ylabel('幅度 (dB)')
            ax.set_title(f'{s_param_names[i]} - 验证损失: {loss:.6f}')
            ax.legend()
            ax.grid(True)
            
            # 为表格添加数据
            for j in range(num_freqs):
                table_data.append({
                    '频率 (GHz)': freqs_ghz[j],
                    'S参数': s_param_names[i],
                    '真实实部': true_real[j],
                    '真实虚部': true_imag[j],
                    '预测实部': pred_real[j],
                    '预测虚部': pred_imag[j]
                })
        
        # 调整子图间距
        plt.tight_layout()
    
    # 保存图形
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f'图形已保存到: {save_path}')
    
    # 创建并打印S参数对比表格
    df = pd.DataFrame(table_data)
    print(f"\nS参数具体数值对比表格 ({'全图模式' if plot_mode == 'combined' else '子图模式'}):")
    print(df.to_string(index=False))
    
    plt.show()

def verify_model(args):
    """
    验证模型并绘制S参数对比图。
    """
    # --- 1. 设备配置 ---
    device = torch.device("cpu")
    print(f"正在使用设备: {device}")

    # --- 2. 加载数据集并动态获取参数 ---
    print("正在加载数据集...")
    try:
        dataset = EM_HDF5_Dataset(args.hdf5_path)
    except FileNotFoundError:
        print(f"错误: HDF5文件未找到于 '{args.hdf5_path}'")
        return
    
    # 从数据集中动态读取输入和输出维度
    input_channels = dataset.layouts_shape[1]
    output_dim = dataset.s_params_shape[1]
    
    print("\n--- 数据集信息 ---")
    print(f"总样本数: {len(dataset)}")
    print(f"输入通道数 (层数): {input_channels}")
    print(f"输出向量维度 (S参数): {output_dim}")
    print("--------------------")

    # --- 3. 初始化模型 ---
    print("\n正在初始化模型...")
    model = AdaptableEM_CNN(output_dim=output_dim, input_channels=input_channels).to(device)
    
    # --- 4. 加载模型权重 ---
    print(f"\n正在加载模型权重从: {args.model_path}")
    try:
        model.load_state_dict(torch.load(args.model_path, map_location=device))
        model.eval()
        print("模型加载成功！")
    except FileNotFoundError:
        print(f"错误: 模型文件未找到于 '{args.model_path}'")
        return
    except Exception as e:
        print(f"加载模型时发生错误: {e}")
        return

    # --- 5. 获取指定索引的数据样本 ---
    print(f"\n正在获取索引为 {args.sample_index} 的样本...")
    try:
        layout, true_s_params = dataset[args.sample_index]
        print(f"样本获取成功！")
    except IndexError:
        print(f"错误: 索引 {args.sample_index} 超出数据集范围")
        return
    
    # 获取频率和S参数名称
    freqs = dataset.metadata['target_frequencies_hz']
    s_param_names = dataset.metadata['s_param_order']
    
    print("\n--- 样本信息 ---")
    print(f"输入张量 (Layout) 的形状: {layout.shape}")
    print(f"输出张量 (S-Params) 的形状: {true_s_params.shape}")
    print("------------------")

    # --- 6. 模型推理 ---
    print("\n正在进行模型推理...")
    with torch.no_grad():
        layout = layout.unsqueeze(0).to(device)  # 添加批次维度
        pred_s_params = model(layout).cpu().numpy().flatten()
    
    true_s_params = true_s_params.numpy()
    
    print("推理完成！")

    # --- 7. 计算验证损失 ---
    criterion = torch.nn.MSELoss()
    loss = criterion(torch.from_numpy(pred_s_params), torch.from_numpy(true_s_params)).item()
    print(f"\n验证损失 (MSE): {loss:.6f}")

    # --- 8. 绘制S参数对比图 ---
    print("\n正在绘制S参数对比图...")
    plot_s_parameters_comparison(
        true_s_params, 
        pred_s_params, 
        freqs, 
        s_param_names, 
        loss,
        save_path=args.output_image,
        plot_mode=args.plot_mode
    )

def main():
    parser = argparse.ArgumentParser(description="用于RFIC电磁仿真器的模型验证脚本")
    
    parser.add_argument('--hdf5_path', type=str, required=True, help='HDF5数据集文件的路径')
    parser.add_argument('--model_path', type=str, required=True, help='训练好的模型文件的路径')
    parser.add_argument('--sample_index', type=int, default=0, help='要验证的数据样本索引')
    parser.add_argument('--output_image', type=str, default=None, help='保存对比图的路径 (可选)')
    parser.add_argument('--plot_mode', type=str, choices=['combined', 'subplots'], default='combined', 
                       help='绘图模式: combined(全图模式) 或 subplots(子图模式), 默认: combined')
    
    args = parser.parse_args()
    
    verify_model(args)

if __name__ == '__main__':
    main()
