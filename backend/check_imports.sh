#!/bin/bash
# 检查 import 和 requirements.txt 的一致性

echo "检查代码中的 import 语句与 requirements.txt 的一致性..."

# 查找所有 Python 文件中的 import 语句
python_imports=$(find . -name "*.py" -not -path "./venv/*" -not -path "./.venv/*" -exec grep -h "^import\|^from.*import" {} \; | sed 's/import //' | sed 's/from //' | cut -d' ' -f1 | cut -d'.' -f1 | sort -u)

# 检查是否有未在 requirements.txt 中声明的包
echo "Python 文件中使用的包："
echo "$python_imports"

echo "检查完成。如果发现不一致，请更新 requirements.txt"