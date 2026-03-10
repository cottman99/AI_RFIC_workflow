# 项目深度体检报告

本报告基于静态分析生成，本轮未运行项目代码。目标是为仓库整理、回忆项目结构、准备 GitHub 发布提供清晰基线。

## 1. 总结结论

项目已经具备完整研究链路：

- 像素版图模板生成
- ADS / RFPro 自动建模与仿真
- 仿真结果导出与归档
- HDF5 数据集构建
- PyTorch CNN 训练与验证

但当前仓库状态仍属于“研究原型可读，公开发布前需治理”。阻塞项主要集中在以下几类：

- 发布材料缺失：根 `README`、依赖清单、许可说明不足
- 环境耦合过强：硬编码本机 ADS / PDK 路径
- 仓库污染：临时目录、仿真产物、日志、缓存混入
- 资产过大：模型权重大于 GitHub 普通 Git 单文件限制
- 文本质量问题：中文文档和注释存在明显乱码

## 2. 仓库结构诊断

### 2.1 Data_process

`Data_process/JSON_layout_create/`

- 负责像素版图 JSON 模板的创建、编辑、导入导出和数据增强
- 同时保留了普通版、增强版、超级增强版 3 套 GUI 脚本
- 包含 `JSON_layout_data/` 样例数据
- 包含一个明显的临时运行目录 `tmp/`

`Data_process/HDF5_create/`

- 负责将 JSON 布局和 `.sNp` 仿真结果对齐为 HDF5
- 核心脚本职责单一，适合保留
- 自带 `utils/verify_hdf5.py` 和 `utils/validate_snp_files.py`，对后续数据治理有帮助

### 2.2 serial_version

- 串行 ADS 工作流实现
- 同时包含 GUI、CLI、worker、批处理器和 Windows 编码修复脚本
- 优点是文档齐全，`docs/` 中有 8 份较系统的内部技术文档
- 缺点是历史兼容层和环境修补内容较多，容易干扰发布主线

### 2.3 parallel_version

- 更清晰的批处理架构
- 把工作流拆分成：
  - workspace / library 创建
  - design 创建
  - simulation 执行
  - report 聚合
- 最适合作为未来公开仓库的主线实现

### 2.4 Pytorch_Model

- 包含数据集加载、模型结构、训练脚本和验证工具
- 职责清楚，适合作为机器学习子模块保留
- 但当前混入了训练权重和数据文件，需要重新定义发布策略

## 3. 适合发布的内容

建议优先保留：

- `parallel_version/` 的核心实现和配置模板
- `Data_process/HDF5_create/` 的数据转换链
- `Pytorch_Model/src/` 与 `Pytorch_Model/src/tools/`
- `Data_process/JSON_layout_create/` 中最终确定的一个 GUI 主版本
- 精选少量 JSON 样例

建议作为文档素材保留，但不应原样作为主入口：

- `serial_version/docs/`
- `serial_version/` 中的早期 GUI / CLI / worker 设计

## 4. 不适合直接发布的内容

### 4.1 临时与缓存

明确不应发布：

- `.claude/`
- `__pycache__/`
- 任意 `tmp/`
- `batch_processor.log` 之类日志
- ADS / RFPro 运行中间产物

当前仓库已看到典型样本：

- `Data_process/JSON_layout_create/tmp/`
- `parallel_version/tmp/`
- 各级 `__pycache__/`

### 4.2 大文件与派生产物

当前存在应重新处理的二进制资产：

- `Pytorch_Model/models/best_model_legacy_1ch_2port_16x16_pre20260310.pth`
  - 约 295.74 MB
  - 本地 legacy 资产，已不再作为当前模型命名
- `Pytorch_Model/data/dataset_2port_16x16.h5`
- `Data_process/HDF5_create/hdf5_data/dataset_2port_16x16.h5`

建议策略：

- 若仅作为示例，改成下载链接或发布资产
- 若必须纳入版本控制，单独评估 Git LFS
- 对外公开仓库默认不直接提交训练权重和完整数据集

### 4.3 内部协作和个人环境文件

不建议公开：

