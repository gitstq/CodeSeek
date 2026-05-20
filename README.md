# 🔍 CodeSeek

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg?style=flat-square&logo=python&logoColor=white" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/License-MIT-green.svg?style=flat-square" alt="License: MIT">
  <img src="https://img.shields.io/badge/Zero%20Dependencies-✓-brightgreen.svg?style=flat-square" alt="Zero Dependencies">
  <img src="https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey.svg?style=flat-square" alt="Platform">
</p>

<p align="center">
  <strong>Lightweight Local Semantic Code Search Engine | 轻量级本地语义代码搜索引擎</strong>
</p>

<p align="center">
  <a href="#english">English</a> •
  <a href="#简体中文">简体中文</a> •
  <a href="#繁體中文">繁體中文</a>
</p>

---

<a name="english"></a>
## 🎉 Introduction

**CodeSeek** is a lightweight, zero-dependency semantic code search engine that runs entirely locally. It combines vector-based semantic search with BM25 keyword ranking to help you find code by meaning, not just keywords.

### Why CodeSeek?

- **🔒 Privacy First**: Your code never leaves your machine
- **⚡ Zero Dependencies**: Pure Python, no external libraries required
- **🧠 Hybrid Search**: Combines semantic (vector) + keyword (BM25) search
- **🌐 Multi-Backend**: Supports GLM-5.1, OpenAI, or local TF-IDF embeddings
- **🖥️ TUI Interface**: Beautiful terminal interface with ANSI colors
- **📦 Multi-Language**: Supports Python, JavaScript/TypeScript, Java, Go, Rust, C/C++, and more

---

## ✨ Core Features

| Feature | Description |
|---------|-------------|
| 🔍 **Semantic Search** | Find code by natural language meaning |
| 🔤 **Keyword Search** | Traditional BM25 text ranking |
| ✨ **Hybrid Ranking** | Combines semantic + keyword scores |
| 🧩 **Code Parsing** | Extracts functions, classes, methods |
| 🗄️ **SQLite Storage** | Fast local vector storage |
| 🎨 **TUI Dashboard** | Interactive terminal interface |
| 🌍 **Multi-Language** | 15+ programming languages |
| 🔧 **Configurable** | Flexible backend and settings |

---

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/gitstq/CodeSeek.git
cd CodeSeek

# Install (optional)
pip install -e .

# Or run directly
python codeseek.py
```

### Basic Usage

```bash
# Index your project
codeseek index

# Search with natural language
codeseek search "find user authentication functions"
codeseek search "database connection handling"
codeseek search "parse JSON data"

# Interactive mode
codeseek interactive

# Show statistics
codeseek stats
```

### Configure Backend

```bash
# Use GLM-5.1 (recommended)
export GLM_API_KEY="your-api-key"
codeseek set-backend glm

# Use OpenAI
export OPENAI_API_KEY="your-api-key"
codeseek set-backend openai

# Use local TF-IDF (no API key needed)
codeseek set-backend local
```

---

## 📖 Detailed Usage

### Indexing Options

```bash
# Index with verbose output
codeseek index -v

# Index specific path
codeseek index /path/to/project
```

### Search Options

```bash
# Limit results
codeseek search "query" -n 10

# Hide content preview
codeseek search "query" --no-content
```

### Configuration

```bash
# List all settings
codeseek config list

# Get specific setting
codeseek config get embedding_backend

