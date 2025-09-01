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

### 3. 自动生成配置文件

```bash
# 从模板生成配置文件（会自动读取.env中的密钥）
python3.11 -c "from src.utils.env_manager import setup_project_environment; setup_project_environment()"
```

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

## 🔒 安全最佳实践

### 什么不会提交到Git
- `.env` - 包含真实密钥
- `config.yaml` - 包含替换后的密钥
- `config.local.yaml` - 本地配置
- `config.production.yaml` - 生产配置

### 什么会提交到Git
- `.env.template` - 环境变量模板
- `config.template.yaml` - 配置模板
- `src/utils/env_manager.py` - 环境管理器
- `SETUP.md` - 设置指南

### 团队协作
1. **新成员加入**：
   ```bash
   git clone <repository>
   cp .env.template .env
   # 填入自己的API密钥
   python3.11 src/utils/env_manager.py
   ```

2. **更新配置模板**：
   - 修改 `config.template.yaml`
   - 提交到Git
   - 团队成员重新运行 `python3.11 src/utils/env_manager.py`

## 🎯 MLX Whisper模型管理

### 模型下载详细说明

Project Bach使用MLX Whisper模型进行音频转录。模型会自动缓存到HuggingFace Hub缓存目录 `~/.cache/huggingface/hub/`。

#### 推荐模型组合

```bash
# 设置HuggingFace认证
source .env  # 加载HUGGINGFACE_TOKEN

# 方案1：基础模型组合（推荐，3个模型）
./venv/bin/python -c "
import os
from huggingface_hub import snapshot_download
token = os.getenv('HUGGINGFACE_TOKEN')

models = [
    'mlx-community/whisper-tiny-mlx',    # 默认快速模型 (~39MB)
    'mlx-community/whisper-base-mlx',    # 英文推荐模型 (~142MB)  
    'mlx-community/whisper-medium-mlx'   # 平衡性能模型 (~769MB)
]

for model in models:
    print(f'📥 Downloading {model}...')
    cache_path = snapshot_download(model, token=token)
    print(f'✅ Downloaded to: {cache_path}')
"

# 方案2：完整模型支持（高级用户）
./venv/bin/python -c "
import os
from huggingface_hub import snapshot_download
token = os.getenv('HUGGINGFACE_TOKEN')

models = [
    'mlx-community/whisper-tiny-mlx',      # 快速模型
    'mlx-community/whisper-base-mlx',      # 英文推荐
    'mlx-community/whisper-small-mlx',     # 英文推荐  
    'mlx-community/whisper-medium-mlx',    # 平衡模型
    'mlx-community/whisper-large-v3-mlx',  # 多语言推荐
    'mlx-community/whisper-large-v3-turbo' # 最新turbo版本
]

for model in models:
    print(f'📥 Downloading {model}...')
    cache_path = snapshot_download(model, token=token)
    print(f'✅ Downloaded to: {cache_path}')
"
```

#### 单独下载特定模型

```bash
# 下载辅助函数
download_mlx_model() {
    local model_name=$1
    source .env
    ./venv/bin/python -c "
import os
from huggingface_hub import snapshot_download
token = os.getenv('HUGGINGFACE_TOKEN')
model = 'mlx-community/$model_name'
print(f'📥 Downloading {model}...')
cache_path = snapshot_download(model, token=token)
print(f'✅ {model} downloaded to: {cache_path}')
"
}

# 使用示例
download_mlx_model whisper-large-v3-mlx
download_mlx_model whisper-small-mlx
```

#### 检查已下载模型

```bash
# 查看HuggingFace缓存中的MLX模型
ls -la ~/.cache/huggingface/hub/ | grep whisper

# 使用API检查模型状态
curl -s http://localhost:8080/api/models/smart-config | python3 -c "
import json, sys
data = json.load(sys.stdin)
print('📊 MLX Whisper模型状态:')
for model in data['all']:
    status = '✅ Downloaded' if model['downloaded'] else '📦 Not downloaded'
    default = ' (default)' if model.get('is_default') else ''
    print(f'  {model[\"name\"]}: {status}{default}')
"
```

#### 模型存储说明

- **存储位置**: `~/.cache/huggingface/hub/models--mlx-community--*`
- **模型大小**: 
  - whisper-tiny-mlx: ~39MB
  - whisper-base-mlx: ~142MB  
  - whisper-small-mlx: ~244MB
  - whisper-medium-mlx: ~769MB
  - whisper-large-v3-mlx: ~1.5GB
  - whisper-large-v3-turbo: ~1.5GB
- **推荐磁盘空间**: 至少3GB可用空间（基础组合）
- **跨项目共享**: 缓存模型可被其他MLX项目重用

## 🔧 故障排除

### 问题1: "配置文件不存在"
```bash
# 解决方案：重新生成配置
python3.11 src/utils/env_manager.py
```

### 问题2: "API密钥无效"
```bash
# 解决方案：检查.env文件中的密钥格式
cat .env
# 确保密钥格式正确，无多余空格或引号
```

### 问题3: "Tailscale连接失败"
```bash
# 检查密钥有效性
tailscale up --authkey=你的密钥

# 检查网络状态
tailscale status
```

### 问题4: "MLX Whisper模型未找到"
```bash
# 解决方案：检查模型下载状态
curl -s http://localhost:8080/api/models/smart-config | python3 -c "
import json, sys
data = json.load(sys.stdin)
for model in data['all']:
    if not model['downloaded']:
        print(f'📦 Missing: {model[\"name\"]}')
"

# 重新下载缺失的模型
source .env
./venv/bin/python -c "
import os
from huggingface_hub import snapshot_download
token = os.getenv('HUGGINGFACE_TOKEN')
snapshot_download('mlx-community/whisper-tiny-mlx', token=token)
"
```

### 问题5: "HuggingFace认证失败"
```bash
# 解决方案1：检查.env文件中的token
grep HUGGINGFACE_TOKEN .env

# 解决方案2：获取新的HuggingFace token
# 1. 访问 https://huggingface.co/settings/tokens
# 2. 创建新的 Read token
# 3. 更新 .env 文件中的 HUGGINGFACE_TOKEN

# 解决方案3：测试认证
source .env
./venv/bin/python -c "
import os
from huggingface_hub import HfApi
api = HfApi(token=os.getenv('HUGGINGFACE_TOKEN'))
user_info = api.whoami()
print(f'✅ Logged in as: {user_info.get(\"name\", \"Unknown\")}')
"
```

### 问题6: "模型下载速度慢或失败"
```bash
# 解决方案1：使用代理（如果需要）
export https_proxy=http://your-proxy:port
export http_proxy=http://your-proxy:port
source .env
./venv/bin/python -c "
import os
from huggingface_hub import snapshot_download
token = os.getenv('HUGGINGFACE_TOKEN')
snapshot_download('mlx-community/whisper-tiny-mlx', token=token)
"

# 解决方案2：分步下载较小模型
# 先下载tiny模型测试网络连接
./venv/bin/python -c "
import os
from huggingface_hub import snapshot_download
token = os.getenv('HUGGINGFACE_TOKEN')
snapshot_download('mlx-community/whisper-tiny-mlx', token=token)
"
```

## 📞 获取帮助

如果遇到问题：
1. 检查 `./data/logs/app.log` 日志文件
2. 运行测试验证功能：`python3.11 -m pytest tests/ -v`
3. 查看详细错误信息：`python3.11 src/utils/env_manager.py`