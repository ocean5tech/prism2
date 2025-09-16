# Prism2 - 股票分析平台

## VS Code 连接说明

### 方法1: 网络路径
在Windows文件资源管理器中输入：
```
\\wsl.localhost\Ubuntu\home\wyatt\prism2
```
然后右键选择"通过Code打开"

### 方法2: 映射网络驱动器
1. 在文件资源管理器中右键"此电脑"
2. 选择"映射网络驱动器"
3. 输入路径：`\\wsl.localhost\Ubuntu\home\wyatt`
4. 分配盘符（如P:）
5. 在VS Code中打开 `P:\prism2`

### 方法3: 克隆到Windows
```bash
# 在Windows用户目录下克隆项目
git clone file:///home/wyatt/prism2 C:\Users\你的用户名\Documents\prism2
```

## 项目文档
- [架构设计](docs/architecture-design.md)