# Set configuration
codeseek config set max_results 50
```

### Interactive Commands

In interactive mode (`codeseek interactive`):

| Command | Description |
|---------|-------------|
| `:quit` or `:q` | Exit interactive mode |
| `:stats` or `:s` | Show index statistics |
| `:clear` or `:c` | Clear the index |
| `:reindex` or `:r` | Reindex the project |

---

## 💡 Design Philosophy

### Why Pure Python?

- **No Dependency Hell**: No numpy, torch, or heavy ML libraries
- **Fast Startup**: No model loading overhead
- **Easy Deployment**: Single file, copy anywhere
- **Hackable**: Easy to understand and modify

### Hybrid Search Strategy

1. **BM25** for exact keyword matching
2. **Vector Similarity** for semantic understanding
3. **Combined Score** for best of both worlds

---

## 📦 Supported Languages

- **Python** (.py)
- **JavaScript/TypeScript** (.js, .ts, .jsx, .tsx)
- **Java** (.java)
- **Go** (.go)
- **Rust** (.rs)
- **C/C++** (.c, .cpp, .h, .hpp)
- **Ruby** (.rb)
- **PHP** (.php)
- **C#** (.cs)
- **Swift** (.swift)
- **Kotlin** (.kt)
- **Scala** (.scala)
- **Lua** (.lua)
- **Perl** (.pl)
- **Shell** (.sh, .bash, .zsh)

---

## 🤝 Contributing

We welcome contributions! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'feat: add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<a name="简体中文"></a>
## 简体中文

### 🎉 项目介绍

**CodeSeek** 是一个轻量级、零依赖的本地语义代码搜索引擎。它结合了基于向量的语义搜索和 BM25 关键词排名，帮助您通过含义而非仅关键词来查找代码。

### 为什么选择 CodeSeek？

- **🔒 隐私优先**：您的代码永远不会离开您的机器
- **⚡ 零依赖**：纯 Python，无需外部库
- **🧠 混合搜索**：结合语义（向量）+ 关键词（BM25）搜索
- **🌐 多后端**：支持 GLM-5.1、OpenAI 或本地 TF-IDF 嵌入
- **🖥️ TUI 界面**：带 ANSI 颜色的美观终端界面
- **📦 多语言**：支持 Python、JavaScript/TypeScript、Java、Go、Rust、C/C++ 等

### 🚀 快速开始

```bash
# 克隆仓库
git clone https://github.com/gitstq/CodeSeek.git
cd CodeSeek

# 安装（可选）
pip install -e .

# 或直接运行
python codeseek.py
```

### 基本用法

```bash
# 索引您的项目
codeseek index

# 使用自然语言搜索
codeseek search "查找用户认证函数"
codeseek search "数据库连接处理"
codeseek search "解析 JSON 数据"

# 交互模式
codeseek interactive

# 显示统计信息
codeseek stats
```

### 配置后端

```bash
# 使用 GLM-5.1（推荐）
export GLM_API_KEY="your-api-key"
codeseek set-backend glm

# 使用 OpenAI
export OPENAI_API_KEY="your-api-key"
codeseek set-backend openai

# 使用本地 TF-IDF（无需 API 密钥）
codeseek set-backend local
```

---

<a name="繁體中文"></a>
## 繁體中文

### 🎉 專案介紹

**CodeSeek** 是一個輕量級、零依賴的本機語義程式碼搜尋引擎。它結合了基於向量的語義搜尋和 BM25 關鍵詞排名，幫助您透過含義而非僅關鍵詞來查找程式碼。

### 為什麼選擇 CodeSeek？

- **🔒 隱私優先**：您的程式碼永遠不會離開您的機器
- **⚡ 零依賴**：純 Python，無需外部函式庫
- **🧠 混合搜尋**：結合語義（向量）+ 關鍵詞（BM25）搜尋
- **🌐 多後端**：支援 GLM-5.1、OpenAI 或本機 TF-IDF 嵌入
- **🖥️ TUI 介面**：帶 ANSI 顏色的美觀終端介面
- **📦 多語言**：支援 Python、JavaScript/TypeScript、Java、Go、Rust、C/C++ 等

### 🚀 快速開始

```bash
# 克隆倉庫
git clone https://github.com/gitstq/CodeSeek.git
cd CodeSeek

# 安裝（可選）
pip install -e .

# 或直接執行
python codeseek.py
```

### 基本用法

```bash
# 索引您的專案
codeseek index

# 使用自然語言搜尋
codeseek search "查找使用者認證函數"
codeseek search "資料庫連線處理"
codeseek search "解析 JSON 資料"

# 互動模式
codeseek interactive

# 顯示統計資訊
codeseek stats
```

### 配置後端

```bash
# 使用 GLM-5.1（推薦）
export GLM_API_KEY="your-api-key"
codeseek set-backend glm

# 使用 OpenAI
export OPENAI_API_KEY="your-api-key"
codeseek set-backend openai

# 使用本機 TF-IDF（無需 API 金鑰）
codeseek set-backend local
```

---

## 🔗 Links

- **GitHub**: https://github.com/gitstq/CodeSeek
- **Issues**: https://github.com/gitstq/CodeSeek/issues

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/gitstq">gitstq</a>
</p>
