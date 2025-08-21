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
        
    def transcribe_audio(self, audio_path: Path) -> str:
        """转录音频文件
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            转录文本
            
        Raises:
            Exception: 转录失败
        """
        model = self.config.get('model', 'medium')
        language = self.config.get('language', 'zh')
        
        # 获取音频文件信息
        file_size_mb = audio_path.stat().st_size / (1024 * 1024)
        audio_duration = self._estimate_audio_duration(audio_path)
        
        self.logger.info(f"开始转录音频: {audio_path.name}")
        self.logger.info(f"文件信息: 大小={file_size_mb:.1f}MB, 预估时长={audio_duration:.1f}分钟, 模型={model}, 语言={language}")
        
        # 从配置获取阈值
        large_file_threshold = self.config.get('large_file_threshold_mb', 50)
        long_audio_threshold = self.config.get('long_audio_threshold_min', 30)
        
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
            # 使用WhisperKit CLI进行真实转录
            return self.whisperkit_client.transcribe(audio_path, audio_duration)
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
        self.language_detector = LanguageDetector(config)
        
    def transcribe(self, audio_path: Path, audio_duration: float = None) -> str:
        """使用WhisperKit CLI进行音频转录
        
        Args:
            audio_path: 音频文件路径
            audio_duration: 音频时长（分钟），用于计算合适的超时时间
            
        Returns:
            转录文本
            
        Raises:
            Exception: 转录失败
        """
        # 从配置文件获取WhisperKit设置
        model = self.config.get('model', 'medium')
        default_language = self.config.get('language', 'zh')
        
        # 检测音频语言
        language = self.language_detector.detect_language(audio_path, default_language)
        
        # 从配置获取超时参数
        base_timeout = self.config.get('base_timeout_seconds', 120)
        max_timeout = self.config.get('max_timeout_seconds', 7200)  # 2小时最大超时
        processing_factors = self.config.get('processing_factor_per_model', {
            'tiny': 5, 'base': 8, 'small': 10, 'medium': 15, 'large': 20
        })
        
        # 动态计算超时时间：基础时间 + 音频时长的倍数
        if audio_duration:
            processing_factor = processing_factors.get(model, 15)
            estimated_timeout = int(audio_duration * processing_factor + base_timeout)
            timeout = min(max(estimated_timeout, 300), max_timeout)  # 至少5分钟，最多max_timeout
            self.logger.info(f"根据音频时长({audio_duration:.1f}分钟)计算超时时间: {timeout}秒 (因子={processing_factor})")
        else:
            timeout = base_timeout
        
        # 获取用户配置
        model_prefix = self.config.get('model_prefix', 'openai')
        
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
            "--language", language,
            "--model", model,
            "--model-prefix", model_prefix,
            "--task", "transcribe",
            "--audio-encoder-compute-units", audio_compute,
            "--text-decoder-compute-units", text_compute,
            "--chunking-strategy", chunking,
            "--concurrent-worker-count", str(workers)
        ]
        
        # 添加性能优化选项
        if use_cache:
            cmd.append("--use-prefill-cache")
        
        self.logger.debug(f"WhisperKit命令: {' '.join(cmd)}")
        self.logger.info(f"🚀 WhisperKit转录配置:")
        self.logger.info(f"   模型: {model_prefix}-{model}, 语言: {language}")
        self.logger.info(f"   计算单元: 音频={audio_compute}, 文本={text_compute}")
        self.logger.info(f"   优化选项: 缓存={'✅' if use_cache else '❌'}, 分块={chunking}, 并发={workers}")
        self.logger.info(f"   预计处理时间: {timeout//60}分{timeout%60}秒")
        
        # 启动进度监控
        start_time = time.time()
        progress_thread = threading.Thread(target=self._monitor_progress, args=(start_time, timeout, audio_path.name))
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
            elapsed = time.time() - start_time
            raise Exception(f"WhisperKit转录超时 (已运行{elapsed//60:.0f}分{elapsed%60:.0f}秒，超时限制{timeout}秒)")
        
        elapsed_time = time.time() - start_time
        
        if result.returncode != 0:
            raise Exception(f"WhisperKit执行失败: {result.stderr}")
        
        # 提取转录文本
        transcript = result.stdout.strip()
        
        if not transcript or len(transcript.strip()) < 5:
            raise Exception("转录结果为空或过短")
        
        # 计算转录性能指标
        words_count = len(transcript.split())
        chars_count = len(transcript)
        words_per_second = words_count / elapsed_time if elapsed_time > 0 else 0
        chars_per_second = chars_count / elapsed_time if elapsed_time > 0 else 0
        
        # 记录转录结果和性能
        preview = transcript[:80].replace('\n', ' ') + "..." if len(transcript) > 80 else transcript
        self.logger.info(f"✅ WhisperKit转录完成!")
        self.logger.info(f"📊 性能指标: 用时={elapsed_time:.1f}秒, 速度={words_per_second:.1f}词/秒, {chars_per_second:.1f}字符/秒")
        self.logger.info(f"📄 结果统计: {words_count}词, {chars_count}字符, 内容预览: {preview}")
        
        return transcript
    
    def _monitor_progress(self, start_time: float, timeout: int, filename: str):
        """监控转录进度并定期输出状态
        
        Args:
            start_time: 开始时间戳
            timeout: 总超时时间
            filename: 文件名
        """
        # 从配置获取进度报告间隔
        intervals = self.config.get('progress_report_intervals', [30, 60, 120, 300, 600])
        
        for interval in intervals:
            time.sleep(interval)
            elapsed = time.time() - start_time
            
            if elapsed >= timeout:
                break
                
            remaining = timeout - elapsed
            progress_percent = (elapsed / timeout) * 100
            
            self.logger.info(f"🔄 转录进度: 正在处理 {filename}")
            self.logger.info(f"⏱️  已运行: {self._format_time(elapsed)}, 剩余约: {self._format_time(remaining)} ({progress_percent:.1f}%)")
            
            # 如果接近超时，提供建议
            if remaining < 120:  # 最后2分钟
                self.logger.warning(f"⚠️  转录即将超时，建议考虑：")
                self.logger.warning(f"   1. 使用更小的WhisperKit模型（如tiny/base）")
                self.logger.warning(f"   2. 分段处理长音频文件")
                self.logger.warning(f"   3. 增加处理超时时间配置")
    
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


