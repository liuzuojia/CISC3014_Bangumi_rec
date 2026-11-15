# PythonAnywhere WSGI 配置模板
# 用法：Web 标签页 → 点击 WSGI configuration file → 用本文件内容替换，
#      并把 <your-username> 换成你的 PythonAnywhere 用户名。

import sys

path = "/home/<your-username>/bangumi_rec"
if path not in sys.path:
    sys.path.insert(0, path)

from app import app as application  # noqa: E402
