import os
import json
import h5py
import numpy as np
import skrf as rf
import argparse # 导入命令行参数处理库
from tqdm import tqdm
from collections import defaultdict

# =============================================================================
# 步骤 1: 升级版的转换函数 (动态处理) - 这部分保持不变
# =============================================================================

def process_layout_to_tensor(design_obj):
    """
    转换函数 (Y_input): 动态处理不同尺寸和层数的版图。
    """
    try:
        layers_order = design_obj['metadata']['layers_used']
        num_layers = len(layers_order)
        N_h, N_w = design_obj['metadata']['base_matrix_shape']
        
        padded_input = np.zeros((num_layers, N_h + 2, N_w + 2), dtype=np.float32)
        layer_map = {name: i for i, name in enumerate(layers_order)}

        for layer_name, matrix_data in design_obj['layout_matrices'].items():
            if layer_name in layer_map:
                channel_idx = layer_map[layer_name]
                padded_input[channel_idx, 1:N_h+1, 1:N_w+1] = np.array(matrix_data)

        for port in design_obj['port_definitions']:
            if port['layer'] in layer_map:
                channel_idx = layer_map[port['layer']]
                edge, index = port['edge'], port['position_index']
                
                if edge == "left": x, y = 0, index + 1
                elif edge == "right": x, y = N_w + 1, index + 1
                elif edge == "bottom": x, y = index + 1, 0
                elif edge == "top": x, y = index + 1, N_h + 1
                else: continue
                
                padded_input[channel_idx, y, x] = 1

        return padded_input

    except KeyError as e:
        print(f"处理JSON时出错：缺少键 {e}")
        return None

def process_s_params_to_vector(sNp_filepath, target_freqs):
    """
    转换函数 (Y_output): 动态处理不同端口数的S参数。
    """
    try:
        network = rf.Network(sNp_filepath)
        network_interp = network.interpolate(rf.Frequency.from_f(target_freqs, unit='hz'))
        
        n_ports = network.nports
        s_matrix_complex = network_interp.s
        
        s_vector_parts = []
        s_param_names = []

        # 动态地遍历S矩阵的上三角部分（包括对角线）
        for i in range(n_ports):
            for j in range(i, n_ports):
                param = s_matrix_complex[:, i, j]
                s_vector_parts.append(param.real)
                s_vector_parts.append(param.imag)
                s_param_names.append(f"S{i+1}{j+1}")
        
        s_vector = np.concatenate(s_vector_parts)
        
        return s_vector.astype(np.float32), s_param_names

    except Exception as e:
        print(f"处理文件 {sNp_filepath} 时出错: {e}")
        return None, None

# =============================================================================
# 步骤 2: 升级版的主执行脚本
# =============================================================================

