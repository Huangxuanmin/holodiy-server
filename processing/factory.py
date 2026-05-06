"""处理器工厂函数。"""
from .full_parallax import FullParallaxProcessor
from .horizontal import HorizontalParallaxProcessor


def create_processor(processor_type: str = "horizontal"):
    """根据类型创建处理器实例。

    支持类型:
      - "horizontal": 水平视差处理器
      - "full": 全视差处理器
    """
    if processor_type == "horizontal":
        return HorizontalParallaxProcessor()
    if processor_type == "full":
        return FullParallaxProcessor()
    raise ValueError(f"不支持的处理器类型: {processor_type}")
