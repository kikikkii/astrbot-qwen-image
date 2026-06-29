from dataclasses import dataclass, field
from typing import List, Optional, Union


# ---------------------------------------------------------------------------
# 内容块 —— 每条消息的内容项可以是图片或文本
# ---------------------------------------------------------------------------

@dataclass
class ImageContent:
    """通过 URL/Base64 引用一张图片。"""
    image: str

    def to_dict(self) -> dict:
        return {"image": self.image}


@dataclass
class TextContent:
    """文本提示词或指令。"""
    text: str

    def to_dict(self) -> dict:
        return {"text": self.text}


ContentBlock = Union[ImageContent, TextContent]


# ---------------------------------------------------------------------------
# 消息
# ---------------------------------------------------------------------------

@dataclass
class Message:
    """对话中的单条消息（通常 role='user'）。"""
    role: str = "user"
    content: List[ContentBlock] = field(default_factory=list)

    def add_image(self, image_url: str) -> "Message":
        """向此消息添加图片引用。"""
        self.content.append(ImageContent(image=image_url))
        return self

    def add_text(self, text: str) -> "Message":
        """向此消息添加文本提示。"""
        self.content.append(TextContent(text=text))
        return self

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": [block.to_dict() for block in self.content],
        }


# ---------------------------------------------------------------------------
# 生成参数
# ---------------------------------------------------------------------------

@dataclass
class GenerationParameters:
    """图像生成的可选参数。

    Attributes:
        n: 生成图片数量（1-4），默认 1。
        size: 输出分辨率，如 "1024*1024"、"2048*2048"。
        negative_prompt: 生成图片中要避免的元素。
        prompt_extend: 是否让模型改写/扩写提示词。
        watermark: 是否在输出中添加水印。
        seed: 可选 RNG 种子，用于可复现结果。
    """

    n: int = 1
    size: str = "1024*1024"
    negative_prompt: str = ""
    prompt_extend: bool = True
    watermark: bool = False
    seed: Optional[int] = None

    def to_dict(self) -> dict:
        d: dict = {
            "n": self.n,
            "size": self.size,
            "prompt_extend": self.prompt_extend,
            "watermark": self.watermark,
        }
        if self.negative_prompt:
            d["negative_prompt"] = self.negative_prompt
        if self.seed is not None:
            d["seed"] = self.seed
        return d


# ---------------------------------------------------------------------------
# 顶层请求
# ---------------------------------------------------------------------------

@dataclass
class QwenImageRequest:
    """Qwen-Image 多模态生成 API 的完整请求体。

    用法::

        req = (
            QwenImageRequest(model="qwen-image-2.0-pro")
            .add_message(
                Message()
                .add_image("https://example.com/ref.png")
                .add_text("把这张照片变成水彩画")
            )
            .with_parameters(GenerationParameters(n=2, size="2048*2048"))
        )
        payload = req.to_dict()
    """

    model: str
    input_messages: List[Message] = field(default_factory=list)
    parameters: GenerationParameters = field(default_factory=GenerationParameters)

    def add_message(self, message: Message) -> "QwenImageRequest":
        """向输入追加一条消息。"""
        self.input_messages.append(message)
        return self

    def with_parameters(self, params: GenerationParameters) -> "QwenImageRequest":
        """设置生成参数。"""
        self.parameters = params
        return self

    def to_dict(self) -> dict:
        """序列化为 Bailian API 所需的 dict 格式。"""
        return {
            "model": self.model,
            "input": {
                "messages": [msg.to_dict() for msg in self.input_messages],
            },
            "parameters": self.parameters.to_dict(),
        }


# ===========================================================================
# 响应类型 —— Bailian JSON 响应的类型化封装
# ===========================================================================


@dataclass
class ImageResult:
    """API 响应内容块中的单张生成图片。"""

    url: str


@dataclass
class ChoiceResult:
    """``output.choices[]`` 中的单个选项。"""

    finish_reason: str
    images: List[ImageResult] = field(default_factory=list)
    text_parts: List[str] = field(default_factory=list)
    role: str = "assistant"


@dataclass
class UsageInfo:
    """成功 API 响应的用量元数据。"""

    image_count: int = 0
    height: int = 0
    width: int = 0


@dataclass
class QwenImageResponse:
    """Qwen-Image 多模态生成 API 的完整解析响应。

    Attributes:
        images: 所有选项中的生成图片（扁平列表）。
        choices: 每个选项的详细信息，包括 finish_reason 和文本部分。
        usage: 图片数量和分辨率信息。
        request_id: Bailian 请求追踪 ID。
        raw: 原始未解析的响应 dict。
    """

    images: List[ImageResult]
    choices: List[ChoiceResult]
    usage: UsageInfo
    request_id: str
    raw: dict


def parse_response(raw: dict) -> QwenImageResponse:
    """将 Bailian API 原始响应 dict 解析为 ``QwenImageResponse``。

    >>> resp = parse_response({
    ...     "output": {
    ...         "choices": [{
    ...             "finish_reason": "stop",
    ...             "message": {
    ...                 "role": "assistant",
    ...                 "content": [{"image": "https://example.com/img.png"}]
    ...             }
    ...         }]
    ...     },
    ...     "usage": {"height": 2048, "width": 2048, "image_count": 1},
    ...     "request_id": "abc-123",
    ... })
    >>> resp.images[0].url
    'https://example.com/img.png'
    >>> resp.usage.image_count
    1
    """
    all_images: list[ImageResult] = []
    all_choices: list[ChoiceResult] = []

    for choice in raw.get("output", {}).get("choices", []):
        finish_reason = choice.get("finish_reason", "stop")
        message = choice.get("message", {})
        role = message.get("role", "assistant")

        images: list[ImageResult] = []
        texts: list[str] = []
        for block in message.get("content", []):
            if "image" in block:
                result = ImageResult(url=block["image"])
                images.append(result)
                all_images.append(result)
            if "text" in block:
                texts.append(block["text"])

        all_choices.append(ChoiceResult(
            finish_reason=finish_reason,
            images=images,
            text_parts=texts,
            role=role,
        ))

    usage_raw = raw.get("usage", {})
    usage = UsageInfo(
        image_count=usage_raw.get("image_count", len(all_images)),
        height=usage_raw.get("height", 0),
        width=usage_raw.get("width", 0),
    )

    return QwenImageResponse(
        images=all_images,
        choices=all_choices,
        usage=usage,
        request_id=raw.get("request_id", ""),
        raw=raw,
    )
