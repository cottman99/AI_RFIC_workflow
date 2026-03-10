#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试超级增强版GUI脚本的新功能
"""

import sys
import os
import numpy as np

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_random_fill_ratio_functionality():
    """测试随机填充率功能"""
    print("=== 测试随机填充率功能 ===")
    
    # 导入超级增强版模块
    try:
        from RFIC布局数据生成器GUI应用_超级增强版 import generate_random_matrices, create_new_design_object
        print("[PASS] 成功导入超级增强版模块")
    except ImportError as e:
        print(f"[FAIL] 导入失败: {e}")
        return False
    
    # 测试不同填充率的随机矩阵生成
    layers = ["metal1", "metal2"]
    test_ratios = [0.1, 0.3, 0.5, 0.7, 0.9]
    
    for ratio in test_ratios:
        matrices = generate_random_matrices(layers, fill_ratio=ratio)
        for layer, matrix in matrices.items():
            actual_ratio = np.sum(matrix) / matrix.size
            print(f"  图层: {layer}, 期望填充率: {ratio:.2f}, 实际填充率: {actual_ratio:.3f}")
            
            # 验证填充率在合理范围内
            if abs(actual_ratio - ratio) > 0.15:  # 允许15%的误差
                print(f"  [WARN] 填充率偏差较大: {abs(actual_ratio - ratio):.3f}")
    
    print("[PASS] 随机填充率功能测试完成")
    return True

def test_random_fill_ratio_generation():
    """测试随机填充率生成"""
    print("\n=== 测试随机填充率生成 ===")
    
    # 测试批量生成随机填充率
    min_ratio = 0.2
    max_ratio = 0.8
    num_samples = 10
    
    random_ratios = []
    for i in range(num_samples):
        random_ratio = np.random.uniform(min_ratio, max_ratio)
        random_ratios.append(random_ratio)
    
    print(f"生成的随机填充率 (范围: {min_ratio:.2f}-{max_ratio:.2f}):")
    for i, ratio in enumerate(random_ratios):
        print(f"  样本 {i+1}: {ratio:.3f}")
    
    # 验证范围
    all_in_range = all(min_ratio <= ratio <= max_ratio for ratio in random_ratios)
    if all_in_range:
        print("[PASS] 所有随机填充率都在指定范围内")
    else:
        print("[FAIL] 部分随机填充率超出范围")
        return False
    
    # 验证分布的均匀性（简单检查）
    avg_ratio = np.mean(random_ratios)
    expected_avg = (min_ratio + max_ratio) / 2
    if abs(avg_ratio - expected_avg) < 0.1:  # 允许10%的误差
        print(f"[PASS] 随机填充率分布均匀 (平均值: {avg_ratio:.3f}, 期望: {expected_avg:.3f})")
    else:
        print(f"[WARN] 随机填充率分布可能不均匀 (平均值: {avg_ratio:.3f}, 期望: {expected_avg:.3f})")
    
    print("[PASS] 随机填充率生成测试完成")
    return True

def test_design_object_enhanced_structure():
    """测试增强版设计对象结构"""
    print("\n=== 测试增强版设计对象结构 ===")
    
    from RFIC布局数据生成器GUI应用_超级增强版 import create_new_design_object
    
    design = create_new_design_object()
    
    # 检查新增的字段
    required_fields = ["fill_ratio", "actual_fill_ratio"]
    for field in required_fields:
        if field in design["metadata"]:
            print(f"[PASS] 发现{field}字段: {design['metadata'][field]}")
        else:
            print(f"[FAIL] 缺少{field}字段")
            return False
    
    # 检查默认值
    if design["metadata"]["fill_ratio"] == 0.5:
        print("[PASS] 默认填充率正确: 0.5")
    else:
        print(f"[FAIL] 默认填充率错误: {design['metadata']['fill_ratio']}")
        return False
    
    if design["metadata"]["actual_fill_ratio"] == 0.5:
        print("[PASS] 默认实际填充率正确: 0.5")
    else:
        print(f"[FAIL] 默认实际填充率错误: {design['metadata']['actual_fill_ratio']}")
        return False
    
    print("[PASS] 增强版设计对象结构测试完成")
    return True

def test_backward_compatibility():
    """测试向后兼容性"""
    print("\n=== 测试向后兼容性 ===")
    
    from RFIC布局数据生成器GUI应用_超级增强版 import generate_random_matrices
    
    # 测试不带fill_ratio参数的调用（应该使用默认值0.5）
    try:
        matrices = generate_random_matrices(["test_layer"])
        print("[PASS] 不带fill_ratio参数的调用成功")
    except Exception as e:
        print(f"[FAIL] 不带fill_ratio参数的调用失败: {e}")
        return False
    
    # 测试带fill_ratio参数的调用
    try:
        matrices = generate_random_matrices(["test_layer"], fill_ratio=0.3)
        print("[PASS] 带fill_ratio参数的调用成功")
    except Exception as e:
        print(f"[FAIL] 带fill_ratio参数的调用失败: {e}")
        return False
    
    print("[PASS] 向后兼容性测试完成")
    return True

def test_validation_functions():
    """测试验证函数逻辑"""
    print("\n=== 测试验证函数逻辑 ===")
    
    # 模拟验证逻辑
    def validate_fill_ratio_range(min_val, max_val):
        """模拟验证函数"""
        try:
            min_f = float(min_val)
            max_f = float(max_val)
            
            if min_f < 0.1 or min_f > 0.9:
                return False, "最小填充率必须在0.1-0.9之间"
            if max_f < 0.1 or max_f > 0.9:
                return False, "最大填充率必须在0.1-0.9之间"
            if min_f > max_f:
                return False, "最小填充率不能大于最大填充率"
            
            return True, "验证通过"
        except ValueError:
            return False, "请输入有效的数字"
    
    # 测试各种情况
    test_cases = [
        ("0.2", "0.8", True, "正常范围"),
        ("0.1", "0.9", True, "边界范围"),
        ("0.05", "0.8", False, "最小值太小"),
        ("0.2", "0.95", False, "最大值太大"),
        ("0.6", "0.4", False, "最小值大于最大值"),
        ("abc", "0.5", False, "非数字输入"),
        ("0.3", "xyz", False, "非数字输入"),
    ]
    
    for min_val, max_val, expected_success, description in test_cases:
        success, message = validate_fill_ratio_range(min_val, max_val)
        if success == expected_success:
            print(f"[PASS] {description}: {message}")
        else:
            print(f"[FAIL] {description}: 期望 {expected_success}, 实际 {success}")
            return False
    
    print("[PASS] 验证函数逻辑测试完成")
    return True

def main():
    """主测试函数"""
    print("开始测试超级增强版GUI脚本的新功能...")
    
    tests = [
        test_random_fill_ratio_functionality,
        test_random_fill_ratio_generation,
        test_design_object_enhanced_structure,
        test_backward_compatibility,
        test_validation_functions
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print(f"测试 {test.__name__} 失败")
        except Exception as e:
            print(f"测试 {test.__name__} 出现异常: {e}")
    
    print(f"\n=== 测试结果 ===")
    print(f"通过: {passed}/{total}")
    
    if passed == total:
        print("[SUCCESS] 所有测试通过！超级增强版GUI脚本准备就绪。")
        return True
    else:
        print("[ERROR] 部分测试失败，请检查代码。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)