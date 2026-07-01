### 千问api调用工具
from pydantic import Field
from pydantic.dataclasses import dataclass

from astrbot.core.agent.run_context import ContextWrapper
from astrbot.core.agent.tool import FunctionTool, ToolExecResult
from astrbot.core.astr_agent_context import AstrAgentContext
from astrbot.api import logger
from qwen_api.QwenGenerateRequest import QwenImageRequest, Message, GenerationParameters
from qwen_api.qwen_image import multimodal_generation, save_images

@dataclass
class QwenTool(FunctionTool[AstrAgentContext]):
    name: str = "qwen_image_generate"
    description: str = "千问图像生成api调用工具"
    # 默认调用模型
    model: str = ""
    base_url: str = ""
    qwen_API_KEY: str = ""
    parameters: dict = Field(
        default_factory = lambda: {
            "type": "object",
            "properties": {
                "prompts": {
                    "type": "string",
                    "description": "要生成图片的描述词/提示词"
                },
                "images": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "字符串数组，包含了图片的url"
                },
            },
            "required": ["prompts"],
        },
    )
    
    def __post_init__(self):
        logger.info("千问图像生成工具默认模型：%s", self.model)

    async def call(self, context: ContextWrapper[AstrAgentContext],
        **kwargs) -> ToolExecResult:
        # 执行qwen图像生成工具
        request = QwenImageRequest(model=self.model)

        input_message = Message()
        prompts: str = kwargs.get("prompts", "")
        if not prompts:
            logger.info("提示词为空")
        input_message.add_text(prompts)

        images: list = kwargs.get("images", [])
        if not images:
            logger.info("未提供参考图片")
        for image in images:
            input_message.add_image(image_url=image)

        request.add_message(input_message)
        # 调用 Qwen-Image API
        response = await multimodal_generation(
            request=request, baseurl=self.base_url, api_key=self.qwen_API_KEY
        )

        urls = [img.url for img in response.images]
        result_text = f"成功生成 {len(urls)} 张图片"
        if urls:
            result_text += "\n" + "\n".join(urls)
        return ToolExecResult(result=result_text)



