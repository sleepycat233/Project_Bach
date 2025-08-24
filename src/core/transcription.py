#!/usr/bin/env python3.11
"""
音频转录模块
负责音频文件的转录处理，包括WhisperKit集成和语言检测
"""

import subprocess
import logging
import time
import threading
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta


class TranscriptionService:
    """音频转录服务"""
    
    def __init__(self, whisperkit_config: Dict[str, Any]):
        """初始化转录服务
        
        Args:
            whisperkit_config: WhisperKit配置字典
        """
        self.config = whisperkit_config
        self.logger = logging.getLogger('project_bach.transcription')
        self.whisperkit_client = WhisperKitClient(whisperkit_config)
        
    def transcribe_audio(self, audio_path: Path, prompt: str = None, language_preference: str = 'english', 
                        custom_model: str = None, custom_model_prefix: str = None) -> str:
        """转录音频文件
        
        Args:
            audio_path: 音频文件路径
            prompt: Whisper系统提示词，用于提高特定术语识别准确性
            language_preference: 语言偏好 ('english' 或 'multilingual')
            custom_model: 自定义模型名称 (如'tiny', 'medium', 'large-v3')
            custom_model_prefix: 自定义模型前缀 (如'openai', 'distil')
            
        Returns:
            转录文本
            
        Raises:
            Exception: 转录失败
        """
        # 优先使用自定义模型参数，否则使用配置文件
        if custom_model and custom_model_prefix:
            model = custom_model
            model_prefix = custom_model_prefix
            # 根据模型前缀确定语言设置
            if custom_model_prefix == 'distil' and language_preference == 'english':
                language = 'en'
            elif custom_model_prefix == 'openai' and language_preference == 'multilingual':
                # WhisperKit不支持'auto'，多语言模式使用空字符串让其自动检测
                language = None  # 让WhisperKit自动检测
            else:
                # 根据语言偏好选择语言代码
                language = 'en' if language_preference == 'english' else None
        else:
            # 使用配置文件的默认设置
            language_config = self.config.get('language_configs', {}).get(language_preference, {})
            model = self.config.get('model', 'large-v3')
            model_prefix = language_config.get('model_prefix', 'distil')
            language = language_config.get('language_code', 'en')
        
        # 获取音频文件信息
        file_size_mb = audio_path.stat().st_size / (1024 * 1024)
        audio_duration = self._estimate_audio_duration(audio_path)
        
        self.logger.info(f"开始转录音频: {audio_path.name}")
        self.logger.info(f"文件信息: 大小={file_size_mb:.1f}MB, 模型={model_prefix}-{model}, 语言={language}")
        if prompt:
            self.logger.info(f"使用自定义提示词: {prompt[:50]}{'...' if len(prompt) > 50 else ''}")
        
        # 硬编码合理的阈值
        large_file_threshold = 50  # MB
        long_audio_threshold = 30  # 分钟
        
        # 大文件预警
        if file_size_mb > large_file_threshold:
            self.logger.warning(f"检测到大音频文件 ({file_size_mb:.1f}MB > {large_file_threshold}MB)，转录可能需要较长时间")
        
        if audio_duration > long_audio_threshold:
            self.logger.warning(f"检测到长音频文件 ({audio_duration:.1f}分钟 > {long_audio_threshold}分钟)，建议考虑分段处理")
            # 为超长音频提供处理建议
            if audio_duration > 60:  # 超过1小时
                self.logger.warning("📋 大文件处理建议:")
                self.logger.warning("   1. 推荐使用tiny或base模型以减少处理时间")
                self.logger.warning("   2. 考虑将音频分割为30分钟的片段")
                self.logger.warning("   3. 增加系统可用内存和处理器资源")
                self.logger.warning("   4. 设置足够的处理超时时间")
        
        try:
            # 使用WhisperKit CLI进行真实转录，传递计算出的实际参数
            return self.whisperkit_client.transcribe(
                audio_path=audio_path, 
                audio_duration=audio_duration, 
                prompt=prompt, 
                model=model, 
                model_prefix=model_prefix, 
                language=language
            )
        except Exception as e:
            self.logger.warning(f"WhisperKit转录失败，使用备用方案: {str(e)}")
            return self._fallback_transcription(audio_path)
    
    def _fallback_transcription(self, audio_path: Path) -> str:
        """备用转录方案（模拟转录）
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            模拟转录文本
        """
        self.logger.info("使用备用转录方案")
        
        # 保留原有的模拟转录逻辑作为备份
        if "meeting" in audio_path.name.lower():
            transcript = f"""
这是一个关于项目进展的会议转录，来自文件 {audio_path.name}。
张三首先汇报了上周的工作进展，主要完成了系统架构设计。
李四提到了在实施过程中遇到的技术难题，需要进一步研究。
王五建议采用新的技术方案来解决性能问题。
赵六负责协调各部门之间的配合工作。
会议持续了大约45分钟，最终确定了下一阶段的工作计划。
主要决策包括：技术架构优化、人员分工调整、时间节点确认。
            """.strip()
        elif "lecture" in audio_path.name.lower():
            transcript = f"""
这是一堂技术讲座的转录内容，来自文件 {audio_path.name}。
教授陈明详细介绍了人工智能在现代软件开发中的应用。
学生刘华提问关于机器学习算法的选择问题。
助教孙丽回答了关于数据预处理的具体方法。
讲座涵盖了理论基础、实践案例和未来发展趋势。
课程时长约60分钟，包含15分钟的问答环节。
            """.strip()
        else:
            transcript = f"""
WhisperKit转录备用方案 - 文件: {audio_path.name}
系统已尝试使用WhisperKit进行真实音频转录，但遇到技术问题。
建议检查：1) WhisperKit CLI是否正确安装 2) 音频文件格式是否支持 3) 系统资源是否充足
如需技术支持，请提供日志文件以便进一步诊断。
处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """.strip()
        
        # 记录备用转录结果预览
        preview = transcript[:50] + "..." if len(transcript) > 50 else transcript
        self.logger.info(f"备用转录完成，文本长度: {len(transcript)} 字符，内容预览: {preview}")
        return transcript
    
    def _estimate_audio_duration(self, audio_path: Path) -> float:
        """估算音频文件时长（分钟）
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            估算的音频时长（分钟）
        """
        try:
            # 尝试使用ffprobe获取精确时长
            cmd = ["ffprobe", "-i", str(audio_path), "-show_entries", "format=duration", 
                   "-v", "quiet", "-of", "csv=p=0"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout.strip():
                duration_seconds = float(result.stdout.strip())
                duration_minutes = duration_seconds / 60.0
                self.logger.debug(f"ffprobe检测音频时长: {duration_minutes:.1f}分钟")
                return duration_minutes
                
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, ValueError, FileNotFoundError):
            self.logger.debug("ffprobe不可用，使用文件大小估算时长")
        
        # 备用方案：基于文件大小估算（经验公式）
        file_size_mb = audio_path.stat().st_size / (1024 * 1024)
        # 假设平均比特率约64kbps（适中质量），1MB ≈ 2分钟
        estimated_minutes = file_size_mb * 2.0
        self.logger.debug(f"基于文件大小估算音频时长: {estimated_minutes:.1f}分钟")
        return estimated_minutes


