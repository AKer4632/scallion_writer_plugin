# scallion_writer_plugin

AstrBot 插件 —— 群友在群里喊话改剧本，AI 自动写入 article.txt，Scallion WatchClient 监听到文件变化后自动编译并 WebSocket 广播。

## 安装

1. 把整个 `scallion_writer_plugin` 文件夹放到 AstrBot 的 `data/plugins/` 目录
2. 重启 AstrBot 或在面板热重载
3. 在群聊中对阿柯说"改剧本"即可触发

## 配置

插件配置项在 `metadata.yaml` 的 `config` 段：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `article_path` | `article.txt` | Scallion 剧本文件的绝对路径 |

## 工具

插件注册了四个 LLM 可调用的工具：

- `scallion_write`：覆盖写入整个剧本文件
- `scallion_read`：读取当前剧本内容
- `scallion_patch`：局部替换（按行号或标签定位）
- `scallion_append`：在剧本末尾追加内容