def create_hdf5_datasets_by_group(json_dir, snp_dir, output_dir, target_freqs):
    """
    主函数，根据版图尺寸和端口数对数据进行分组，并为每个组创建独立的HDF5文件。
    """
    print("开始扫描和分组原始数据...")
    
    grouped_files = defaultdict(list)
    
    # 扫描JSON目录
    all_json_files = [os.path.join(json_dir, f) for f in os.listdir(json_dir) if f.endswith('.json')]

    for json_path in tqdm(all_json_files, desc="正在扫描文件"):
        design_id = os.path.splitext(os.path.basename(json_path))[0]
        
        # 在S参数目录中寻找对应的.sNp文件
        sNp_path = None
        for ext in ['.s2p', '.s3p', '.s4p', '.s5p', '.s6p']: # 可根据需要扩展
            potential_path = os.path.join(snp_dir, f"{design_id}{ext}")
            if os.path.exists(potential_path):
                # 验证S参数文件是否有效
                try:
                    network = rf.Network(potential_path)
                    if len(network.f) > 0 and network.s.shape[0] > 0:
                        sNp_path = potential_path
                        break
                except Exception:
                    # 跳过无效文件
                    continue
        
        if sNp_path is None:
            # print(f"警告: 找不到与 {os.path.basename(json_path)} 匹配的S参数文件，已跳过。")
            continue

        with open(json_path, 'r') as f:
            design_obj = json.load(f)
        
        shape = tuple(design_obj['metadata']['base_matrix_shape'])
        port_count = len(design_obj['port_definitions'])
        group_key = f"{port_count}port_{shape[0]}x{shape[1]}"
        
        grouped_files[group_key].append((json_path, sNp_path))

    if not grouped_files:
        print("错误：在指定目录中未找到任何匹配的 .json 和 .sNp 文件对。")
        return

    print(f"\n数据扫描完成，共找到 {len(grouped_files)} 个组: {list(grouped_files.keys())}")
    os.makedirs(output_dir, exist_ok=True)

    # 为每个组创建HDF5文件
    for group_key, file_pairs in grouped_files.items():
        print(f"\n--- 正在处理组: {group_key} ({len(file_pairs)} 个样本) ---")
        hdf5_path = os.path.join(output_dir, f"dataset_{group_key}.h5")

        sample_json_path, sample_sNp_path = file_pairs[0]
        with open(sample_json_path, 'r') as f: sample_json = json.load(f)
        sample_input_array = process_layout_to_tensor(sample_json)
        sample_output_vector, s_param_names = process_s_params_to_vector(sample_sNp_path, target_freqs)

        if sample_input_array is None or sample_output_vector is None:
            print(f"错误: 处理组 '{group_key}' 的第一个样本失败，跳过该组。")
            continue

        input_shape = sample_input_array.shape
        output_shape = sample_output_vector.shape

        with h5py.File(hdf5_path, 'w') as f:
            meta_group = f.create_group('metadata')
            meta_group.create_dataset('target_frequencies_hz', data=target_freqs)
            meta_group.create_dataset('s_param_order', data=[n.encode('utf-8') for n in s_param_names])
            meta_group.attrs['port_count'] = len(sample_json['port_definitions'])
            meta_group.attrs['base_matrix_shape'] = sample_json['metadata']['base_matrix_shape']

            layouts_dset = f.create_dataset('layouts', shape=(0, *input_shape), maxshape=(None, *input_shape), dtype='float32')
            sparams_dset = f.create_dataset('s_params', shape=(0, *output_shape), maxshape=(None, *output_shape), dtype='float32')
            
            current_size = 0
            for json_path, sNp_path in tqdm(file_pairs, desc=f"写入 {group_key}"):
                with open(json_path, 'r') as jf: design_obj = json.load(jf)
                input_array = process_layout_to_tensor(design_obj)
                output_vector, _ = process_s_params_to_vector(sNp_path, target_freqs)

                if input_array is not None and output_vector is not None:
                    layouts_dset.resize(current_size + 1, axis=0)
                    sparams_dset.resize(current_size + 1, axis=0)
                    layouts_dset[current_size] = input_array
                    sparams_dset[current_size] = output_vector
                    current_size += 1
        
        print(f"组 '{group_key}' 的HDF5数据集创建完成！路径: {hdf5_path}")

def main():
    """
    主函数，用于解析命令行参数并启动数据集创建过程。
    """
    parser = argparse.ArgumentParser(description="将JSON版图描述和S参数文件批量转换为HDF5数据集。")
    parser.add_argument(
        "--json_dir", 
        type=str, 
        required=True, 
        help="包含 layout_object.json 文件的目录路径。"
    )
    parser.add_argument(
        "--snp_dir", 
        type=str, 
        required=True, 
        help="包含 .sNp (如 .s2p) 文件的目录路径。"
    )
    parser.add_argument(
        "--output_dir", 
        type=str, 
        required=True, 
        help="用于存放生成的HDF5文件的输出目录路径。"
    )
    
    args = parser.parse_args()

    # --- 用户配置区 ---
    TARGET_FREQUENCIES_HZ = np.linspace(0e9, 6e9, 7) # 1-60 GHz, 51个点

    # 检查输入目录是否存在
    if not os.path.isdir(args.json_dir):
        print(f"错误: JSON目录 '{args.json_dir}' 不存在。")
        return
    if not os.path.isdir(args.snp_dir):
        print(f"错误: S参数目录 '{args.snp_dir}' 不存在。")
        return

    create_hdf5_datasets_by_group(args.json_dir, args.snp_dir, args.output_dir, TARGET_FREQUENCIES_HZ)


if __name__ == '__main__':
    # =============================================================================
    # 如何从命令行运行:
    # =============================================================================
    # 
    # 1. 打开您的终端 (例如 MINGW64, PowerShell, anaconda prompt 等)。
    # 2. 确保您的Python环境已激活 (例如激活一个包含 h5py 和 scikit-rf 的环境)。
    # 3. 导航到此脚本所在的目录。
    # 4. 执行以下命令，将路径替换为您的实际路径:
    #
    # python hdf5_converter_script.py ^
    #   --json_dir "f:/pfli/Code/PY_code/ADS_Python_API/AI_RFIC_workflow/parallel_version/config_examples/json_layout" ^
    #   --snp_dir "f:/pfli/Code/PY_code/ADS_Python_API/AI_RFIC_workflow/parallel_version/batch_results" ^
    #   --output_dir "./datasets"
    #
    # 注意: 在Windows CMD中，使用 `^` 进行换行。在PowerShell或Linux/MacOS中，使用 `` ` `` 或 `\`。
    # =============================================================================
    main()