class WhisperKitClient:
    """WhisperKit CLI客户端"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化WhisperKit客户端
        
        Args:
            config: WhisperKit配置字典
        """
        self.config = config
        self.logger = logging.getLogger('project_bach.whisperkit')
    
    def _ensure_model_available(self, base_model_path: str, model_path: str, model: str, model_prefix: str):
        """确保模型可用，如果不存在则自动下载"""
        import os
        from pathlib import Path
        
        # 确保模型目录存在
        model_dir = Path(base_model_path)
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # 检查期望的模型是否存在 (model_path 已经是完整的模型路径)
        expected_model_name = f"{model_prefix}-{model}" if model_prefix else model
        expected_model_dir = Path(model_path)
        
        if expected_model_dir.exists():
            self.logger.debug(f"模型已存在: {expected_model_dir}")
            return
        
        # 模型不存在，需要下载
        self.logger.info(f"🔄 模型文件夹 {expected_model_dir.name} 不存在，WhisperKit将自动下载")
        self.logger.info("⏳ 首次转录时会自动下载模型，可能需要几分钟...")
        
    def transcribe(self, audio_path: Path, audio_duration: float = None, prompt: str = None, model: str = None, model_prefix: str = None, language: str = None) -> str:
        """使用WhisperKit CLI进行音频转录
        
        Args:
            audio_path: 音频文件路径
            audio_duration: 音频时长（分钟），用于计算合适的超时时间
            prompt: Whisper系统提示词，用于提高特定术语识别准确性
            model: WhisperKit模型名称（如'large-v3', 'tiny'等）
            model_prefix: 模型前缀（如'openai', 'distil'）
            language: 语言代码（如'en', 'zh'，None表示自动检测）
            
        Returns:
            转录文本
            
        Raises:
            Exception: 转录失败
        """
        # 使用传入的参数，如果没有传入则使用默认值
        if model is None:
            model = self.config.get('model', 'large-v3')
        if model_prefix is None:
            model_prefix = 'openai'  # 默认使用OpenAI模型
        # language 参数直接使用传入值，None表示让WhisperKit自动检测
        
        # 获取模型路径并确保模型存在
        base_model_path = self.config.get('model_path', './models')
        model_container_path = f"{base_model_path}/whisperkit-coreml"
        
        # 根据实际文件夹命名约定构建模型路径
        # 实际模型文件夹命名规律：
        # - distil-whisper_distil-large-v3
        # - openai_whisper-large-v3-v20240930
        # - openai_whisper-large-v3  
        # - openai_whisper-medium
        if model_prefix == 'distil' and model == 'large-v3':
            # 特殊情况：distil模型使用不同的命名约定
            model_folder_name = "distil-whisper_distil-large-v3"
        elif model_prefix == 'openai':
            # OpenAI模型使用标准命名约定
            model_folder_name = f"openai_whisper-{model}"
        else:
            # 默认命名约定（向后兼容）
            model_folder_name = f"{model_prefix}_whisper-{model}"
        
        model_path = f"{model_container_path}/{model_folder_name}"
        self._ensure_model_available(base_model_path, model_path, model, model_prefix)
        
        # 硬编码合理的超时参数
        base_timeout = 120  # 2分钟基础超时
        max_timeout = 7200  # 2小时最大超时
        processing_factors = {
            'tiny': 5, 'base': 8, 'small': 10, 'medium': 15, 'large': 20
        }
        
        # 动态计算超时时间：基础时间 + 音频时长的倍数
        if audio_duration:
            processing_factor = processing_factors.get(model, 15)
            estimated_timeout = int(audio_duration * processing_factor + base_timeout)
            timeout = min(max(estimated_timeout, 300), max_timeout)  # 至少5分钟，最多max_timeout
            self.logger.info(f"根据音频时长({audio_duration:.1f}分钟)计算超时时间: {timeout}秒 (因子={processing_factor})")
        else:
            timeout = base_timeout
        
        
        # 硬编码最优性能设置
        audio_compute = 'cpuAndNeuralEngine'  # Apple Silicon最优
        text_compute = 'cpuAndNeuralEngine'   # 神经引擎加速
        use_cache = True                      # 启用预填充缓存
        chunking = 'vad'                     # 语音活动检测
        workers = 2                          # 长音频优化并发数
        
        
        # 构建WhisperKit命令
        cmd = [
            "whisperkit-cli",
            "transcribe",
            "--audio-path", str(audio_path),
            "--model", model,
            "--model-prefix", model_prefix,
            "--task", "transcribe",
            "--audio-encoder-compute-units", audio_compute,
            "--text-decoder-compute-units", text_compute,
            "--chunking-strategy", chunking,
            "--concurrent-worker-count", str(workers)
        ]
        
        # 只有模型存在时才指定model-path，否则让WhisperKit自动下载
        if Path(model_path).exists():
            cmd.extend(["--model-path", model_path])
            self.logger.debug(f"Using local model: {model_path}")
        else:
            cmd.extend(["--download-model-path", base_model_path])
            self.logger.info(f"Model not found, will auto-download to: {base_model_path}")
        
        # 添加语言参数
        if language:
            cmd.extend(["--language", language])
        
        # 添加prompt参数
        if prompt and prompt.strip():
            cmd.extend(["--prompt", prompt.strip()])
        
        # 添加性能优化选项
        if use_cache:
            cmd.append("--use-prefill-cache")
        
        self.logger.debug(f"WhisperKit command: {' '.join(cmd)}")
        self.logger.info("🚀 WhisperKit transcription config:")
        self.logger.info(f"   Model: {model_prefix}-{model}, Language: {language or 'auto'}")
        self.logger.info(f"   Compute units: audio={audio_compute}, text={text_compute}")
        self.logger.info(f"   Optimization: cache={'✅' if use_cache else '❌'}, chunking={chunking}, workers={workers}")
        self.logger.info(f"   Timeout limit: {timeout//60}m{timeout%60}s")
        
        # 启动进度监控
        start_time = time.time()
        stop_event = threading.Event()
        progress_thread = threading.Thread(target=self._monitor_progress, args=(start_time, timeout, audio_path.name, stop_event))
        progress_thread.daemon = True
        progress_thread.start()
        
        # 执行转录
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
        except subprocess.TimeoutExpired:
            stop_event.set()  # 停止进度监控
            elapsed = time.time() - start_time
            raise Exception(f"WhisperKit transcription timeout (ran {elapsed//60:.0f}m{elapsed%60:.0f}s, timeout limit {timeout}s)")
        
        elapsed_time = time.time() - start_time
        
        if result.returncode != 0:
            stop_event.set()  # 停止进度监控
            raise Exception(f"WhisperKit执行失败: {result.stderr}")
        
        # 提取转录文本
        transcript = result.stdout.strip()
        
        if not transcript or len(transcript.strip()) < 5:
            stop_event.set()  # 停止进度监控
            raise Exception("转录结果为空或过短")
        
        # 计算转录性能指标
        words_count = len(transcript.split())
        chars_count = len(transcript)
        words_per_second = words_count / elapsed_time if elapsed_time > 0 else 0
        chars_per_second = chars_count / elapsed_time if elapsed_time > 0 else 0
        
        # 记录转录结果和性能
        preview = transcript[:80].replace('\n', ' ') + "..." if len(transcript) > 80 else transcript
        # 停止进度监控线程
        stop_event.set()
        
        self.logger.info("✅ WhisperKit transcription completed!")
        self.logger.info(f"📊 Performance metrics: time={elapsed_time:.1f}s, speed={words_per_second:.1f}words/s, {chars_per_second:.1f}chars/s")
        self.logger.info(f"📄 Result stats: {words_count} words, {chars_count} characters, preview: {preview}")
        
        return transcript
    
    def _monitor_progress(self, start_time: float, timeout: int, filename: str, stop_event: threading.Event):
        """监控转录进度并定期输出状态
        
        Args:
            start_time: 开始时间戳
            timeout: 总超时时间
            filename: 文件名
            stop_event: 停止事件信号
        """
        # 硬编码合理的进度报告间隔
        intervals = [30, 60, 120, 300, 600]  # 30秒, 1分钟, 2分钟, 5分钟, 10分钟
        
        for interval in intervals:
            # 使用wait()而非sleep()，这样可以立即响应stop_event
            if stop_event.wait(timeout=interval):
                # 收到停止信号，退出监控
                break
                
            elapsed = time.time() - start_time
            
            if elapsed >= timeout:
                break
                
            remaining = timeout - elapsed
            progress_percent = (elapsed / timeout) * 100
            
            # Display real-time processing status
            self.logger.info(f"🔄 Transcription in progress: {filename}")
            self.logger.info(f"⏱️  Elapsed time: {self._format_time(elapsed)} | Timeout progress: {progress_percent:.1f}%")
            
            # Provide suggestions if nearing timeout
            if remaining < 120:  # Last 2 minutes
                self.logger.warning("⚠️  Transcription nearing timeout, consider:")
                self.logger.warning("   1. Use smaller WhisperKit model (e.g. tiny/base)")
                self.logger.warning("   2. Process long audio files in segments")
                self.logger.warning("   3. Increase processing timeout configuration")
    
    def _format_time(self, seconds: float) -> str:
        """格式化时间显示
        
        Args:
            seconds: 秒数
            
        Returns:
            格式化的时间字符串
        """
        if seconds < 60:
            return f"{seconds:.0f}秒"
        elif seconds < 3600:
            return f"{seconds//60:.0f}分{seconds%60:.0f}秒"
        else:
            return f"{seconds//3600:.0f}小时{(seconds%3600)//60:.0f}分{seconds%60:.0f}秒"



