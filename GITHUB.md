# 上传到 GitHub 操作指南

## 前提

项目已经推送到 [github.com/rundust1-design/star-td](https://github.com/rundust1-design/star-td)，以下是一般流程记录。

## 首次上传

### 1. 初始化 Git 仓库

```bash
cd 项目目录
git init
```

### 2. 配置用户信息

```bash
git config user.email "你的邮箱"
git config user.name "你的用户名"
```

### 3. 添加 .gitignore

```bash
# Python 缓存
__pycache__/
*.py[cod]

# 虚拟环境
.venv/

# 大文件（需从原版星际争霸获取）
StarCraft108B/*.mpq
```

### 4. 提交并推送

```bash
git add -A
git commit -m "初始提交"
git remote add origin git@github.com:rundust1-design/star-td.git
git push -u origin master
```

## 后续更新

```bash
git add -A
git commit -m "描述改动内容"
git push
```

## 注意事项

- `StarDat.mpq`（63MB）和 `BrooDat.mpq`（23MB）已加入 `.gitignore`，不会上传到 GitHub。运行游戏需要从原版星际争霸 1.08b 安装目录手动复制这两个文件到 `StarCraft108B/`。
- GitHub 不推荐超过 50MB 的单文件，超过 100MB 会被拒绝。大文件建议使用 Git LFS 或排除上传。
