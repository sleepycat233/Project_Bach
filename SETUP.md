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

# 3. 下载WhisperKit模型（必需）
# 创建模型目录
mkdir -p ./models/whisperkit-coreml

# 下载英文优化模型（推荐）- 使用空音频触发下载
echo "创建临时音频文件用于模型下载..."
ffmpeg -f lavfi -i "anullsrc=channel_layout=mono:sample_rate=16000" -t 1 temp_download.wav -y 2>/dev/null
whisperkit-cli transcribe --model large-v3 --model-prefix distil --download-model-path ./models/whisperkit-coreml --audio-path temp_download.wav
rm temp_download.wav

# 下载多语言通用模型（可选）
# ffmpeg -f lavfi -i "anullsrc=channel_layout=mono:sample_rate=16000" -t 1 temp_download.wav -y 2>/dev/null
# whisperkit-cli transcribe --model large-v3 --model-prefix openai --download-model-path ./models/whisperkit-coreml --audio-path temp_download.wav
# rm temp_download.wav

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

## 🎯 WhisperKit模型管理

### 模型下载详细说明

Project Bach需要WhisperKit模型进行音频转录。模型会下载到项目本地的`./models/whisperkit-coreml/`目录。

#### 推荐模型组合

```bash
# 方案1：仅英文处理（推荐，节省存储空间）
ffmpeg -f lavfi -i "anullsrc=channel_layout=mono:sample_rate=16000" -t 1 temp_download.wav -y 2>/dev/null
whisperkit-cli transcribe --model large-v3 --model-prefix distil --download-model-path ./models/whisperkit-coreml --audio-path temp_download.wav
rm temp_download.wav

# 方案2：英文+多语言支持（完整功能）
ffmpeg -f lavfi -i "anullsrc=channel_layout=mono:sample_rate=16000" -t 1 temp_download.wav -y 2>/dev/null
whisperkit-cli transcribe --model large-v3 --model-prefix distil --download-model-path ./models/whisperkit-coreml --audio-path temp_download.wav
whisperkit-cli transcribe --model large-v3 --model-prefix openai --download-model-path ./models/whisperkit-coreml --audio-path temp_download.wav
rm temp_download.wav
```

#### 所有可用模型

```bash
# 下载辅助函数（复制使用）
download_model() {
    local model=$1
    local prefix=$2
    echo "下载 $prefix-$model 模型..."
    ffmpeg -f lavfi -i "anullsrc=channel_layout=mono:sample_rate=16000" -t 1 temp_download.wav -y 2>/dev/null
    whisperkit-cli transcribe --model $model --model-prefix $prefix --download-model-path ./models/whisperkit-coreml --audio-path temp_download.wav
    rm temp_download.wav
    echo "✅ $prefix-$model 下载完成"
}

# 英文专用模型（distil前缀）
download_model large-v3 distil  # 推荐
download_model medium distil

# 多语言模型（openai前缀）  
download_model large-v3 openai  # 推荐
download_model large-v2 openai
download_model medium openai
download_model small openai
download_model base openai
download_model tiny openai
```

#### 检查已下载模型

```bash
# 查看已下载的模型
ls -la ./models/whisperkit-coreml/

# 检查模型完整性
find ./models/whisperkit-coreml/ -name "*.mlmodelc" | head -10
```

#### 模型存储说明

- **存储位置**: `./models/whisperkit-coreml/`
- **模型大小**: 
  - tiny: ~39MB
  - base: ~142MB  
  - small: ~244MB
  - medium: ~600-769MB
  - large-v3: ~1.5-2.9GB
- **推荐磁盘空间**: 至少5GB可用空间

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

### 问题4: "WhisperKit模型未找到"
```bash
# 解决方案：重新下载推荐模型
whisperkit-cli download --model large-v3 --model-prefix distil --download-model-path ./models/whisperkit-coreml

# 检查下载结果
ls -la ./models/whisperkit-coreml/
```

### 问题5: "whisperkit-cli命令不存在"
```bash
# 解决方案：安装WhisperKit CLI
# macOS (推荐使用Homebrew)
brew install argmaxinc/whisperkit/whisperkit

# 或直接下载
curl -L https://github.com/argmaxinc/WhisperKit/releases/latest/download/whisperkit-cli-macos.zip -o whisperkit-cli.zip
unzip whisperkit-cli.zip
sudo mv whisperkit-cli /usr/local/bin/
```

### 问题6: "模型下载速度慢或失败"
```bash
# 解决方案1：使用代理（如果需要）
export https_proxy=http://your-proxy:port
whisperkit-cli download --model large-v3 --model-prefix distil --download-model-path ./models/whisperkit-coreml

# 解决方案2：分步下载较小模型
whisperkit-cli download --model medium --model-prefix distil --download-model-path ./models/whisperkit-coreml
```

## 📞 获取帮助

如果遇到问题：
1. 检查 `./data/logs/app.log` 日志文件
2. 运行测试验证功能：`python3.11 -m pytest tests/ -v`
3. 查看详细错误信息：`python3.11 src/utils/env_manager.py`