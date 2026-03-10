# 术语表

## A

### ADS

Keysight Advanced Design System。项目中的版图创建、工程组织和 EM 仿真调度依赖 ADS 生态。

### ADS Workspace

ADS 工程工作区。用于承载 library、cell、view 以及仿真相关文件。

## C

### Cell

ADS library 内的设计单元。通常对应一个待仿真的像素版图实例。

### CNN Surrogate Model

卷积神经网络代理模型。输入像素版图，输出对 EM 仿真结果的近似预测。

## E

### EM

Electromagnetic Simulation，电磁仿真。

### EM View

与版图绑定的电磁仿真视图。在本项目中通常指 `rfpro_view`。

## H

### HDF5 Dataset

用于机器学习训练的数据容器。保存版图张量、S 参数向量和元数据。

## J

### JSON Layout

以 JSON 形式描述的像素版图模板，包含元数据、图层矩阵和端口定义。

### JSON Layout Template

可批量生成、增强、导入导出的版图模板，是整个工作流的起点。

## L

### Layer Mapping

逻辑层名到 ADS 工艺层名的映射关系，例如 `M1 -> M1:drawing`。

### Layout Matrix

某个图层对应的二维二值矩阵。`1` 表示该像素存在金属或图形，`0` 表示空白。

### Library

ADS 工程中的设计库，包含多个 cell 和对应技术信息。

## P

### PDK

Process Design Kit，工艺设计套件。包含技术层、器件、规则和 substrate 等信息。

### Pixel Layout

将版图离散为规则像素网格后的表示方式，便于自动生成与机器学习建模。

### Port Definition

端口定义。通常包含端口名、所在层、边界方向和位置索引。

## R

### RFPro

Keysight 的电磁仿真相关视图与工作流组件。本项目使用它创建和执行 EM 视图。

## S

### S-Parameter

散射参数，描述多端口网络在频域下的响应。

### Touchstone

保存 S 参数的标准文件格式，扩展名通常为 `.s2p`、`.s3p`、`.s4p` 等。

### Substrate

版图和 EM 仿真使用的介质/层叠结构定义。

## W

### Worker

在本项目中指通过 ADS Python 环境执行具体任务的子进程脚本。

### Workflow

本项目的完整流程：版图模板生成 -> ADS 建模 -> EM 仿真 -> 结果导出 -> HDF5 构建 -> CNN 训练。

