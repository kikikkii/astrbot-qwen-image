import os
import sys

# 将插件目录加入 sys.path，使 AstrBot 能加载 qwen_api 子包
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.message_components import Image, ComponentType
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
from qwen_api.QwenGenerateRequest import QwenImageRequest, Message, GenerationParameters
from qwen_api.qwen_image import multimodal_generation, save_images
from .tool.qwen_tool import QwenTool

@register("QwenImagePlugin", "lbh", "千问生图插件", "1.0.0")
class QwenImagePlugin(Star):

    def __init__(self, context: Context, config: AstrBotConfig=None):

        super().__init__(context)

        self.config = config
        logger.info(self.config)

        self.qwen_API_KEY = self.config["api-key"]

        self.base_url = self.config["base-url"]

        self.model_name = self.config["model-name"]
        self.context.add_llm_tools(QwenTool(self.model_name))



    async def initialize(self):

        logger.info("qwen-image初始化成功")

        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""


    # 注册指令的装饰器。指令名为 helloworld。注册成功后，发送 `/helloworld` 就会触发这个指令，并回复 `你好, {user_name}!`

    @filter.command("helloworld")

    async def helloworld(self, event: AstrMessageEvent):

        """这是一个 hello world 指令""" # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。

        user_name = event.get_sender_name()

        message_str = event.message_str # 用户发的纯文本消息字符串

        message_chain = event.get_messages() # 用户所发的消息的消息链 # from astrbot.api.message_components import *

        logger.info(message_chain)

        yield event.plain_result(f"Hello, {user_name}, 你发了 {message_str}!") # 发送一条纯文本消息


    @filter.command("qwen-image")

    async def qwen_image(self, event: AstrMessageEvent):
        user_name = event.get_sender_name()

        message_str = event.message_str  # 用户发的纯文本消息字符串

        message_chain = event.get_messages()
        yield event.plain_result("收到生成图片请求")
        # 提取所有图片
        images = [comp for comp in message_chain if comp.type == ComponentType.Image]

        # 构建输入消息
        input_message = Message()
        input_message.add_text(message_str)
        for img in images:
            # 优先使用 URL，其次使用 file 字段
            img_ref = img.url or img.file or ""
            input_message.add_image(image_url=img_ref)

        # 构建请求
        request = QwenImageRequest(model=self.model_name)
        request.add_message(input_message)

        # 调用 Qwen-Image API
        response = await multimodal_generation(
            request=request, baseurl=self.base_url, api_key=self.qwen_API_KEY
        )
        await save_images(response=response)
        # 返回结果
        yield event.plain_result(
            f"成功生成图片，消耗：{response.usage}"
        )
        for image_result in response.images:
            yield event.image_result(image_result.url)



    async def terminate(self):

        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""

