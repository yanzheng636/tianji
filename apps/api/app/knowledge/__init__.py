"""书籍知识库：把古籍原文拆解、分类、入库（CowAgent 式结构化 wiki + 关键词检索）。

流程：原文 .txt/.md ──chunker──> 分章分段 ──topics──> 主题/标签 ──(可选)LLM──> 白话
        ──> Book/Passage 落库 ──wiki──> 导出 index.md + 分类 markdown

先关键词检索，向量列留好，日后接 pgvector 不用重构。
"""
