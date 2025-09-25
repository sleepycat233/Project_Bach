# Project Bach 设置指南

## 🔐 安全配置

Project Bach使用环境变量管理敏感配置，使用YAML文件管理应用配置。

### 1. 设置环境变量

```bash
# 复制环境变量模板
cp .env.template .env

# 编辑.env文件，填入真实的密钥
nano .env
```

### 2. 获取API密钥

#### OpenRouter API密钥（AI功能必需）
1. 访问 https://openrouter.ai/
2. 注册账户并登录
3. 进入 **API Keys** 页面
4. 创建新的API密钥
5. 复制密钥到`.env`文件中的`OPENROUTER_API_KEY`

#### HuggingFace Token（Speaker Diarization功能必需）
1. 访问 https://huggingface.co/
2. 注册账户并登录
3. 进入 **Settings** → **Access Tokens**
4. 创建新的Token（Read权限即可）
5. 复制Token到`.env`文件中的`HUGGINGFACE_TOKEN`

#### Tailscale认证密钥（远程访问可选）
1. 访问 https://tailscale.com/
2. 注册账户并登录管理控制台
3. 进入 **Settings** → **Keys**
4. 点击 **Generate auth key**
5. 配置密钥设置：
   - ✅ **Reusable** (可重复使用)
   - ✅ **Preauthorized** (预授权)
   - ❌ **Ephemeral** (非临时)
6. 复制密钥到`.env`文件中的`TAILSCALE_AUTH_KEY`

## 🚀 快速启动

### 第一次设置
```bash
# 1. 创建虚拟环境并安装依赖
python3.11 -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt

# 2. 设置环境变量（见上方说明）
cp .env.template .env
# 编辑.env文件填入真实密钥

# 3. 安装spaCy语言模型（NER匿名化功能）
python -m spacy download zh_core_web_sm
python -m spacy download en_core_web_sm

# 4. 下载基础MLX Whisper模型
python -c "
import os
from huggingface_hub import snapshot_download

# 下载推荐的基础模型组合
models = [
    'mlx-community/whisper-tiny-mlx',        # 快速转录
    'mlx-community/whisper-large-v3-mlx'     # 高精度转录
]

for model_repo in models:
    try:
        print(f'Downloading {model_repo}...')
        cache_path = snapshot_download(model_repo)
        print(f'✅ {model_repo} downloaded')
    except Exception as e:
        print(f'❌ Failed to download {model_repo}: {e}')
"

# 5. 验证安装
python -m pytest tests/unit/utils/test_preferences_manager.py -v
```

## 🎮 运行项目

### 开发模式（推荐）
```bash
# 启动开发模式 - 支持自动重载
python src/cli/main.py --dev

# 特点：
# ✅ Flask自动重载 - 代码修改立即生效
# ✅ 跳过Tailscale检查 - 快速启动
# ✅ 调试模式开启
# ✅ 本地访问：http://localhost:8080
```

### 生产模式
```bash
# 启动生产模式 - 完整功能
python src/cli/main.py

# 特点：
# ✅ 文件监控功能
# ✅ Tailscale网络检查
# ✅ 远程安全访问
# ✅ 稳定性优化
```

### Web前端独立启动
```bash
# 仅启动Web界面（测试用）
python run_dev_server.py

# 访问: http://localhost:8080
```