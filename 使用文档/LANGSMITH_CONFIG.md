# LangSmith 追溯配置指南

## 🔗 什么是LangSmith

LangSmith是LangChain官方提供的监控、调试和追溯平台，可以帮您：
- 📊 监控智能体执行过程
- 🐛 调试复杂的多步骤流程
- 📈 分析性能和成本
- 🔍 追溯每次对话的详细日志

## ⚙️ 配置步骤

### 1. 获取LangSmith API Key

1. 访问 [https://smith.langchain.com](https://smith.langchain.com)
2. 注册/登录账户
3. 在设置页面生成API Key

### 2. 设置环境变量

创建 `.env` 文件（如果不存在），添加以下配置：

```bash
# OpenAI API 配置
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1

# LangSmith 追溯配置
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__your-langsmith-api-key-here
LANGCHAIN_PROJECT=instrument_agent
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com

# 模型配置
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-ada-002
```

### 3. 验证配置

运行智能体时，如果看到以下信息说明配置成功：
```
🔗 LangSmith追溯已启用 - 项目: instrument_agent
```

## 📊 使用说明

### 项目名称
- **默认项目名**：`instrument_agent`
- **自定义项目名**：修改 `LANGCHAIN_PROJECT` 环境变量

### 追溯功能
启用后，所有智能体执行都会在LangSmith平台显示：
- 🔄 **流程图**：可视化执行路径
- 📝 **详细日志**：每个节点的输入输出
- ⏱️ **时间统计**：各步骤耗时分析
- 💰 **成本追踪**：LLM调用费用统计

### 敏感工具说明
当智能体显示"使用敏感工具处理N条标准"时，表示将执行：
- 🔍 标准数据库查询
- 🤖 LLM增强分析
- 📊 专业推荐生成

这些操作会在LangSmith中详细记录。

## 🚀 快速测试

运行交互式体验：
```bash
python interactive_experience.py
```

然后在LangSmith平台的 `instrument_agent` 项目中查看执行详情。

## ❓ 常见问题

**Q: 不配置LangSmith可以使用吗？**
A: 可以！不配置只是没有追溯功能，智能体正常工作。

**Q: API Key收费吗？**
A: LangSmith有免费额度，超出后按使用量收费。

**Q: 如何关闭追溯？**
A: 设置 `LANGCHAIN_TRACING_V2=false` 或删除相关环境变量。 