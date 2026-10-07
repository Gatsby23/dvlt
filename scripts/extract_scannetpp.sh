#!/bin/bash

# 1. 获取目标文件夹路径
# 如果运行时带了参数 (例如 ./extract_files.sh /path/to/folder)，则使用参数
TARGET_DIR="$1"

# 如果没有带参数，则提示用户手动输入
if [ -z "$TARGET_DIR" ]; then
    read -p "请输入要处理的文件夹绝对或相对路径: " TARGET_DIR
fi

# 2. 校验文件夹是否存在
if [ ! -d "$TARGET_DIR" ]; then
    echo "❌ 错误: 找不到文件夹 '$TARGET_DIR'，请检查路径是否正确。"
    exit 1
fi

# 3. 切换到目标目录
# 切换目录的好处是，7z 解压出来的文件会自动放在该目录下，不需要额外指定输出路径
cd "$TARGET_DIR" || { echo "❌ 无法进入目录 '$TARGET_DIR'"; exit 1; }

echo "📂 开始处理目录: $(pwd)"

# 错误日志将保存在你指定的这个目标文件夹中
ERROR_LOG="extract_errors.log"

# 开启 nullglob，防止找不到文件时报错
shopt -s nullglob

# 查找 .zip 和 .tar 文件
for file in *.zip *.tar; do
    echo "===================================="
    echo "正在解压: $file"
    # -o参数用来指定输出目录，${file%.*} 表示去掉文件后缀名
    if 7z x "$file" -y -o"${file%.*}"; then
        echo "✅ 解压成功，正在删除原压缩包: $file"
        rm -f "$file"
    else
        echo "❌ 解压失败，已将文件名记录到 $ERROR_LOG"
        echo "$file" >> "$ERROR_LOG"
    fi
    
    echo "休眠 500ms..."
    sleep 0.5
done

echo "===================================="
echo "🎉 文件夹 '$TARGET_DIR' 内的所有任务处理完毕！"

if [ -s "$ERROR_LOG" ]; then
    echo "⚠️ 发现有解压失败的文件，请查看日志: $(pwd)/$ERROR_LOG"
fi