- `serial_version/CLAUDE.md`
- `parallel_version/CLAUDE.md`
- `parallel_version/tmp/plan1.md`

## 5. 结构一致性问题

本轮抽查了全部非 `tmp/` 的 `design_*.json` 文件。

结果：

- 共发现 121 个设计 JSON
- 其中 120 个结构一致
- 1 个样例存在明显元数据不一致

问题样例：

- `serial_version/design_20250728_164254_882780.json`

具体表现：

- `metadata.layers_used` 写的是 `M1, M2`
- `layout_matrices` 实际键是 `cond, cond2`
- `port_definitions` 中端口层又使用 `M1, M2`

这个文件不应作为公开样例，也不应作为 schema 说明参考。

## 6. 环境与路径耦合问题

仓库中曾存在大量 ADS / PDK 绝对路径示例或默认值，例如：

- `C:\Path\To\ADS\...`
- `D:\Path\To\Keysight\ADS\...`
- `C:\Path\To\AI_RFIC_workflow\...`

这类路径出现在：

- `serial_version/subprocess_cli.py`
- `parallel_version/subprocess_cli_parallel.py`
- `serial_version/batch_config.json`
- `parallel_version/config_examples/batch_config_pdk.json`
- 多份内部文档

影响：

- 公开用户无法直接复用
- 文档会暴露明显的个人环境痕迹
- 让“样例配置”和“实际可移植配置”混淆

建议：

- 保留模板结构
- 全部替换为占位符路径
- 用环境变量或配置文件注入真实路径

## 7. 编码与文档质量问题

当前仓库有一类高优先级问题：中文文本在多个文件中表现为乱码。

典型位置：

- `Pytorch_Model/README.md`
- `Pytorch_Model/src/train.py`
- `Pytorch_Model/src/dataset.py`
- `Pytorch_Model/src/model.py`
- `Pytorch_Model/src/tools/README.md`
- `Data_process/JSON_layout_create/layout_generator_gui_guide.md`
- `Data_process/JSON_layout_create/legacy_variants/test_enhanced_features.py`
- `Data_process/JSON_layout_create/legacy_variants/test_super_enhanced_features.py`

这会直接影响：

- GitHub 可读性
- 项目可信度
- 后续维护成本

建议将“文本编码统一修复”列为发布前最高优先级之一。

## 8. 文档现状评价

优点：

- `serial_version/docs/` 已有较完整的架构、协议、错误处理和可视化说明
- 对回忆项目设计非常有帮助

问题：

- 文档数量多，但不适合作为公开项目首页
- 内容偏内部实现讲解，缺少仓库级导航
- 存在大量示例路径和环境假设

建议：

- 保留这些文档作为技术参考
- 重新提炼为根级文档体系

## 9. 发布策略建议

建议采用“收敛主线”的方式发布：

### 9.1 主线

以 `parallel_version/` 为 ADS 自动化执行主线。

### 9.2 数据链

保留 `Data_process/HDF5_create/`。

### 9.3 模型链

保留 `Pytorch_Model/src/`，去除默认大权重和大数据。

### 9.4 版图模板工具

在 `Data_process/JSON_layout_create/` 的 3 个 GUI 中只保留 1 个主版本，其余移入 `legacy/` 或删除。

## 10. 当前建议的文件分类

### Keep

- `parallel_version/*.py`
- `parallel_version/config_examples/`
- `Data_process/HDF5_create/*.py`
- `Pytorch_Model/src/`
- `serial_version/docs/`

### Review

- `serial_version/*.py`
- `Data_process/JSON_layout_create/*.py`
- 全部 `design_*.json`
- `Pytorch_Model/src/tools/`

### Remove or ignore

- `tmp/`
- `__pycache__/`
- `.claude/`
- `*.log`
- `*.pth`
- `*.h5`，除非作为极小样例保留

## 11. 下一阶段建议

下一阶段不建议直接“大规模重构”。更稳妥的顺序是：

1. 完成发布文档、术语表和仓库结构说明
2. 清理不应公开的文件与大文件
3. 统一编码并修复文档可读性
4. 把绝对路径改成模板配置
5. 在具备 ADS / RFPro / PDK 环境的机器上做最小运行验证
