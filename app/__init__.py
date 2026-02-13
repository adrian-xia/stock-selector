"""A股智能选股系统应用包。

在模块导入时清除代理环境变量，避免数据源请求走代理。
"""

import os

# 清除代理环境变量（在任何其他模块导入前执行）
for _key in ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"]:
    os.environ.pop(_key, None)
