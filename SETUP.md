# Project Bach 设置指南

## 🔐 安全配置

为了保护API密钥和敏感信息，Project Bach使用环境变量管理配置。

### 1. 设置环境变量

```bash
# 复制环境变量模板
cp .env.template .env

# 编辑.env文件，填入真实的密钥
nano .env
```

### 2. 获取必需的API密钥

#### OpenRouter API密钥
1. 访问 https://openrouter.ai/
2. 注册账户并登录
3. 进入 **API Keys** 页面
4. 创建新的API密钥
5. 复制密钥到`.env`文件中的`OPENROUTER_API_KEY`

#### Tailscale认证密钥
1. 访问 https://tailscale.com/
2. 注册账户并登录管理控制台
3. 进入 **Settings** → **Keys**
4. 点击 **Generate auth key**
5. 配置密钥设置：
   - ✅ **Reusable** (可重复使用)
   - ✅ **Preauthorized** (预授权)
   - ❌ **Ephemeral** (非临时)
6. 复制密钥到`.env`文件中的`TAILSCALE_AUTH_KEY`

python3.11 src/cli/main.py --mode monitor --config config.yaml

## 🚀 快速启动

### 第一次设置
```bash
# 1. 安装依赖
pip3.11 install -r requirements.txt

# 2. 设置环境变量（见上方说明）
cp .env.template .env
# 编辑.env文件填入真实密钥

# 3. 下载MLX Whisper模型（必需）
# 设置HuggingFace token（如果.env文件中已有，自动使用）
source .env

# 下载推荐的基础模型
./venv/bin/python -c "
import os
from huggingface_hub import snapshot_download
token = os.getenv('HUGGINGFACE_TOKEN')

# 下载基础模型组合
models = [
    'mlx-community/whisper-tiny-mlx',    # 默认快速模型
    'mlx-community/whisper-base-mlx',    # 英文推荐模型
    'mlx-community/whisper-medium-mlx'   # 平衡模型
]

for model in models:
    try:
        print(f'Downloading {model}...')
        cache_path = snapshot_download(model, token=token)
        print(f'✅ {model} downloaded to: {cache_path}')
    except Exception as e:
        print(f'❌ Failed to download {model}: {e}')
"

# 4. 生成配置文件
python3.11 src/utils/env_manager.py

# 5. 运行测试验证
python3.11 -m pytest tests/unit/test_network_manager.py -v
```

### 连接Tailscale网络
```bash
# 使用配置中的密钥连接
python3.11 -c "
from src.utils.env_manager import setup_project_environment
from src.network.tailscale_manager import TailscaleManager

config = setup_project_environment()
if config:
    manager = TailscaleManager(config['network']['tailscale'])
    if manager.connect():
        print('✅ Tailscale连接成功')
        status = manager.check_status()
        print(f'节点IP: {status[\"tailscale_ips\"]}')
    else:
        print('❌ Tailscale连接失败')
"
```

## 📁 文件结构说明

```
Project_Bach/
├── .env                    # 环境变量（不提交到Git）
├── .env.template          # 环境变量模板
├── config.template.yaml   # 配置模板
├── config.yaml           # 实际配置（自动生成，不提交到Git）
├── src/
│   ├── utils/
│   │   └── env_manager.py # 环境管理器
│   └── network/           # 网络集成模块
├── tests/                 # 测试文件
└── SETUP.md              # 此设置指南
```