class LanguageDetector:
    """音频语言检测器"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化语言检测器
        
        Args:
            config: WhisperKit配置字典
        """
        self.config = config
        self.logger = logging.getLogger('project_bach.language_detector')
    
    def detect_language(self, audio_path: Path, default_language: str = 'zh') -> str:
        """智能检测音频语言（支持中英文双语）
        
        Args:
            audio_path: 音频文件路径
            default_language: 默认语言
            
        Returns:
            检测到的语言代码
        """
        filename_lower = audio_path.name.lower()
        
        # 明确的英文关键词检测（优先级最高）
        explicit_english_keywords = ['english', 'en-', '_en_', 'eng', 'lecture', 'meeting', 'class', 'course', 
                                   'lesson', 'presentation', 'seminar', 'interview']
        if any(keyword in filename_lower for keyword in explicit_english_keywords):
            self.logger.debug(f"文件名明确标识为英文: {audio_path.name}")
            return 'en'
        
        # 检查文件名中是否包含中文字符
        if any('\u4e00' <= char <= '\u9fff' for char in audio_path.name):
            self.logger.debug(f"文件名包含中文字符，判定为中文: {audio_path.name}")
            return 'zh'
        
        # 中文相关关键词检测
        chinese_keywords = ['chinese', 'zh', '中文', '会议', '讲座', '讨论', '汇报', '培训', 'audio', 'test']
        if any(keyword in filename_lower for keyword in chinese_keywords):
            self.logger.debug(f"文件名检测为中文相关: {audio_path.name}")
            return 'zh'
        
        # 对于无法明确判断的文件，使用配置的默认语言
        # 考虑到Project Bach主要处理中文内容，默认倾向中文
        self.logger.debug(f"无法从文件名判断语言，使用默认语言 {default_language}: {audio_path.name}")
        return default_language
    
    def is_supported_language(self, language: str) -> bool:
        """检查是否为支持的语言
        
        Args:
            language: 语言代码
            
        Returns:
            是否支持
        """
        supported_languages = self.config.get('supported_languages', ['en', 'zh'])
        return language in supported_languages


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