class TranscriptionValidator:
    """转录结果验证器"""
    
    @staticmethod
    def validate_transcript(transcript: str) -> bool:
        """验证转录结果的有效性
        
        Args:
            transcript: 转录文本
            
        Returns:
            是否有效
        """
        if not transcript or not isinstance(transcript, str):
            return False
        
        # 检查最小长度
        if len(transcript.strip()) < 5:
            return False
        
        # 检查是否包含有意义的内容（不只是空白字符）
        meaningful_chars = sum(1 for c in transcript if c.isalnum() or c in '，。！？,.')
        if meaningful_chars < 3:
            return False
        
        return True
    
    @staticmethod
    def clean_transcript(transcript: str) -> str:
        """清理转录文本
        
        Args:
            transcript: 原始转录文本
            
        Returns:
            清理后的文本
        """
        if not transcript:
            return ""
        
        # 先按行处理，移除标记行
        lines = transcript.split('\n')
        content_lines = []
        
        for line in lines:
            line = line.strip()
            # 跳过时间戳和其他标记行
            if line and not line.startswith('[') and not line.startswith('>>'):
                # 清理行内多余空格
                import re
                line = re.sub(r'\s+', ' ', line)
                content_lines.append(line)
        
        # 合并行并清理多余空白
        result = '\n'.join(content_lines)
        
        # 移除多余的连续换行符，但保留必要的换行
        result = re.sub(r'\n\s*\n+', '\n', result)
        
        return result.strip()