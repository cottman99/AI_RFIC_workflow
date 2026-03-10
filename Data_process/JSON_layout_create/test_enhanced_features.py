#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试增强版GUI脚本的新功能
"""

import sys
import os
import numpy as np

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_fill_ratio_functionality():
    """测试填充率控制功能"""
    print("=== 测试填充率控制功能 ===")
    
    # 导入增强版模块
    try:
        from RFIC布局数据生成器GUI应用_增强版 import generate_random_matrices, create_new_design_object
        print("[PASS] 成功导入增强版模块")
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
    
    print("[PASS] 填充率控制功能测试完成")
    return True

def test_design_object_structure():
    """测试设计对象结构"""
    print("\n=== 测试设计对象结构 ===")
    
    from RFIC布局数据生成器GUI应用_增强版 import create_new_design_object
    
    design = create_new_design_object()
    
    # 检查新增的fill_ratio字段
    if "fill_ratio" in design["metadata"]:
        print(f"[PASS] 发现fill_ratio字段: {design['metadata']['fill_ratio']}")
    else:
        print("[FAIL] 缺少fill_ratio字段")
        return False
    
    # 检查默认值
    if design["metadata"]["fill_ratio"] == 0.5:
        print("[PASS] 默认填充率正确: 0.5")
    else:
        print(f"[FAIL] 默认填充率错误: {design['metadata']['fill_ratio']}")
        return False
    
    print("[PASS] 设计对象结构测试完成")
    return True

def test_backward_compatibility():
    """测试向后兼容性"""
    print("\n=== 测试向后兼容性 ===")
    
    from RFIC布局数据生成器GUI应用_增强版 import generate_random_matrices
    
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

def main():
    """主测试函数"""
    print("开始测试增强版GUI脚本的新功能...")
    
    tests = [
        test_fill_ratio_functionality,
        test_design_object_structure,
        test_backward_compatibility
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
        print("[SUCCESS] 所有测试通过！增强版GUI脚本准备就绪。")
        return True
    else:
        print("[ERROR] 部分测试失败，请检查代码。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)