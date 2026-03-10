import torch
import torch.nn as nn

class AdaptableEM_CNN(nn.Module):
    """
    一个灵活的、可适应不同输入输出规格的卷积神经网络模型。
    - 通过自适应池化层，可以处理不同空间尺寸的输入版图。
    - 通过动态配置的输出层，可以预测不同长度的S参数向量。
    """
    def __init__(self, output_dim, input_channels=2):
        """
        模型初始化。
        Args:
            output_dim (int): 最终S参数向量的长度 (例如 306)。
            input_channels (int): 输入版图的层数/通道数 (例如 2)。
        """
        super(AdaptableEM_CNN, self).__init__()
        
        # --- Part 1: 特征提取器 (Encoder) ---
        # 增强的特征提取网络，增加深度和宽度
        self.feature_extractor = nn.Sequential(
            # 第一组卷积层
            nn.Conv2d(input_channels, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.LeakyReLU(0.1, inplace=True),
            nn.Conv2d(64, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.LeakyReLU(0.1, inplace=True),
            nn.MaxPool2d(2),  # 尺寸减半
            
            # 第二组卷积层
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.LeakyReLU(0.1, inplace=True),
            nn.Conv2d(128, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.LeakyReLU(0.1, inplace=True),
            nn.MaxPool2d(2),  # 尺寸减半
            
            # 第三组卷积层
            nn.Conv2d(128, 256, kernel_size=3, padding=1),
            nn.BatchNorm2d(256),
            nn.LeakyReLU(0.1, inplace=True),
            nn.Conv2d(256, 256, kernel_size=3, padding=1),
            nn.BatchNorm2d(256),
            nn.LeakyReLU(0.1, inplace=True),
            nn.Conv2d(256, 256, kernel_size=3, padding=1),
            nn.BatchNorm2d(256),
            nn.LeakyReLU(0.1, inplace=True),
            nn.MaxPool2d(2),  # 尺寸减半
            
            # 第四组卷积层
            nn.Conv2d(256, 512, kernel_size=3, padding=1),
            nn.BatchNorm2d(512),
            nn.LeakyReLU(0.1, inplace=True),
            nn.Conv2d(512, 512, kernel_size=3, padding=1),
            nn.BatchNorm2d(512),
            nn.LeakyReLU(0.1, inplace=True),
            nn.Conv2d(512, 512, kernel_size=3, padding=1),
            nn.BatchNorm2d(512),
            nn.LeakyReLU(0.1, inplace=True),
            
            # 增强的自适应池化层
            nn.AdaptiveAvgPool2d((8, 8))  # 增加到8x8以容纳更多特征
        )
        
        # --- Part 2: 预测头 (Regressor) ---
        # 增强的预测网络，增加宽度和深度
        self.regressor = nn.Sequential(
            nn.Flatten(),
            nn.Linear(512 * 8 * 8, 2048),  # 增加输入维度
            nn.ReLU(inplace=True),
            nn.Dropout(0.4),
            
            nn.Linear(2048, 1024),
            nn.ReLU(inplace=True),
            nn.Dropout(0.4),
            
            nn.Linear(1024, 512),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            
            nn.Linear(512, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            
            # 动态输出层
            nn.Linear(256, output_dim),
            nn.Tanh()
        )

    def forward(self, x):
        """定义前向传播路径。"""
        features = self.feature_extractor(x)
        output = self.regressor(features)
        return output

if __name__ == '__main__':
    # 这是一个简单的测试，用于验证模型是否能被正确创建和运行
    
    # 模拟一个 2端口, 16x16, 双层版图的数据
    print("--- 测试场景 1: 2端口, 16x16, 2层 ---")
    output_dim_1 = 306 # 3个S参数 * 2 (实/虚) * 51个频率点
    input_channels_1 = 2
    model1 = AdaptableEM_CNN(output_dim=output_dim_1, input_channels=input_channels_1)
    
    # 模拟一个批次的输入数据 (4个样本)
    # 输入尺寸为 18x18 (16x16 + 2 padding)
    dummy_input_1 = torch.randn(4, input_channels_1, 18, 18)
    output_1 = model1(dummy_input_1)
    print(f"输入形状: {dummy_input_1.shape}")
    print(f"输出形状: {output_1.shape}")
    assert output_1.shape == (4, output_dim_1)
    print("测试通过!")

    # 模拟一个 4端口, 25x25, 单层版图的数据
    print("\n--- 测试场景 2: 4端口, 25x25, 1层 ---")
    # 4端口需要预测 S11,S21,S22,S31,S32,S33,S41,S42,S43,S44 共10个S参数
    output_dim_2 = 10 * 2 * 51 # 假设还是51个频率点
    input_channels_2 = 1
    model2 = AdaptableEM_CNN(output_dim=output_dim_2, input_channels=input_channels_2)
    
    # 输入尺寸为 27x27 (25x25 + 2 padding)
    dummy_input_2 = torch.randn(4, input_channels_2, 27, 27)
    output_2 = model2(dummy_input_2)
    print(f"输入形状: {dummy_input_2.shape}")
    print(f"输出形状: {output_2.shape}")
    assert output_2.shape == (4, output_dim_2)
    print("测试通过!")
