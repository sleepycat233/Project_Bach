#!/usr/bin/env python3.11
"""
Project Bach 第五阶段 - GitHub自动发布模块
"""

from .template_engine import TemplateEngine
from .git_publisher import GitPublisher

__version__ = "1.0.0"
__author__ = "Project Bach"

__all__ = [
    'TemplateEngine',
    'GitPublisher'
]