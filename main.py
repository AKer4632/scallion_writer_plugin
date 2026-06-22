"""Scallion 剧本写入器 —— AstrBot 插件

群友在群里让阿柯改剧本，阿柯调用工具写 article.txt，
Scallion 的 WatchClient 监听到文件变化后自动编译 + WebSocket 广播。

工具列表:
  - scallion_write: 覆盖写入整个剧本
  - scallion_read:  读取当前剧本内容
  - scallion_patch: 局部替换（按标签或行号定位）
  - scallion_append: 追加内容到末尾
"""

import os
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.provider import LLMResponse
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.message_components import Plain
from dataclasses import dataclass


@register(
    "scallion_writer_plugin",
    "阿柯AKer",
    "Scallion剧本写入器 - 群友改剧本AI自动写文件",
    "1.0.0",
    "https://github.com/AKer4632/scallion_writer_plugin",
)
class ScallionWriterPlugin(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.config = config
        # 剧本文件路径，优先用配置的绝对路径
        self.article_path: str = config.get("article_path", "article.txt")

    # ── 工具: scallion_write ──────────────────────────
    @filter.tool("scallion_write")
    async def scallion_write(self, event: AstrMessageEvent, content: str) -> LLMResponse:
        """覆盖写入 Scallion 剧本文件。content 参数为完整的剧本文本。

        用法: 当群友要求重写或替换整个剧本时调用此工具。
        传入的 content 必须是合法的 Scallion 语法。
        """
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.article_path)), exist_ok=True)
            with open(self.article_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"[ScallionWriter] 剧本已写入: {self.article_path}")
            return LLMResponse(
                content=f"剧本已写入 {self.article_path}，共 {len(content.splitlines())} 行。Scallion WatchClient 会自动检测变化并编译。"
            )
        except Exception as e:
            logger.error(f"[ScallionWriter] 写入失败: {e}")
            return LLMResponse(content=f"写入失败: {e}")

    # ── 工具: scallion_read ──────────────────────────
    @filter.tool("scallion_read")
    async def scallion_read(self, event: AstrMessageEvent) -> LLMResponse:
        """读取当前 Scallion 剧本文件的完整内容。

        用法: 当需要查看当前剧本内容以便修改时调用。
        """
        try:
            with open(self.article_path, "r", encoding="utf-8") as f:
                content = f.read()
            return LLMResponse(content=f"当前剧本内容:\n{content}")
        except FileNotFoundError:
            return LLMResponse(content=f"剧本文件不存在: {self.article_path}")
        except Exception as e:
            return LLMResponse(content=f"读取失败: {e}")

    # ── 工具: scallion_patch ──────────────────────────
    @filter.tool("scallion_patch")
    async def scallion_patch(
        self,
        event: AstrMessageEvent,
        target: str,
        new_content: str,
        mode: str = "label",
    ) -> LLMResponse:
        """局部替换剧本中的某一段。

        参数:
          target: 定位目标。
            - mode="label" 时，target 为标签名（如 "eaten"），替换该标签所在行及其到下一个标签之间的所有行。
            - mode="line"  时，target 为行号（从1开始），替换该行。
          new_content: 替换后的内容（可多行）。
          mode: 定位模式，"label" 或 "line"，默认 "label"。

        用法: 群友要求修改某个分支或某句话时调用，不需要重写整个剧本。
        """
        try:
            with open(self.article_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            if mode == "line":
                # 按行号替换
                line_num = int(target)
                if 1 <= line_num <= len(lines):
                    new_lines = new_content.splitlines(keepends=True)
                    if not new_lines[-1].endswith("\n"):
                        new_lines[-1] += "\n"
                    lines[line_num - 1:line_num] = new_lines
                else:
                    return LLMResponse(content=f"行号超出范围: {line_num}（共 {len(lines)} 行）")

            elif mode == "label":
                # 按标签定位: 找到 "target#" 开头的行，替换到下一个标签或文件末尾
                start_idx = None
                end_idx = len(lines)
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    # 匹配 "标签名#" 开头
                    if stripped.startswith(f"{target}#"):
                        start_idx = i
                    elif start_idx is not None and "#" in stripped and not stripped.startswith("//"):
                        # 遇到下一个标签，停止
                        # 判断是否是标签格式: xxx#语句
                        potential_label = stripped.split("#")[0]
                        if potential_label and not potential_label.startswith(("*", "enter", "focus", "unfocus", "talk", "play", "select", "jump", "exit", "}", ")", "{")):
                            end_idx = i
                            break

                if start_idx is None:
                    return LLMResponse(content=f"未找到标签: {target}")

                new_lines = new_content.splitlines(keepends=True)
                if new_lines and not new_lines[-1].endswith("\n"):
                    new_lines[-1] += "\n"
                lines[start_idx:end_idx] = new_lines

            else:
                return LLMResponse(content=f"不支持的 mode: {mode}，请用 'label' 或 'line'")

            with open(self.article_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

            logger.info(f"[ScallionWriter] 剧本已局部更新 (mode={mode}, target={target})")
            return LLMResponse(
                content=f"剧本已局部更新 (mode={mode}, target={target})。WatchClient 会自动检测变化。"
            )

        except FileNotFoundError:
            return LLMResponse(content=f"剧本文件不存在: {self.article_path}")
        except Exception as e:
            logger.error(f"[ScallionWriter] 局部更新失败: {e}")
            return LLMResponse(content=f"局部更新失败: {e}")

    # ── 工具: scallion_append ──────────────────────────
    @filter.tool("scallion_append")
    async def scallion_append(self, event: AstrMessageEvent, content: str) -> LLMResponse:
        """在剧本文件末尾追加内容。

        参数:
          content: 要追加的剧本文本（可多行）。

        用法: 群友要求在剧本末尾新增场景或对话时调用。
        """
        try:
            with open(self.article_path, "a", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"[ScallionWriter] 已追加内容到剧本末尾")
            return LLMResponse(content=f"已追加 {len(content.splitlines())} 行到剧本末尾。")
        except Exception as e:
            return LLMResponse(content=f"追加失败: {e}")
