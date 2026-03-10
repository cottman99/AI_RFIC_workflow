import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import torch
import numpy as np
import matplotlib.pyplot as plt
import h5py
import os
import pandas as pd
from pathlib import Path
import sys

# 从本地文件中导入我们定义的类
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dataset import EM_HDF5_Dataset
from model import AdaptableEM_CNN

class ModelVerifierGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("RFIC模型验证工具")
        self.root.geometry("600x500")
        
        # 变量初始化
        self.hdf5_path = tk.StringVar()
        self.model_path = tk.StringVar()
        self.sample_index = tk.IntVar(value=0)
        self.plot_mode = tk.StringVar(value="combined")
        self.output_image = tk.StringVar()
        
        self.setup_ui()
        
    def setup_ui(self):
        """设置用户界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # HDF5文件选择
        ttk.Label(main_frame, text="HDF5数据集文件:").grid(row=0, column=0, sticky=tk.W, pady=5)
        hdf5_frame = ttk.Frame(main_frame)
        hdf5_frame.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Entry(hdf5_frame, textvariable=self.hdf5_path, width=50).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(hdf5_frame, text="浏览...", command=self.select_hdf5).pack(side=tk.LEFT)
        
        # 模型文件选择
        ttk.Label(main_frame, text="模型文件:").grid(row=1, column=0, sticky=tk.W, pady=5)
        model_frame = ttk.Frame(main_frame)
        model_frame.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Entry(model_frame, textvariable=self.model_path, width=50).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(model_frame, text="浏览...", command=self.select_model).pack(side=tk.LEFT)
        
        # 样本索引
        ttk.Label(main_frame, text="样本索引:").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.sample_index, width=10).grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # 绘图模式选择
        ttk.Label(main_frame, text="绘图模式:").grid(row=3, column=0, sticky=tk.W, pady=5)
        mode_frame = ttk.Frame(main_frame)
        mode_frame.grid(row=3, column=1, columnspan=2, sticky=tk.W, pady=5)
        
        ttk.Radiobutton(mode_frame, text="全图模式", variable=self.plot_mode, value="combined").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(mode_frame, text="子图模式", variable=self.plot_mode, value="subplots").pack(side=tk.LEFT)
        
        # 输出图片路径
        ttk.Label(main_frame, text="保存图片(可选):").grid(row=4, column=0, sticky=tk.W, pady=5)
        output_frame = ttk.Frame(main_frame)
        output_frame.grid(row=4, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Entry(output_frame, textvariable=self.output_image, width=50).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(output_frame, text="浏览...", command=self.select_output).pack(side=tk.LEFT)
        
        # 验证按钮
        ttk.Button(main_frame, text="开始验证", command=self.start_verification).grid(row=5, column=1, pady=20)
        
        # 状态显示
        self.status_text = tk.Text(main_frame, height=10, width=70)
        self.status_text.grid(row=6, column=0, columnspan=3, pady=10)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.status_text.yview)
        scrollbar.grid(row=6, column=3, sticky=(tk.N, tk.S))
        self.status_text.configure(yscrollcommand=scrollbar.set)
        
        # 配置列权重
        main_frame.columnconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
    def select_hdf5(self):
        """选择HDF5文件"""
        filename = filedialog.askopenfilename(
            title="选择HDF5数据集文件",
            filetypes=[("HDF5文件", "*.h5 *.hdf5"), ("所有文件", "*.*")]
        )
        if filename:
            self.hdf5_path.set(filename)
            
    def select_model(self):
        """选择模型文件"""
        filename = filedialog.askopenfilename(
            title="选择模型文件",
            filetypes=[("PyTorch模型", "*.pth *.pt"), ("所有文件", "*.*")]
        )
        if filename:
            self.model_path.set(filename)
            
    def select_output(self):
        """选择输出图片路径"""
        filename = filedialog.asksaveasfilename(
            title="保存对比图",
            defaultextension=".png",
            filetypes=[("PNG图片", "*.png"), ("JPG图片", "*.jpg"), ("所有文件", "*.*")]
        )
        if filename:
            self.output_image.set(filename)
            
    def log_message(self, message):
        """记录消息到状态文本框"""
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
        self.root.update()
        
    def start_verification(self):
        """开始验证过程"""
        # 验证输入
        if not self.hdf5_path.get():
            messagebox.showerror("错误", "请选择HDF5数据集文件")
            return
            
        if not self.model_path.get():
            messagebox.showerror("错误", "请选择模型文件")
            return
            
        try:
            sample_idx = int(self.sample_index.get())
        except ValueError:
            messagebox.showerror("错误", "样本索引必须是整数")
            return
            
        # 清空状态文本框
        self.status_text.delete(1.0, tk.END)
        
        # 禁用按钮
        self.root.config(cursor="watch")
        
        try:
            self.verify_model()
        except Exception as e:
            messagebox.showerror("验证失败", str(e))
        finally:
            # 恢复按钮
            self.root.config(cursor="")
            
    def verify_model(self):
        """验证模型的主要逻辑"""
        # --- 1. 设备配置 ---
        device = torch.device("cpu")
        self.log_message(f"正在使用设备: {device}")

        # --- 2. 加载数据集并动态获取参数 ---
        self.log_message("正在加载数据集...")
        try:
            dataset = EM_HDF5_Dataset(self.hdf5_path.get())
        except FileNotFoundError:
            raise FileNotFoundError(f"HDF5文件未找到于 '{self.hdf5_path.get()}'")
        except Exception as e:
            raise Exception(f"加载数据集失败: {e}")
        
        # 从数据集中动态读取输入和输出维度
        input_channels = dataset.layouts_shape[1]
        output_dim = dataset.s_params_shape[1]
        
        self.log_message(f"\n--- 数据集信息 ---")
        self.log_message(f"总样本数: {len(dataset)}")
        self.log_message(f"输入通道数 (层数): {input_channels}")
        self.log_message(f"输出向量维度 (S参数): {output_dim}")
        self.log_message("--------------------")

        # --- 3. 初始化模型 ---
        self.log_message("\n正在初始化模型...")
        model = AdaptableEM_CNN(output_dim=output_dim, input_channels=input_channels).to(device)
        
        # --- 4. 加载模型权重 ---
        self.log_message(f"\n正在加载模型权重从: {self.model_path.get()}")
        try:
            model.load_state_dict(torch.load(self.model_path.get(), map_location=device))
            model.eval()
            self.log_message("模型加载成功！")
        except FileNotFoundError:
            raise FileNotFoundError(f"模型文件未找到于 '{self.model_path.get()}'")
        except Exception as e:
            raise Exception(f"加载模型时发生错误: {e}")

        # --- 5. 获取指定索引的数据样本 ---
        sample_idx = int(self.sample_index.get())
        self.log_message(f"\n正在获取索引为 {sample_idx} 的样本...")
        try:
            layout, true_s_params = dataset[sample_idx]
            self.log_message("样本获取成功！")
        except IndexError:
            raise IndexError(f"索引 {sample_idx} 超出数据集范围")
        
        # 获取频率和S参数名称
        freqs = dataset.metadata['target_frequencies_hz']
        s_param_names = dataset.metadata['s_param_order']
        
        self.log_message(f"\n--- 样本信息 ---")
        self.log_message(f"输入张量 (Layout) 的形状: {layout.shape}")
        self.log_message(f"输出张量 (S-Params) 的形状: {true_s_params.shape}")
        self.log_message("------------------")

        # --- 6. 模型推理 ---
        self.log_message("\n正在进行模型推理...")
        with torch.no_grad():
            layout = layout.unsqueeze(0).to(device)  # 添加批次维度
            pred_s_params = model(layout).cpu().numpy().flatten()
        
        true_s_params = true_s_params.numpy()
        
        self.log_message("推理完成！")

        # --- 7. 计算验证损失 ---
        criterion = torch.nn.MSELoss()
        loss = criterion(torch.from_numpy(pred_s_params), torch.from_numpy(true_s_params)).item()
        self.log_message(f"\n验证损失 (MSE): {loss:.6f}")

        # --- 8. 绘制S参数对比图 ---
        self.log_message("\n正在绘制S参数对比图...")
        
        try:
            self.plot_s_parameters_comparison(
                true_s_params, 
                pred_s_params, 
                freqs, 
                s_param_names, 
                loss,
                save_path=self.output_image.get() if self.output_image.get() else None,
                plot_mode=self.plot_mode.get()
            )
            self.log_message("图形绘制完成！")
            
            if self.output_image.get():
                self.log_message(f"图形已保存到: {self.output_image.get()}")
                
        except Exception as e:
            self.log_message(f"绘图失败: {e}")
            
    def plot_s_parameters_comparison(self, true_s_params, pred_s_params, freqs, s_param_names, loss, save_path=None, plot_mode='combined'):
        """绘制S参数对比图"""
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False
        
        num_s_params = len(s_param_names)
        freqs_ghz = freqs / 1e9
        num_freqs = len(freqs_ghz)
        
        if plot_mode == 'combined':
            fig, ax = plt.subplots(figsize=(12, 8))
            
            for i in range(num_s_params):
                start_idx = i * num_freqs * 2
                true_real = true_s_params[start_idx:start_idx + num_freqs]
                true_imag = true_s_params[start_idx + num_freqs:start_idx + 2 * num_freqs]
                pred_real = pred_s_params[start_idx:start_idx + num_freqs]
                pred_imag = pred_s_params[start_idx + num_freqs:start_idx + 2 * num_freqs]
                
                true_mag = 20 * np.log10(np.abs(true_real + 1j*true_imag))
                pred_mag = 20 * np.log10(np.abs(pred_real + 1j*pred_imag))
                
                ax.plot(freqs_ghz, true_mag, label=f'真实 {s_param_names[i]}', linestyle='-', linewidth=2)
                ax.plot(freqs_ghz, pred_mag, label=f'预测 {s_param_names[i]}', linestyle='--', linewidth=2)
            
            ax.set_xlabel('频率 (GHz)')
            ax.set_ylabel('幅度 (dB)')
            ax.set_title(f'S参数对比 - 全图模式\n验证损失: {loss:.6f}')
            ax.legend()
            ax.grid(True)
            
        elif plot_mode == 'subplots':
            fig, axes = plt.subplots(num_s_params, 1, figsize=(12, 3*num_s_params))
            if num_s_params == 1:
                axes = [axes]
            
            for i in range(num_s_params):
                ax = axes[i]
                start_idx = i * num_freqs * 2
                true_real = true_s_params[start_idx:start_idx + num_freqs]
                true_imag = true_s_params[start_idx + num_freqs:start_idx + 2 * num_freqs]
                pred_real = pred_s_params[start_idx:start_idx + num_freqs]
                pred_imag = pred_s_params[start_idx + num_freqs:start_idx + 2 * num_freqs]
                
                true_mag = 20 * np.log10(np.abs(true_real + 1j*true_imag))
                pred_mag = 20 * np.log10(np.abs(pred_real + 1j*pred_imag))
                
                ax.plot(freqs_ghz, true_mag, label=f'真实 {s_param_names[i]}', linestyle='-', linewidth=2)
                ax.plot(freqs_ghz, pred_mag, label=f'预测 {s_param_names[i]}', linestyle='--', linewidth=2)
                
                ax.set_xlabel('频率 (GHz)')
                ax.set_ylabel('幅度 (dB)')
                ax.set_title(f'{s_param_names[i]} - 验证损失: {loss:.6f}')
                ax.legend()
                ax.grid(True)
            
            plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()

def main():
    root = tk.Tk()
    app = ModelVerifierGUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()
